"""Unit tests for IpapiCoProvider."""

import pytest
import respx
from httpx import AsyncClient, Response, TimeoutException

from app.core.exceptions import (
    InvalidIPError,
    LocationNotFoundError,
    PrivateIPError,
    ProviderUnavailableError,
    RateLimitError,
)
from app.providers.implementations.ipapi_co import IpapiCoProvider

_SUCCESS_PAYLOAD = {
    "ip": "8.8.8.8",
    "country_name": "United States",
    "country_code": "US",
    "region": "California",
    "region_code": "CA",
    "city": "Mountain View",
    "postal": "94043",
    "latitude": 37.4223,
    "longitude": -122.0848,
    "timezone": "America/Los_Angeles",
    "org": "Google LLC",
}


@pytest.fixture
def provider():
    with respx.mock(base_url="https://ipapi.co") as mock:
        yield IpapiCoProvider(client=AsyncClient(base_url="https://ipapi.co")), mock


async def test_locate_success(provider):
    prov, mock = provider
    mock.get("/8.8.8.8/json/").mock(return_value=Response(200, json=_SUCCESS_PAYLOAD))

    result = await prov.locate("8.8.8.8")

    assert result.ip == "8.8.8.8"
    assert result.country == "United States"
    assert result.country_code == "US"
    assert result.city == "Mountain View"
    assert result.coordinates is not None
    assert result.coordinates.lat == 37.4223
    assert result.ip_version == 4
    # ipapi.co free tier exposes only `org` — both `isp` and `org` mirror it.
    assert result.isp == result.org == "Google LLC"
    await prov.close()


async def test_locate_ipv6_success(provider):
    prov, mock = provider
    payload = {**_SUCCESS_PAYLOAD, "ip": "2001:4860:4860::8888"}
    mock.get("/2001:4860:4860::8888/json/").mock(return_value=Response(200, json=payload))

    result = await prov.locate("2001:4860:4860::8888")

    assert result.ip_version == 6
    await prov.close()


async def test_locate_missing_optional_fields_become_null(provider):
    """Optional fields absent in upstream payload must surface as null, not ''."""
    prov, mock = provider
    payload = {
        "ip": "8.8.8.8",
        "country_name": "United States",
        "country_code": "US",
        # region, region_code, city, postal, timezone, org, lat/lon omitted
    }
    mock.get("/8.8.8.8/json/").mock(return_value=Response(200, json=payload))

    result = await prov.locate("8.8.8.8")

    assert result.region is None
    assert result.city is None
    assert result.zip_code is None
    assert result.coordinates is None
    assert result.timezone is None
    assert result.isp is None
    assert result.org is None
    await prov.close()


async def test_locate_invalid_ip(provider):
    prov, _ = provider
    with pytest.raises(InvalidIPError):
        await prov.locate("not-an-ip")
    await prov.close()


async def test_locate_private_ip(provider):
    prov, _ = provider
    with pytest.raises(PrivateIPError):
        await prov.locate("192.168.1.1")
    await prov.close()


async def test_locate_rate_limit_via_http_429(provider):
    prov, mock = provider
    mock.get("/8.8.8.8/json/").mock(return_value=Response(429))
    with pytest.raises(RateLimitError):
        await prov.locate("8.8.8.8")
    await prov.close()


async def test_locate_rate_limit_via_error_payload(provider):
    """ipapi.co quirk: rate-limit can be signalled as HTTP 200 + error payload."""
    prov, mock = provider
    mock.get("/8.8.8.8/json/").mock(
        return_value=Response(
            200,
            json={"error": True, "reason": "RateLimited", "message": "..."},
        )
    )
    with pytest.raises(RateLimitError):
        await prov.locate("8.8.8.8")
    await prov.close()


async def test_locate_throttled_payload_also_rate_limit(provider):
    """Defensive: ``Throttled`` reason maps to RateLimitError as well."""
    prov, mock = provider
    mock.get("/8.8.8.8/json/").mock(
        return_value=Response(200, json={"error": True, "reason": "Throttled"})
    )
    with pytest.raises(RateLimitError):
        await prov.locate("8.8.8.8")
    await prov.close()


async def test_locate_error_other_reason_is_not_found(provider):
    """Other error payloads (e.g. Reserved IP) map to LocationNotFoundError."""
    prov, mock = provider
    mock.get("/8.8.8.8/json/").mock(
        return_value=Response(200, json={"error": True, "reason": "Reserved IP Address"})
    )
    with pytest.raises(LocationNotFoundError):
        await prov.locate("8.8.8.8")
    await prov.close()


async def test_locate_unexpected_status(provider):
    prov, mock = provider
    mock.get("/8.8.8.8/json/").mock(return_value=Response(500))
    with pytest.raises(ProviderUnavailableError):
        await prov.locate("8.8.8.8")
    await prov.close()


async def test_locate_timeout(provider):
    prov, mock = provider
    mock.get("/8.8.8.8/json/").mock(side_effect=TimeoutException("timed out"))
    with pytest.raises(ProviderUnavailableError):
        await prov.locate("8.8.8.8")
    await prov.close()


async def test_api_key_is_forwarded_as_query_param():
    """When configured with an API key, it must be sent as ?key=..."""
    with respx.mock(base_url="https://ipapi.co") as mock:
        route = mock.get("/8.8.8.8/json/", params={"key": "secret-key"}).mock(
            return_value=Response(200, json=_SUCCESS_PAYLOAD)
        )
        prov = IpapiCoProvider(
            client=AsyncClient(base_url="https://ipapi.co"),
            api_key="secret-key",
        )
        await prov.locate("8.8.8.8")
        assert route.called
        await prov.close()
