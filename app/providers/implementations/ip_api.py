"""ip-api.com geolocation provider implementation.

Free tier, no API key required, 45 requests/minute on HTTP.
Supports IPv4 and IPv6.
"""

import logging
from typing import TypedDict, cast

import httpx

from app.core.exceptions import LocationNotFoundError, ProviderUnavailableError, RateLimitError
from app.models.geo import Coordinates, GeolocationResponse
from app.providers.base import GeoProvider

logger = logging.getLogger(__name__)

# Fields requested from ip-api.com — keeps the response payload minimal
_FIELDS = "status,message,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,query"
_BASE_URL = "http://ip-api.com/json"


class _IpApiResponse(TypedDict):
    """Shape of a successful ip-api.com JSON response."""

    status: str
    country: str
    countryCode: str
    region: str
    regionName: str
    city: str
    zip: str
    lat: float
    lon: float
    timezone: str
    isp: str
    org: str
    query: str


class IpApiProvider(GeoProvider):
    """Geolocation provider backed by `ip-api.com <http://ip-api.com>`_.

    Attributes:
        _client: Shared async HTTP client. Must be closed via :meth:`close`.

    Note:
        Free tier is limited to 45 requests/minute on plain HTTP.
        The paid HTTPS plan removes the rate limit.
    """

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def locate(self, ip: str) -> GeolocationResponse:
        """Return geolocation data for the given IP address.

        Args:
            ip: A public IPv4 or IPv6 address string.

        Returns:
            Populated :class:`~app.models.geo.GeolocationResponse`.

        Raises:
            InvalidIPError: If *ip* is not a valid IP address.
            PrivateIPError: If *ip* is a private or reserved address.
            LocationNotFoundError: If ip-api.com reports no data for *ip*.
            RateLimitError: If ip-api.com returns HTTP 429.
            ProviderUnavailableError: On timeout or unexpected HTTP status.
        """
        addr = self.validate_ip(ip)
        logger.debug("Locating IP via ip-api.com", extra={"ip": ip})

        try:
            response = await self._client.get(
                f"{_BASE_URL}/{ip}",
                params={"fields": _FIELDS},
            )
        except httpx.TimeoutException as exc:
            logger.warning("ip-api.com request timed out", extra={"ip": ip})
            raise ProviderUnavailableError("ip-api.com timed out.") from exc
        except httpx.RequestError as exc:
            logger.warning("ip-api.com request failed", extra={"ip": ip, "error": str(exc)})
            raise ProviderUnavailableError(f"Could not reach ip-api.com: {exc}") from exc

        if response.status_code == 429:
            logger.warning("ip-api.com rate limit exceeded", extra={"ip": ip})
            raise RateLimitError("ip-api.com rate limit exceeded. Retry after 60 seconds.")

        if response.status_code != 200:
            logger.error(
                "ip-api.com returned unexpected status",
                extra={"ip": ip, "status": response.status_code},
            )
            raise ProviderUnavailableError(
                f"ip-api.com returned unexpected status {response.status_code}."
            )

        data = cast(_IpApiResponse, response.json())

        if data["status"] == "fail":
            logger.info("ip-api.com: no data for IP", extra={"ip": ip})
            raise LocationNotFoundError(ip)

        logger.debug("ip-api.com lookup successful", extra={"ip": ip, "country": data["country"]})

        return GeolocationResponse(
            ip=data["query"],
            country=data["country"],
            country_code=data["countryCode"],
            region=data["regionName"],
            region_code=data["region"],
            city=data["city"],
            zip_code=data["zip"],
            coordinates=Coordinates(lat=data["lat"], lon=data["lon"]),
            timezone=data["timezone"],
            isp=data["isp"],
            org=data["org"],
            ip_version=addr.version,
        )

    async def close(self) -> None:
        """Close the underlying HTTP client and release connections."""
        await self._client.aclose()
        logger.debug("IpApiProvider HTTP client closed")
