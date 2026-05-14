"""Domain exceptions for the geolocation service.

All exceptions are raised by providers and caught by exception handlers
in ``app.main``. HTTP concerns (status codes, response bodies) live
exclusively in the handlers — not here.
"""


class InvalidIPError(ValueError):
    """Raised when the provided string is not a valid IP address.

    Args:
        ip: The invalid string that was supplied.
    """

    def __init__(self, ip: str) -> None:
        self.ip = ip
        super().__init__(f"'{ip}' is not a valid IP address.")


class PrivateIPError(ValueError):
    """Raised when the IP address belongs to a private or reserved range.

    Args:
        ip: The private/reserved IP address that was supplied.
    """

    def __init__(self, ip: str) -> None:
        self.ip = ip
        super().__init__(f"'{ip}' is a private or reserved IP address.")


class LocationNotFoundError(LookupError):
    """Raised when no geolocation data is available for the given IP.

    Args:
        ip: The IP address for which no data was found.
    """

    def __init__(self, ip: str) -> None:
        self.ip = ip
        super().__init__(f"No geolocation data found for '{ip}'.")


class RateLimitError(RuntimeError):
    """Raised when the upstream provider returns a rate-limit response (HTTP 429)."""


class ProviderUnavailableError(RuntimeError):
    """Raised when the upstream provider is unreachable or returns an unexpected error."""
