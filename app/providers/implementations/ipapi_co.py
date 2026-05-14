"""ipapi.co geolocation provider implementation.

Free tier: 1 000 requests/day without a key.
Authenticated tier: higher quota via GEO_API_KEY setting.
Supports IPv4 and IPv6.
"""

import logging
from typing import Any, TypedDict

import httpx

from app.core.exceptions import LocationNotFoundError, ProviderUnavailableError, RateLimitError
from app.models.geo import Coordinates, GeolocationResponse
from app.providers.base import GeoProvider

logger = logging.getLogger(__name__)

_BASE_URL = "https://ipapi.co"


class _IpapiCoResponse(TypedDict, total=False):
    """Shape of a successful ipapi.co JSON response."""

    ip: str
    country_name: str
    country_code: str
    region: str
    region_code: str
    city: str
    postal: str
    latitude: float
    longitude: float
    timezone: str
    org: str
    error: bool
    reason: str


class IpapiCoProvider(GeoProvider):
    """Geolocation provider backed by `ipapi.co <https://ipapi.co>`_.

    Attributes:
        _client: Shared async HTTP client.
        _api_key: Optional API key for authenticated requests.
    """

    def __init__(self, client: httpx.AsyncClient, api_key: str | None = None) -> None:
        self._client = client
        self._api_key = api_key

    async def locate(self, ip: str) -> GeolocationResponse:
        """Return geolocation data for the given IP address.

        Args:
            ip: A public IPv4 or IPv6 address string.

        Returns:
            Populated :class:`~app.models.geo.GeolocationResponse`.

        Raises:
            InvalidIPError: If *ip* is not a valid IP address.
            PrivateIPError: If *ip* is a private or reserved address.
            LocationNotFoundError: If ipapi.co reports no data for *ip*.
            RateLimitError: If ipapi.co returns HTTP 429.
            ProviderUnavailableError: On timeout or unexpected HTTP status.
        """
        addr = self.validate_ip(ip)
        logger.debug("Locating IP via ipapi.co", extra={"ip": ip})

        params: dict[str, Any] = {}
        if self._api_key:
            params["key"] = self._api_key

        try:
            response = await self._client.get(f"{_BASE_URL}/{ip}/json/", params=params)
        except httpx.TimeoutException as exc:
            logger.warning("ipapi.co request timed out", extra={"ip": ip})
            raise ProviderUnavailableError("ipapi.co timed out.") from exc
        except httpx.RequestError as exc:
            logger.warning("ipapi.co request failed", extra={"ip": ip, "error": str(exc)})
            raise ProviderUnavailableError(f"Could not reach ipapi.co: {exc}") from exc

        if response.status_code == 429:
            logger.warning("ipapi.co rate limit exceeded", extra={"ip": ip})
            raise RateLimitError("ipapi.co rate limit exceeded.")

        if response.status_code != 200:
            logger.error(
                "ipapi.co returned unexpected status",
                extra={"ip": ip, "status": response.status_code},
            )
            raise ProviderUnavailableError(
                f"ipapi.co returned unexpected status {response.status_code}."
            )

        data: _IpapiCoResponse = response.json()

        if data.get("error"):
            logger.info("ipapi.co: no data for IP", extra={"ip": ip, "reason": data.get("reason")})
            raise LocationNotFoundError(ip)

        logger.debug("ipapi.co lookup successful", extra={"ip": ip, "country": data.get("country_name")})

        return GeolocationResponse(
            ip=data["ip"],
            country=data["country_name"],
            country_code=data["country_code"],
            region=data["region"],
            region_code=data.get("region_code", ""),
            city=data["city"],
            zip_code=data.get("postal", ""),
            coordinates=Coordinates(lat=data["latitude"], lon=data["longitude"]),
            timezone=data["timezone"],
            isp=data.get("org", ""),
            org=data.get("org", ""),
            ip_version=addr.version,
        )

    async def close(self) -> None:
        """Close the underlying HTTP client and release connections."""
        await self._client.aclose()
        logger.debug("IpapiCoProvider HTTP client closed")
