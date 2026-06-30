"""
market_data/retry.py
--------------------
Provides a deterministic retry and exponential backoff layer for HTTP requests.
Handles rate limits (HTTP 429), timeouts, and network connection errors
with structured logging for each retry scenario.
"""

import logging
import time
from typing import Any, Callable

import httpx

logger = logging.getLogger(__name__)

# Constants for deterministic retry behavior
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0  # seconds
BACKOFF_FACTOR = 2.0


def with_retry(func: Callable[..., httpx.Response]) -> Callable[..., httpx.Response]:
    """
    A decorator that applies exponential backoff to a function returning httpx.Response.
    Retries on:
        - httpx.TimeoutException (connect/read/write/pool timeouts)
        - httpx.ConnectError (DNS resolution, connection refused)
        - httpx.RequestError (other transport-level errors)
        - HTTP 429 Too Many Requests
        - HTTP 500+ Server Errors
    """

    def wrapper(*args: Any, **kwargs: Any) -> httpx.Response:
        retries = 0
        backoff = INITIAL_BACKOFF

        while True:
            try:
                response = func(*args, **kwargs)

                # Check for rate limiting
                if response.status_code == 429:
                    if retries >= MAX_RETRIES:
                        logger.error(
                            "Max retries (%d) reached after HTTP 429 rate limit.",
                            MAX_RETRIES,
                        )
                        response.raise_for_status()

                    retry_after = response.headers.get("Retry-After")
                    wait = float(retry_after) if retry_after else backoff
                    logger.warning(
                        "HTTP 429 Rate Limit hit. Retry %d/%d in %.1fs...",
                        retries + 1, MAX_RETRIES, wait,
                    )
                    time.sleep(wait)
                    retries += 1
                    backoff *= BACKOFF_FACTOR
                    continue

                # Check for server errors
                if response.status_code >= 500:
                    if retries >= MAX_RETRIES:
                        logger.error(
                            "Max retries (%d) reached after HTTP %d server error.",
                            MAX_RETRIES, response.status_code,
                        )
                        response.raise_for_status()

                    logger.warning(
                        "HTTP %d Server Error. Retry %d/%d in %.1fs...",
                        response.status_code, retries + 1, MAX_RETRIES, backoff,
                    )
                    time.sleep(backoff)
                    retries += 1
                    backoff *= BACKOFF_FACTOR
                    continue

                # Return successful response
                response.raise_for_status()
                return response

            except httpx.TimeoutException as exc:
                if retries >= MAX_RETRIES:
                    logger.error(
                        "Max retries (%d) reached for timeout: %s", MAX_RETRIES, exc,
                    )
                    raise

                logger.warning(
                    "Request timeout: %s. Retry %d/%d in %.1fs...",
                    exc, retries + 1, MAX_RETRIES, backoff,
                )
                time.sleep(backoff)
                retries += 1
                backoff *= BACKOFF_FACTOR

            except httpx.ConnectError as exc:
                if retries >= MAX_RETRIES:
                    logger.error(
                        "Max retries (%d) reached for connection error: %s",
                        MAX_RETRIES, exc,
                    )
                    raise

                logger.warning(
                    "Connection error: %s. Retry %d/%d in %.1fs...",
                    exc, retries + 1, MAX_RETRIES, backoff,
                )
                time.sleep(backoff)
                retries += 1
                backoff *= BACKOFF_FACTOR

            except httpx.RequestError as exc:
                if retries >= MAX_RETRIES:
                    logger.error(
                        "Max retries (%d) reached for request error: %s",
                        MAX_RETRIES, exc,
                    )
                    raise

                logger.warning(
                    "Request error: %s. Retry %d/%d in %.1fs...",
                    exc, retries + 1, MAX_RETRIES, backoff,
                )
                time.sleep(backoff)
                retries += 1
                backoff *= BACKOFF_FACTOR

    return wrapper
