"""
llm/openai_client.py
---------------------
Centralised LLM adapter layer for PhantomClaw v2.

All OpenAI-specific code lives here. Agents NEVER call OpenAI directly.
They call `call_llm()` from this module only.

To switch to Gemini, Claude, or DeepSeek:
  1. Add a new function (e.g. `call_gemini()`)
  2. Replace the body of `call_llm()` to delegate to it
  3. Zero agent code changes required.
"""

import logging
from openai import OpenAI, APIError, APIConnectionError, RateLimitError

from utils.config import config

logger = logging.getLogger(__name__)

# Lazy-initialised client (avoids creating it at import time before .env is loaded)
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """Return a cached OpenAI client, initialising on first call."""
    global _client
    if _client is None:
        if not config.OPENAI_API_KEY or config.OPENAI_API_KEY == "your_openai_api_key_here":
            raise EnvironmentError(
                "OPENAI_API_KEY is not configured. "
                "Set it in your .env file before running PhantomClaw."
            )
        _client = OpenAI(api_key=config.OPENAI_API_KEY)
        logger.debug("OpenAI client initialised with model=%s", config.OPENAI_MODEL)
    return _client


def call_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.3,
    max_tokens: int = 512,
    json_mode: bool = True,
) -> str:
    """
    Send a structured prompt to the configured LLM and return the raw text response.

    This is the SINGLE point of LLM contact for the entire PhantomClaw system.

    Args:
        system_prompt:  Role / persona instructions for the model.
        user_prompt:    The task / question to answer.
        temperature:    Sampling temperature (lower = more deterministic).
        max_tokens:     Maximum tokens in the response.
        json_mode:      If True, instructs the model to respond with valid JSON.

    Returns:
        Raw string response from the model.

    Raises:
        RuntimeError: On API errors (with descriptive message for logging).
    """
    client = _get_client()

    kwargs: dict = {
        "model": config.OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    try:
        logger.debug("Calling LLM [model=%s, json_mode=%s]", config.OPENAI_MODEL, json_mode)
        response = client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or ""
        logger.debug("LLM responded with %d characters", len(content))
        return content

    except RateLimitError as exc:
        logger.error("OpenAI rate limit exceeded: %s", exc)
        raise RuntimeError(f"LLM rate limit hit. Try again shortly. Detail: {exc}") from exc

    except APIConnectionError as exc:
        logger.error("Cannot reach OpenAI API: %s", exc)
        raise RuntimeError(f"Cannot connect to LLM API. Check network. Detail: {exc}") from exc

    except APIError as exc:
        logger.error("OpenAI API error: %s", exc)
        raise RuntimeError(f"LLM API error: {exc}") from exc
