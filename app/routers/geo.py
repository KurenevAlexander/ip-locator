"""Geolocation router — provides endpoints for IP lookup."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request

from app.dependencies import get_client_ip
from app.models.errors import ErrorResponse
from app.models.geo import GeolocationResponse
from app.providers import GeoProvider

router = APIRouter(prefix="/v1/geo", tags=["Geolocation"])

# Shared response definitions reused across endpoints
_error_responses: dict[int | str, dict[str, object]] = {
    400: {"model": ErrorResponse, "description": "Invalid or private IP address"},
    404: {"model": ErrorResponse, "description": "No geolocation data found for the IP"},
    429: {"model": ErrorResponse, "description": "Upstream provider rate limit exceeded"},
    503: {"model": ErrorResponse, "description": "Upstream provider unavailable"},
}


def _get_provider(request: Request) -> GeoProvider:
    """Retrieve the provider instance stored on application state."""
    return request.app.state.geo_provider  # type: ignore[no-any-return]


ProviderDep = Annotated[GeoProvider, Depends(_get_provider)]
ClientIPDep = Annotated[str, Depends(get_client_ip)]

# Path parameter declared once — reused only by /{ip}, but kept here so the
# OpenAPI examples and description stay close to other endpoint metadata.
IpPathParam = Annotated[
    str,
    Path(
        description="Public IPv4 or IPv6 address to look up.",
        examples=["8.8.8.8", "1.1.1.1", "2001:4860:4860::8888"],
    ),
]


@router.get(
    "/me",
    response_model=GeolocationResponse,
    responses=_error_responses,
    operation_id="get_my_geolocation",
    summary="Look up geolocation for the requesting client",
    description=(
        "Automatically detects the caller's IP address from the request "
        "(``X-Forwarded-For`` → ``X-Real-IP`` → direct connection) "
        "and returns its geolocation information."
    ),
)
async def get_my_geolocation(provider: ProviderDep, client_ip: ClientIPDep) -> GeolocationResponse:
    """Look up geolocation data for the IP address of the requesting client."""
    return await provider.locate(client_ip)


@router.get(
    "/{ip}",
    response_model=GeolocationResponse,
    responses=_error_responses,
    operation_id="get_geolocation_by_ip",
    summary="Look up geolocation for a specific IP address",
    description=(
        "Returns geolocation information (country, region, city, coordinates, timezone, ISP) "
        "for the supplied IPv4 or IPv6 address."
    ),
)
async def get_geolocation(ip: IpPathParam, provider: ProviderDep) -> GeolocationResponse:
    """Look up geolocation data for the provided IP address."""
    return await provider.locate(ip)
