"""Response models for the geolocation API."""

from pydantic import BaseModel, Field


class Coordinates(BaseModel):
    """Geographic coordinates."""

    lat: float = Field(..., description="Latitude", examples=[51.5085])
    lon: float = Field(..., description="Longitude", examples=[-0.1257])


class GeolocationResponse(BaseModel):
    """Geolocation information for an IP address."""

    ip: str = Field(..., description="Queried IP address", examples=["8.8.8.8"])
    country: str = Field(..., description="Country name", examples=["United States"])
    country_code: str = Field(..., description="ISO 3166-1 alpha-2 country code", examples=["US"])
    region: str = Field(..., description="Region / state name", examples=["California"])
    region_code: str = Field(..., description="Region code", examples=["CA"])
    city: str = Field(..., description="City name", examples=["Mountain View"])
    zip_code: str = Field(..., description="ZIP / postal code", examples=["94043"])
    coordinates: Coordinates = Field(..., description="Geographic coordinates")
    timezone: str = Field(..., description="IANA timezone identifier", examples=["America/Los_Angeles"])
    isp: str = Field(..., description="Internet Service Provider name", examples=["Google LLC"])
    org: str = Field(..., description="Organisation name", examples=["AS15169 Google LLC"])
    ip_version: int = Field(..., description="IP protocol version (4 or 6)", examples=[4])
