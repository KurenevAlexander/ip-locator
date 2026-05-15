"""Unit tests for IpApiProvider."""

import pytest
import respx
from httpx import AsyncClient, Response

from app.core.exceptions import (
    InvalidIPError,
    LocationNotFoundError,
    PrivateIPError,
    ProviderUnavailableError,
    RateLimitError,
)
from app.providers.implementations.ip_api import IpApiProvider

_SUCCESS_PAYLOAD = {
    "status": "success",
    "country": "United States",
    "countryCode": "US",
    "region": "CA",
    "regionName": "California",
    "city": "Mountain View",
    "zip": "94043",
    "lat": 37.4223,
    "lon": -122.0848,
    "timezone": "America/Los_Angeles",
    "isp": "Google LLC",
    "org": "AS15169 Google LLC",
    "query": "8.8.8.8",
}


@pytest.fixture
def provider():
    with respx.mock(base_url="http://ip-api.com") as mock:
        yield IpApiProvider(client=AsyncClient(base_url="http://ip-api.com")), mock


@pytest.mark.asyncio
async def test_locate_success(provider):
    prov, mock = provider
    mock.get("/json/8.8.8.8").mock(return_value=Response(200, json=_SUCCESS_PAYLOAD))

    result = await prov.locate("8.8.8.8")

    assert result.ip == "8.8.8.8"
    assert result.country == "United States"
    assert result.country_code == "US"
    assert result.city == "Mountain View"
    assert result.coordinates.lat == 37.4223
    assert result.ip_version == 4
    await prov.close()


@pytest.mark.asyncio
async def test_locate_ipv6_success(provider):
    prov, mock = provider
    payload = {**_SUCCESS_PAYLOAD, "query": "2001:4860:4860::8888"}
    mock.get("/json/2001:4860:4860::8888").mock(return_value=Response(200, json=payload))

    result = await prov.locate("2001:4860:4860::8888")
    assert result.ip_version == 6
    await prov.close()


@pytest.mark.asyncio
async def test_locate_invalid_ip(provider):
    prov, _ = provider
    with pytest.raises(InvalidIPError):
        await prov.locate("not-an-ip")
    await prov.close()


@pytest.mark.asyncio
async def test_locate_private_ip(provider):
    prov, _ = provider
    with pytest.raises(PrivateIPError):
        await prov.locate("192.168.1.1")
    await prov.close()


@pytest.mark.asyncio
async def test_locate_fail_status(provider):
    prov, mock = provider
    mock.get("/json/8.8.8.8").mock(
        return_value=Response(
            200,
            json={"status": "fail", "message": "private range", "query": "8.8.8.8"},
        )
    )
    with pytest.raises(LocationNotFoundError):
        await prov.locate("8.8.8.8")
    await prov.close()


@pytest.mark.asyncio
async def test_locate_rate_limit(provider):
    prov, mock = provider
    mock.get("/json/8.8.8.8").mock(return_value=Response(429))
    with pytest.raises(RateLimitError):
        await prov.locate("8.8.8.8")
    await prov.close()


@pytest.mark.asyncio
async def test_locate_provider_error(provider):
    prov, mock = provider
    mock.get("/json/8.8.8.8").mock(return_value=Response(500))
    with pytest.raises(ProviderUnavailableError):
        await prov.locate("8.8.8.8")
    await prov.close()
