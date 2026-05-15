# IP Geolocation Service

A production-quality FastAPI microservice that returns geolocation information for IPv4 and IPv6 addresses. Backed by a configurable provider — by default uses [ip-api.com](http://ip-api.com) (free, no key required).

---

## Features

- `GET /v1/geo/{ip}` — geolocation for any public IPv4 or IPv6 address
- `GET /v1/geo/me` — auto-detects the caller's IP (`X-Forwarded-For` → `X-Real-IP` → direct connection)
- Pluggable provider architecture — switch between **ip-api.com** and **ipapi.co** via a single env variable
- Consistent JSON error responses for all failure cases (invalid IP, private IP, rate limit, provider unavailable)
- Interactive API docs at `/docs` (Swagger UI) and `/redoc` (ReDoc)

---

## Requirements

- Python 3.11+
- [Poetry](https://python-poetry.org/) 2.x

---

## Setup

### 1. Clone and install dependencies

```bash
git clone <repository-url>
cd ip-locator
poetry install
```

To also install dev dependencies (pytest, ruff, mypy):

```bash
poetry install --with dev
```

### 2. Configure environment (optional)

Copy the example env file and adjust if needed:

```bash
cp .env.example .env
```

The service works out of the box with defaults — no configuration required for the `ip_api` provider.

| Variable | Default | Description |
|---|---|---|
| `GEO_PROVIDER` | `ip_api` | Provider: `ip_api` \| `ipapi_co` |
| `GEO_API_KEY` | _(none)_ | API key for `ipapi_co` paid plan |
| `HTTP_TIMEOUT` | `5.0` | Outbound HTTP timeout in seconds |
| `LOG_LEVEL` | `INFO` | Log level: `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` |

---

## Running the service

```bash
poetry run uvicorn app.main:app --reload
```

Or via the module entry point:

```bash
poetry run python -m app.main
```

The service starts on `http://localhost:8000` by default.

---

## API Documentation

Once the service is running:

| URL | Description |
|---|---|
| http://localhost:8000/docs | Swagger UI (interactive) |
| http://localhost:8000/redoc | ReDoc |
| http://localhost:8000/openapi.json | Raw OpenAPI 3.1 spec |

---

## Running tests

```bash
poetry run python -m pytest -v
```

All tests use mocked HTTP — no network access required.

---

## End-to-end smoke test

Starts the server in a background thread and runs real HTTP requests against the live API:

```bash
poetry run python check_flow.py
```

---

## Project structure

```
ip-locator/
├── app/
│   ├── core/                   # Cross-cutting concerns
│   │   ├── config.py           # Settings (pydantic-settings, lru_cache)
│   │   ├── exceptions.py       # Domain exceptions
│   │   └── log.py              # Logging setup
│   ├── models/
│   │   ├── geo.py              # GeolocationResponse, Coordinates
│   │   └── errors.py           # ErrorResponse (HTTP layer)
│   ├── providers/
│   │   ├── base.py             # GeoProvider ABC + IP validation
│   │   ├── factory.py          # create_provider() — reads config, returns provider
│   │   └── implementations/
│   │       ├── ip_api.py       # ip-api.com provider
│   │       └── ipapi_co.py     # ipapi.co provider
│   ├── routers/
│   │   └── geo.py              # GET /v1/geo/{ip}, GET /v1/geo/me
│   ├── dependencies.py         # get_client_ip() DI function
│   └── main.py                 # App factory, lifespan, exception handlers
├── tests/
│   ├── test_config.py
│   ├── test_dependencies.py
│   ├── test_factory.py
│   ├── test_geo_router.py          # Integration tests (router layer)
│   ├── test_ip_api_provider.py     # Unit tests (ip-api.com)
│   └── test_ipapi_co_provider.py   # Unit tests (ipapi.co)
├── docs/
│   └── DEVELOPMENT_NOTES.md
├── check_flow.py               # End-to-end smoke test
├── .env.example
└── pyproject.toml
```

---

## Switching providers

Set `GEO_PROVIDER` in `.env` or as an environment variable:

```bash
# Use ipapi.co (optional key for higher quota)
GEO_PROVIDER=ipapi_co
GEO_API_KEY=your-key-here
```

---

## Example responses

### Successful lookup

```
GET /v1/geo/8.8.8.8
```

```json
{
    "ip": "8.8.8.8",
    "country": "United States",
    "country_code": "US",
    "region": "Virginia",
    "region_code": "VA",
    "city": "Ashburn",
    "zip_code": "20149",
    "coordinates": {
        "lat": 39.03,
        "lon": -77.5
    },
    "timezone": "America/New_York",
    "isp": "Google LLC",
    "org": "Google Public DNS",
    "ip_version": 4
}
```

### Error response

```
GET /v1/geo/192.168.1.1
```

```json
{
    "error": "private_ip",
    "message": "'192.168.1.1' is a private or reserved IP address.",
    "detail": "Geolocation is only available for public IP addresses."
}
```
