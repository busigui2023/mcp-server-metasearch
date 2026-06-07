"""Configuration management for mcp-server-metasearch."""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

CONFIG_DIR = Path.home() / ".config" / "mcp-server-metasearch"
ENV_FILE = CONFIG_DIR / ".env"

_env_loaded: bool = False


def load_environment() -> None:
    """Ensure config directory exists and load .env into os.environ.

    Safe to call multiple times; only loads from disk once.
    """
    global _env_loaded
    if _env_loaded:
        return
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    load_dotenv(dotenv_path=ENV_FILE, override=True)
    _env_loaded = True


class Settings(BaseSettings):
    """Server settings loaded from ~/.config/mcp-server-metasearch/.env."""

    model_config = SettingsConfigDict(
        extra="ignore",
    )

    # API Keys (declared explicitly for type safety and validation)
    jina_api_key: str | None = None
    tavily_api_key: str | None = None
    exa_api_key: str | None = None
    firecrawl_api_key: str | None = None
    bocha_api_key: str | None = None

    def is_tool_enabled(self, env_var_name: str) -> bool:
        """Check if a tool switch is enabled.

        Reads directly from os.environ so new tools don't require
        updating this class.
        """
        value = os.getenv(env_var_name.upper())
        if value is None:
            return False
        return value.strip().lower() in ("1", "true", "yes", "on")

    def has_api_key(self, key_name: str) -> bool:
        """Check if an API key is present and non-empty."""
        value = getattr(self, key_name.lower(), None)
        return value is not None and str(value).strip() != ""


def get_settings() -> Settings:
    """Return a Settings instance with environment loaded.

    Callers should invoke this lazily rather than at import time.
    """
    load_environment()
    return Settings()
