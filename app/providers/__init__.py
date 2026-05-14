"""Provider package — public API.

Consumers should import only from this module, not from submodules directly::

    from app.providers import GeoProvider, create_provider
"""

from app.providers.base import GeoProvider
from app.providers.factory import create_provider

__all__ = ["GeoProvider", "create_provider"]
