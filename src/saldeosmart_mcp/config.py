"""SaldeoSMART connection settings.

Loaded from environment variables prefixed with ``SALDEO_``. Owns nothing
beyond the credentials and a couple of HTTP knobs — kept in its own module
so every other layer can import it without dragging in httpx, FastMCP, or
domain models.
"""

from __future__ import annotations

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_BASE_URL = "https://saldeo.brainshare.pl"
DEFAULT_TIMEOUT = 30.0


class SaldeoConfig(BaseSettings):
    """SaldeoSMART connection settings.

    Loads from environment variables prefixed with ``SALDEO_``:
      - ``SALDEO_USERNAME``      (required)
      - ``SALDEO_API_TOKEN``     (required) — held as ``SecretStr`` so it
                                  never leaks via ``repr()`` or logs
      - ``SALDEO_BASE_URL``      (default: production)
      - ``SALDEO_TIMEOUT``       (default: 30s)

    Use ``SaldeoConfig()`` to load from env, or ``SaldeoConfig(username=...,
    api_token=...)`` to build explicitly (e.g. in tests).
    """

    username: str = Field(min_length=1)
    api_token: SecretStr = Field(min_length=1)
    base_url: str = Field(default=DEFAULT_BASE_URL, pattern=r"^https?://")
    timeout: float = Field(default=DEFAULT_TIMEOUT, gt=0)

    model_config = SettingsConfigDict(env_prefix="SALDEO_", extra="ignore")
