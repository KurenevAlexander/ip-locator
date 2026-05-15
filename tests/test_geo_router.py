"""Integration tests for the geolocation router endpoints."""

import pytest
import respx
from httpx import ASGITransport, AsyncClient, Response

from app.main import create_app
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
def mock_ip_api():
    """Mock all HTTP calls to ip-api.com; assert_all_called=False for tests that
    don't reach the HTTP layer (e.g. invalid/private IP pre-validation)."""
    with respx.mock(base_url="http://ip-api.com", assert_all_called=False) as mock:
        yield mock


@pytest.fixture
def app_with_provider(mock_ip_api):
    """
    Create a FastAPI app with a real IpApiProvider injected into app.state,
    bypassing the lifespan so tests stay fast and self-contained.
    The provider's httpx client is intercepted by respx.
    """
    application = create_app()
    # Inject the provider directly — no lifespan needed in tests
    application.state.geo_provider = IpApiProvider(client=AsyncClient(base_url="http://ip-api.com"))
    return application


def make_client(application):
    return AsyncClient(transport=ASGITransport(app=application), base_url="http://test")


@pytest.mark.asyncio
async def test_get_geolocation_success(app_with_provider, mock_ip_api):
    mock_ip_api.get("/json/8.8.8.8").mock(return_value=Response(200, json=_SUCCESS_PAYLOAD))
    async with make_client(app_with_provider) as client:
        response = await client.get("/v1/geo/8.8.8.8")

    assert response.status_code == 200
    data = response.json()
    assert data["ip"] == "8.8.8.8"
    assert data["country"] == "United States"
    assert data["country_code"] == "US"
    assert data["coordinates"]["lat"] == 37.4223
    assert data["ip_version"] == 4


@pytest.mark.asyncio
async def test_get_geolocation_invalid_ip(app_with_provider):
    async with make_client(app_with_provider) as client:
        response = await client.get("/v1/geo/not-an-ip")

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_ip"


@pytest.mark.asyncio
async def test_get_geolocation_private_ip(app_with_provider):
    async with make_client(app_with_provider) as client:
        response = await client.get("/v1/geo/10.0.0.1")

    assert response.status_code == 400
    assert response.json()["error"] == "private_ip"


@pytest.mark.asyncio
async def test_get_geolocation_not_found(app_with_provider, mock_ip_api):
    mock_ip_api.get("/json/8.8.8.8").mock(
        return_value=Response(
            200,
            json={"status": "fail", "message": "private range", "query": "8.8.8.8"},
        )
    )
    async with make_client(app_with_provider) as client:
        response = await client.get("/v1/geo/8.8.8.8")

    assert response.status_code == 404
    assert response.json()["error"] == "location_not_found"


@pytest.mark.asyncio
async def test_get_geolocation_rate_limit(app_with_provider, mock_ip_api):
    mock_ip_api.get("/json/8.8.8.8").mock(return_value=Response(429))
    async with make_client(app_with_provider) as client:
        response = await client.get("/v1/geo/8.8.8.8")

    assert response.status_code == 429
    assert response.json()["error"] == "rate_limit_exceeded"


@pytest.mark.asyncio
async def test_get_geolocation_provider_unavailable(app_with_provider, mock_ip_api):
    mock_ip_api.get("/json/8.8.8.8").mock(return_value=Response(503))
    async with make_client(app_with_provider) as client:
        response = await client.get("/v1/geo/8.8.8.8")

    assert response.status_code == 503
    assert response.json()["error"] == "provider_unavailable"


@pytest.mark.asyncio
async def test_get_my_geolocation(app_with_provider, mock_ip_api):
    """GET /v1/geo/me — IP taken from X-Forwarded-For header."""
    mock_ip_api.get("/json/8.8.8.8").mock(return_value=Response(200, json=_SUCCESS_PAYLOAD))
    async with make_client(app_with_provider) as client:
        response = await client.get("/v1/geo/me", headers={"X-Forwarded-For": "8.8.8.8"})

    assert response.status_code == 200
    assert response.json()["ip"] == "8.8.8.8"


@pytest.mark.asyncio
async def test_get_my_geolocation_x_real_ip(app_with_provider, mock_ip_api):
    """GET /v1/geo/me — IP taken from X-Real-IP header when X-Forwarded-For is absent."""
    mock_ip_api.get("/json/1.1.1.1").mock(
        return_value=Response(200, json={**_SUCCESS_PAYLOAD, "query": "1.1.1.1"})
    )
    async with make_client(app_with_provider) as client:
        response = await client.get("/v1/geo/me", headers={"X-Real-IP": "1.1.1.1"})

    assert response.status_code == 200
    assert response.json()["ip"] == "1.1.1.1"
