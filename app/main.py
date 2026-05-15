"""
FastAPI application factory.

Startup / teardown:
    The geolocation provider is created **once** inside the lifespan context
    manager and stored on ``app.state``. This ensures HTTP client connection
    pools and database handles are properly shared and cleaned up.

Exception handlers:
    All custom domain exceptions are mapped to consistent JSON error responses
    here, keeping routers and providers free of HTTP concerns.
    Every handled exception is logged so failures are visible in application logs.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.exceptions import (
    InvalidIPError,
    LocationNotFoundError,
    PrivateIPError,
    ProviderUnavailableError,
    RateLimitError,
)
from app.core.log import setup_logging
from app.models.errors import ErrorResponse
from app.providers import create_provider
from app.routers import geo

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown.

    On startup: configure logging, read settings, instantiate the provider.
    On shutdown: close the provider and release its resources.
    """
    setup_logging()
    settings = get_settings()
    logger.info("Starting IP Geolocation Service", extra={"provider": settings.geo_provider})
    provider = create_provider(settings)
    app.state.geo_provider = provider
    yield
    logger.info("Shutting down IP Geolocation Service")
    await provider.close()


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application.

    Returns:
        A fully configured :class:`fastapi.FastAPI` instance.
    """
    app = FastAPI(
        title="IP Geolocation Service",
        version="1.0.0",
        description=(
            "A microservice that returns geolocation information for IPv4 and IPv6 addresses. "
            "Backed by a configurable provider (ip-api.com, ipapi.co, or a local MaxMind database)."
        ),
        lifespan=lifespan,
    )

    app.include_router(geo.router)

    # Exception handlers
    @app.exception_handler(InvalidIPError)
    async def handle_invalid_ip(_: Request, exc: InvalidIPError) -> JSONResponse:
        logger.debug("Invalid IP address rejected", extra={"ip": exc.ip})
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error="invalid_ip",
                message=str(exc),
                detail="Both IPv4 and IPv6 addresses are accepted.",
            ).model_dump(),
        )

    @app.exception_handler(PrivateIPError)
    async def handle_private_ip(_: Request, exc: PrivateIPError) -> JSONResponse:
        logger.debug("Private IP address rejected", extra={"ip": exc.ip})
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error="private_ip",
                message=str(exc),
                detail="Geolocation is only available for public IP addresses.",
            ).model_dump(),
        )

    @app.exception_handler(LocationNotFoundError)
    async def handle_not_found(_: Request, exc: LocationNotFoundError) -> JSONResponse:
        logger.info("Geolocation not found", extra={"ip": exc.ip})
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error="location_not_found",
                message=str(exc),
                detail=None,
            ).model_dump(),
        )

    @app.exception_handler(RateLimitError)
    async def handle_rate_limit(_: Request, exc: RateLimitError) -> JSONResponse:
        logger.warning("Provider rate limit hit: %s", exc)
        return JSONResponse(
            status_code=429,
            content=ErrorResponse(
                error="rate_limit_exceeded",
                message=str(exc),
                detail="Please retry after 60 seconds.",
            ).model_dump(),
        )

    @app.exception_handler(ProviderUnavailableError)
    async def handle_provider_unavailable(_: Request, exc: ProviderUnavailableError) -> JSONResponse:
        logger.error("Provider unavailable: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=503,
            content=ErrorResponse(
                error="provider_unavailable",
                message=str(exc),
                detail="The geolocation provider is currently unreachable. Please try again later.",
            ).model_dump(),
        )

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
