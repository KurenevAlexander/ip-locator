"""Unit tests for the provider factory."""

import pytest

from app.core.config import Settings
from app.providers.factory import create_provider
from app.providers.implementations.ip_api import IpApiProvider
from app.providers.implementations.ipapi_co import IpapiCoProvider


def _settings(**overrides) -> Settings:
    """Build a Settings instance, bypassing .env discovery."""
    defaults = {
        "geo_provider": "ip_api",
        "geo_api_key": None,
        "http_timeout": 5.0,
    }
    return Settings(**(defaults | overrides), _env_file=None)


def test_create_provider_ip_api():
    prov = create_provider(_settings(geo_provider="ip_api"))
    assert isinstance(prov, IpApiProvider)


def test_create_provider_ipapi_co():
    prov = create_provider(_settings(geo_provider="ipapi_co", geo_api_key="abc"))
    assert isinstance(prov, IpapiCoProvider)
    assert prov._api_key == "abc"


def test_create_provider_unknown_raises():
    # Bypass pydantic Literal validation by constructing Settings then mutating.
    settings = _settings()
    object.__setattr__(settings, "geo_provider", "bogus")
    with pytest.raises(ValueError, match="Unknown GEO_PROVIDER"):
        create_provider(settings)
