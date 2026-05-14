"""Application configuration via environment variables / .env file."""

from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or a ``.env`` file.

    Environment variable names match field names in upper-case
    (e.g. ``GEO_PROVIDER=ipapi_co``).
    See ``.env.example`` for all available options.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Provider selection
    geo_provider: Literal["ip_api", "ipapi_co", "maxmind"] = "ip_api"

    # Optional API key (used by providers that support authentication, e.g. ipapi.co)
    geo_api_key: str | None = None

    # Path to MaxMind GeoLite2-City.mmdb (required only when geo_provider="maxmind")
    maxmind_db_path: str = "GeoLite2-City.mmdb"

    # HTTP client timeout in seconds
    http_timeout: float = 5.0

    @model_validator(mode="after")
    def _validate_maxmind_path(self) -> "Settings":
        """Ensure maxmind_db_path is set when the MaxMind provider is selected."""
        if self.geo_provider == "maxmind" and not self.maxmind_db_path:
            raise ValueError("maxmind_db_path must be set when geo_provider='maxmind'")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return application settings.

    Results are cached so the ``.env`` file is read only once per process.

    Note:
        In tests, call ``get_settings.cache_clear()`` after patching env vars.

    Returns:
        The cached :class:`Settings` instance.
    """
    return Settings()
