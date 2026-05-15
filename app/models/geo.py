"""Response models for the geolocation API."""

from pydantic import BaseModel, ConfigDict, Field


class Coordinates(BaseModel):
    """Geographic coordinates."""

    lat: float = Field(..., description="Latitude", examples=[51.5085])
    lon: float = Field(..., description="Longitude", examples=[-0.1257])


class GeolocationResponse(BaseModel):
    """Geolocation information for an IP address.

    Only ``ip``, ``country``, ``country_code`` and ``ip_version`` are guaranteed
    to be present. All other fields are optional: upstream providers (and the
    free GeoLite2 database) may omit them depending on the IP address or tier.
    Returning ``null`` instead of an empty string preserves the distinction
    between "missing data" and "empty value".
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ip": "8.8.8.8",
                "country": "United States",
                "country_code": "US",
                "region": "Virginia",
                "region_code": "VA",
                "city": "Ashburn",
                "zip_code": "20149",
                "coordinates": {"lat": 39.03, "lon": -77.5},
                "timezone": "America/New_York",
                "isp": "Google LLC",
                "org": "Google Public DNS",
                "ip_version": 4,
            }
        }
    )

    ip: str = Field(..., description="Queried IP address", examples=["8.8.8.8"])
    country: str = Field(..., description="Country name", examples=["United States"])
    country_code: str = Field(..., description="ISO 3166-1 alpha-2 country code", examples=["US"])
    region: str | None = Field(None, description="Region / state name", examples=["California"])
    region_code: str | None = Field(None, description="Region code", examples=["CA"])
    city: str | None = Field(None, description="City name", examples=["Mountain View"])
    zip_code: str | None = Field(None, description="ZIP / postal code", examples=["94043"])
    coordinates: Coordinates | None = Field(None, description="Geographic coordinates")
    timezone: str | None = Field(
        None, description="IANA timezone identifier", examples=["America/Los_Angeles"]
    )
    isp: str | None = Field(
        None, description="Internet Service Provider name", examples=["Google LLC"]
    )
    org: str | None = Field(
        None, description="Organisation name", examples=["AS15169 Google LLC"]
    )
    ip_version: int = Field(..., description="IP protocol version (4 or 6)", examples=[4])
