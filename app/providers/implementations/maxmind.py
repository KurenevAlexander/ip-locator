"""MaxMind GeoLite2 local database provider implementation.

Requires the ``maxmind`` optional dependency group::

    poetry install --extras maxmind

And a downloaded ``GeoLite2-City.mmdb`` file. Configure its path via
``MAXMIND_DB_PATH`` (defaults to ``GeoLite2-City.mmdb`` in the working directory).

Free database: https://dev.maxmind.com/geoip/geolite2-free-geolocation-data
"""

import asyncio
import ipaddress
import logging
from functools import partial

from app.core.exceptions import LocationNotFoundError, ProviderUnavailableError
from app.models.geo import Coordinates, GeolocationResponse
from app.providers.base import GeoProvider

logger = logging.getLogger(__name__)

try:
    import geoip2.database
    import geoip2.errors

    _GEOIP2_AVAILABLE = True
except ImportError:
    _GEOIP2_AVAILABLE = False


class MaxMindProvider(GeoProvider):
    """Geolocation provider backed by a local MaxMind GeoLite2-City database.

    Lookups are purely in-process (no network I/O) so there are no rate limits
    and latency is minimal. The ``geoip2`` library uses synchronous file I/O,
    which is dispatched to a thread-pool executor to avoid blocking the async
    event loop.

    Note:
        Requires the ``maxmind`` optional extra and a downloaded ``.mmdb`` file.
        MaxMind releases database updates every Tuesday.
        The GeoLite2-City database does not include ISP data — use GeoIP2-ISP
        for that field.

    Args:
        db_path: Filesystem path to the ``GeoLite2-City.mmdb`` file.

    Raises:
        RuntimeError: If the ``geoip2`` package is not installed.
    """

    def __init__(self, db_path: str) -> None:
        if not _GEOIP2_AVAILABLE:
            raise RuntimeError(
                "The 'geoip2' package is required for the MaxMind provider. "
                "Install it with: poetry install --extras maxmind"
            )
        self._db_path = db_path
        self._reader: "geoip2.database.Reader | None" = None

    def _get_reader(self) -> "geoip2.database.Reader":
        """Open (or return the cached) database reader.

        Raises:
            ProviderUnavailableError: If the ``.mmdb`` file is not found.
        """
        if self._reader is None:
            try:
                self._reader = geoip2.database.Reader(self._db_path)
                logger.info("MaxMind database opened", extra={"path": self._db_path})
            except FileNotFoundError as exc:
                raise ProviderUnavailableError(
                    f"MaxMind database not found at '{self._db_path}'. "
                    "Download GeoLite2-City.mmdb from https://dev.maxmind.com/"
                ) from exc
        return self._reader

    def _lookup_sync(self, ip: str) -> GeolocationResponse:
        """Perform a synchronous database lookup (runs in a thread-pool executor).

        Args:
            ip: A validated public IP address string.

        Returns:
            Populated :class:`~app.models.geo.GeolocationResponse`.

        Raises:
            LocationNotFoundError: If the database has no record for *ip*.
        """
        addr = ipaddress.ip_address(ip)
        reader = self._get_reader()
        try:
            record = reader.city(ip)
        except geoip2.errors.AddressNotFoundError as exc:
            raise LocationNotFoundError(ip) from exc

        return GeolocationResponse(
            ip=ip,
            country=record.country.name or "",
            country_code=record.country.iso_code or "",
            region=record.subdivisions.most_specific.name or "",
            region_code=record.subdivisions.most_specific.iso_code or "",
            city=record.city.name or "",
            zip_code=record.postal.code or "",
            coordinates=Coordinates(
                lat=record.location.latitude or 0.0,
                lon=record.location.longitude or 0.0,
            ),
            timezone=record.location.time_zone or "",
            isp="",   # GeoLite2-City does not include ISP data
            org="",
            ip_version=addr.version,
        )

    async def locate(self, ip: str) -> GeolocationResponse:
        """Return geolocation data for the given IP address.

        Args:
            ip: A public IPv4 or IPv6 address string.

        Returns:
            Populated :class:`~app.models.geo.GeolocationResponse`.

        Raises:
            InvalidIPError: If *ip* is not a valid IP address.
            PrivateIPError: If *ip* is a private or reserved address.
            LocationNotFoundError: If the database has no record for *ip*.
            ProviderUnavailableError: If the ``.mmdb`` file cannot be opened.
        """
        self.validate_ip(ip)
        logger.debug("Locating IP via MaxMind", extra={"ip": ip})
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(self._lookup_sync, ip))

    async def close(self) -> None:
        """Close the database reader and release the file handle."""
        if self._reader is not None:
            self._reader.close()
            self._reader = None
            logger.debug("MaxMind database reader closed")
