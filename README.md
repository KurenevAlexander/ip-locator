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

## Running in Docker

Build the image and run a container:

```bash
docker build -t ip-locator .
docker run --rm -p 8000:8000 ip-locator
```

The service then becomes available at `http://localhost:8000`.

To override configuration at runtime, pass environment variables with `-e`:

```bash
docker run --rm -p 8000:8000 \
    -e GEO_PROVIDER=ipapi_co \
    -e GEO_API_KEY=your-key-here \
    ip-locator
```

The `Dockerfile` is intentionally a single-stage build optimised for clarity.
See `docs/DEVELOPMENT_NOTES.md` for the multi-stage / non-root / healthcheck
hardening that would apply in production.

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

## API Design Decisions

This section summarises the key decisions behind the API contract.
A more detailed reflection (including alternatives considered and what would
change for a production deployment) lives in
[`docs/DEVELOPMENT_NOTES.md`](docs/DEVELOPMENT_NOTES.md).

### REST style and resource model

The service exposes a single resource — **geolocation** — addressed by an IP
address. Two read operations are provided:

| Endpoint | Purpose |
|---|---|
| `GET /v1/geo/{ip}` | Lookup by explicit IP address |
| `GET /v1/geo/me`   | Lookup for the caller's own IP (auto-detected) |

Both endpoints return the same response shape (`GeolocationResponse`) — the
only difference is **how the IP is supplied**. Keeping a single response model
across both endpoints lets clients share parsing code and keeps the OpenAPI
spec small.

### Versioning

All endpoints live under `/v1`. URL-prefix versioning is the simplest
mechanism that survives breaking changes without disrupting existing clients:
a future `/v2` can ship side-by-side and clients migrate on their own
schedule. Header-based versioning was considered but rejected as harder to
discover from Swagger UI and harder to cache through HTTP intermediaries.

### Idempotency, safety and caching

Both endpoints are `GET`, side-effect-free and **idempotent**. They are also
inherently cacheable: a given IP's geolocation changes rarely. The current
implementation does not cache, but the contract leaves the door open — any
HTTP cache (CDN, reverse proxy) can be placed in front of the service without
breaking semantics.

### Response shape

`GeolocationResponse` fields fall into two tiers:

- **Required** (`ip`, `country`, `country_code`, `ip_version`) — guaranteed to
  be present on a successful response.
- **Optional** (`region`, `city`, `zip_code`, `coordinates`, `timezone`, `isp`,
  `org`, …) — returned as `null` when the upstream source has no data.

Distinguishing **missing data** from **empty value** matters: a client receiving
`{"city": ""}` cannot tell whether the city is genuinely unknown or whether the
upstream returned an empty string. Explicit `null` removes that ambiguity. The
schema is documented in the OpenAPI spec with a full example payload.

### Error contract

All failures return the same `ErrorResponse` envelope:

```json
{ "error": "invalid_ip", "message": "...", "detail": "..." }
```

| HTTP | `error` code | Cause |
|---|---|---|
| 400 | `invalid_ip` | String is not a valid IPv4/IPv6 address |
| 400 | `private_ip` | Address is private, loopback or reserved |
| 404 | `location_not_found` | Upstream has no record for the address |
| 429 | `rate_limit_exceeded` | Upstream provider rate-limited the request |
| 503 | `provider_unavailable` | Upstream timeout / connection error / unexpected status |

The machine-readable `error` code is the **stable** part of the contract;
`message` and `detail` are human-friendly and may evolve. HTTP status codes
follow standard semantics so generic HTTP-aware clients can react correctly
without parsing the body.

Validation, business and upstream failures are raised as domain exceptions
from the providers and converted to HTTP responses in a single place
(`app/main.py`). This keeps providers and routers free of HTTP concerns and
guarantees a consistent error shape across all endpoints.

### Provider abstraction

`GeoProvider` is an `ABC` with two implementations (`ip-api.com`,
`ipapi.co`). The active provider is chosen at startup via the `GEO_PROVIDER`
environment variable, and the HTTP client is created once in the lifespan
context so connection pools are shared across requests. Adding a new
provider is a three-step change documented in the docstring of
`app/providers/factory.py`.

### Client IP detection (`/v1/geo/me`)

Resolution order: `X-Forwarded-For` (leftmost entry) → `X-Real-IP` →
`request.client.host` → `127.0.0.1` fallback. The current implementation
trusts forwarded headers unconditionally; production-grade hardening
(trusted-proxy whitelist, using the **rightmost** entry of the chain) is
listed in `DEVELOPMENT_NOTES.md` as a next step.

### What is intentionally **not** in the API

- No write endpoints — the service is read-only.
- No batch endpoint (`POST /v1/geo/lookup` with a list of IPs) — out of scope
  for the assignment; would be the obvious next addition.
- No authentication — the service is a thin gateway to public data. AuthN/Z
  belongs at the edge (API gateway, mTLS, JWT).

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
