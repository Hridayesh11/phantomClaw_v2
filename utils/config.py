"""
utils/config.py
---------------
Central configuration loader for PhantomClaw v2.
Reads from .env using python-dotenv so all secrets stay out of source code.
"""

import os
from dotenv import load_dotenv

# Load .env from project root (works regardless of CWD)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))


class Config:
    """Singleton-style config object with typed accessors."""

    # --- AI ---
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

    # --- Backend ---
    FASTAPI_URL: str = os.getenv("FASTAPI_URL", "http://localhost:8000")

    # --- Database ---
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./database/trades.db")

    # --- Logging ---
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls) -> None:
        """Raise a clear error if required config is missing."""
        if not cls.OPENAI_API_KEY or cls.OPENAI_API_KEY == "your_openai_api_key_here":
            raise EnvironmentError(
                "OPENAI_API_KEY is not set. Please add it to your .env file."
            )


# Convenience singleton
config = Config()
