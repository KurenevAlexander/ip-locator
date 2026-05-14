"""Provider factory — instantiates the configured GeoProvider.

Adding a new provider requires:

1. Implementing :class:`~app.providers.base.GeoProvider` in ``implementations/``.
2. Exporting it from ``implementations/__init__.py``.
3. Adding a ``case`` branch below.
"""

import logging

import httpx

from app.core.config import Settings
from app.providers.base import GeoProvider

logger = logging.getLogger(__name__)


def create_provider(settings: Settings) -> GeoProvider:
    """Instantiate and return the geolocation provider specified in *settings*.

    Args:
        settings: Application settings carrying ``geo_provider``,
            ``geo_api_key``, ``maxmind_db_path``, and ``http_timeout``.

    Returns:
        A ready-to-use :class:`~app.providers.base.GeoProvider` instance.

    Raises:
        ValueError: If ``settings.geo_provider`` is not a recognised value.
    """
    timeout = httpx.Timeout(settings.http_timeout)
    logger.info("Creating geolocation provider", extra={"provider": settings.geo_provider})

    match settings.geo_provider:
        case "ip_api":
            from app.providers.implementations.ip_api import IpApiProvider

            return IpApiProvider(client=httpx.AsyncClient(timeout=timeout))

        case "ipapi_co":
            from app.providers.implementations.ipapi_co import IpapiCoProvider

            return IpapiCoProvider(
                client=httpx.AsyncClient(timeout=timeout),
                api_key=settings.geo_api_key,
            )

        case "maxmind":
            from app.providers.implementations.maxmind import MaxMindProvider

            return MaxMindProvider(db_path=settings.maxmind_db_path)

        case _:
            raise ValueError(
                f"Unknown GEO_PROVIDER '{settings.geo_provider}'. "
                "Supported values: ip_api, ipapi_co, maxmind."
            )
