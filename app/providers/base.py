"""Abstract base class for all geolocation providers."""

import ipaddress
from abc import ABC, abstractmethod

from app.core.exceptions import InvalidIPError, PrivateIPError
from app.models.geo import GeolocationResponse


class GeoProvider(ABC):
    """Abstract interface for geolocation providers.

    All concrete providers must implement :meth:`locate` and :meth:`close`.
    The base class provides the shared :meth:`validate_ip` helper so validation
    logic is defined in exactly one place.

    To add a new provider:

    1. Create a module under ``app/providers/implementations/``.
    2. Subclass ``GeoProvider`` and implement :meth:`locate` and :meth:`close`.
    3. Export the class from ``implementations/__init__.py``.
    4. Add a branch in :func:`~app.providers.factory.create_provider`.
    """

    @abstractmethod
    async def locate(self, ip: str) -> GeolocationResponse:
        """Return geolocation information for *ip*.

        Args:
            ip: A public IPv4 or IPv6 address string.

        Returns:
            Populated :class:`~app.models.geo.GeolocationResponse`.

        Raises:
            InvalidIPError: If *ip* is not a valid IP address.
            PrivateIPError: If *ip* belongs to a private or reserved range.
            LocationNotFoundError: If no data is available for *ip*.
            RateLimitError: If the upstream provider is rate-limiting requests.
            ProviderUnavailableError: If the upstream provider is unreachable.
        """

    @abstractmethod
    async def close(self) -> None:
        """Release resources held by this provider.

        Examples of resources: HTTP client connection pools, database handles.
        Called automatically during application shutdown (lifespan teardown).
        """

    @staticmethod
    def validate_ip(ip: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
        """Parse and validate an IP address string.

        Args:
            ip: The string to validate.

        Returns:
            A parsed :class:`~ipaddress.IPv4Address` or
            :class:`~ipaddress.IPv6Address` instance.

        Raises:
            InvalidIPError: If *ip* is not a valid IPv4 or IPv6 address.
            PrivateIPError: If *ip* is private, loopback, reserved,
                or link-local.
        """
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            raise InvalidIPError(ip) from None

        if addr.is_private or addr.is_reserved or addr.is_loopback or addr.is_link_local:
            raise PrivateIPError(ip)

        return addr
