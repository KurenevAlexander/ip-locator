"""HTTP error response model for the geolocation API."""

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Consistent error response returned by all endpoints on failure."""

    error: str = Field(
        ...,
        description="Machine-readable error code.",
        examples=["invalid_ip"],
    )
    message: str = Field(
        ...,
        description="Human-readable description of the error.",
        examples=["'999.x.x.x' is not a valid IP address."],
    )
    detail: str | None = Field(
        None,
        description="Optional additional context or remediation hint.",
        examples=["Both IPv4 and IPv6 addresses are accepted."],
    )
