"""End-to-end smoke test for the IP Geolocation service.

Starts uvicorn in a background thread, runs a few real HTTP requests against
the live API, prints the result of each check and exits with a non-zero code
if anything failed.

    poetry run python check_flow.py
"""

import asyncio
import json
import sys
import threading
import time

import httpx
import uvicorn

from app.main import create_app

HOST = "127.0.0.1"
PORT = 8765
BASE_URL = f"http://{HOST}:{PORT}"


# ---------------------------------------------------------------------------
# Tiny reporting helpers
# ---------------------------------------------------------------------------

_failures: list[str] = []


def section(title: str) -> None:
    print(f"\n--- {title} ---")


def check(condition: bool, message: str) -> None:
    """Record a single assertion."""
    if condition:
        print(f"  OK   {message}")
    else:
        print(f"  FAIL {message}")
        _failures.append(message)


# ---------------------------------------------------------------------------
# Server lifecycle
# ---------------------------------------------------------------------------

def start_server() -> None:
    """Run uvicorn in a daemon thread and wait until it answers."""

    def _serve() -> None:
        config = uvicorn.Config(
            app=create_app(),
            host=HOST,
            port=PORT,
            log_level="warning",
        )
        uvicorn.Server(config).run()

    threading.Thread(target=_serve, daemon=True).start()

    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            httpx.get(f"{BASE_URL}/docs", timeout=1)
            return
        except httpx.RequestError:
            time.sleep(0.2)
    print("Server did not start in time.")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

async def run_checks() -> None:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10) as client:
        await check_docs(client)
        await check_happy_path(client)
        await check_me_endpoint(client)
        await check_invalid_ips(client)
        await check_private_ips(client)
        await check_response_schema(client)


async def check_docs(client: httpx.AsyncClient) -> None:
    section("OpenAPI and interactive docs")
    for path in ("/openapi.json", "/docs", "/redoc"):
        r = await client.get(path)
        check(r.status_code == 200, f"GET {path} -> {r.status_code}")


async def check_happy_path(client: httpx.AsyncClient) -> None:
    section("Happy path lookups")
    cases = [
        ("8.8.8.8", 4),
        ("1.1.1.1", 4),
        ("2001:4860:4860::8888", 6),
    ]
    for ip, expected_version in cases:
        r = await client.get(f"/v1/geo/{ip}")
        if r.status_code != 200:
            check(False, f"GET /v1/geo/{ip} -> {r.status_code} (body: {r.text[:120]})")
            continue
        data = r.json()
        check(data["ip_version"] == expected_version, f"{ip}: ip_version={data['ip_version']}")
        check(bool(data["country"]), f"{ip}: country={data['country']}")


async def check_me_endpoint(client: httpx.AsyncClient) -> None:
    section("GET /v1/geo/me")

    # No proxy headers -> client IP is loopback -> 400 private_ip
    r = await client.get("/v1/geo/me")
    check(
        r.status_code == 400 and r.json().get("error") == "private_ip",
        f"no headers (loopback) -> {r.status_code} {r.json().get('error')}",
    )

    # With X-Forwarded-For
    r = await client.get("/v1/geo/me", headers={"X-Forwarded-For": "8.8.8.8"})
    check(
        r.status_code == 200 and r.json().get("ip") == "8.8.8.8",
        f"X-Forwarded-For: 8.8.8.8 -> {r.status_code}",
    )

    # With X-Real-IP
    r = await client.get("/v1/geo/me", headers={"X-Real-IP": "1.1.1.1"})
    check(
        r.status_code == 200 and r.json().get("ip") == "1.1.1.1",
        f"X-Real-IP: 1.1.1.1 -> {r.status_code}",
    )


async def check_invalid_ips(client: httpx.AsyncClient) -> None:
    section("Invalid IP addresses")
    for bad_ip in ("not-an-ip", "999.999.999.999", "abc.def.ghi.jkl"):
        r = await client.get(f"/v1/geo/{bad_ip}")
        check(
            r.status_code == 400 and r.json().get("error") == "invalid_ip",
            f"'{bad_ip}' -> {r.status_code} {r.json().get('error')}",
        )


async def check_private_ips(client: httpx.AsyncClient) -> None:
    section("Private / reserved IP addresses")
    for private_ip in ("10.0.0.1", "192.168.1.100", "172.16.0.1", "127.0.0.1"):
        r = await client.get(f"/v1/geo/{private_ip}")
        check(
            r.status_code == 400 and r.json().get("error") == "private_ip",
            f"'{private_ip}' -> {r.status_code} {r.json().get('error')}",
        )


async def check_response_schema(client: httpx.AsyncClient) -> None:
    section("Response schema")
    r = await client.get("/v1/geo/8.8.4.4")
    if r.status_code != 200:
        check(False, f"GET /v1/geo/8.8.4.4 -> {r.status_code}")
        return

    data = r.json()
    required = [
        "ip", "country", "country_code", "region", "region_code",
        "city", "zip_code", "coordinates", "timezone", "isp", "org", "ip_version",
    ]
    missing = [f for f in required if f not in data]
    check(not missing, f"all expected fields present (missing: {missing or 'none'})")
    check(data.get("ip_version") in (4, 6), f"ip_version is 4 or 6: {data.get('ip_version')}")

    coords = data.get("coordinates") or {}
    check("lat" in coords and "lon" in coords, "coordinates has lat and lon")

    print("  Sample payload:")
    print(json.dumps(data, indent=2))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print(f"Starting server on {BASE_URL} ...")
    start_server()
    print("Server is up.")

    asyncio.run(run_checks())

    print()
    if _failures:
        print(f"FAILED: {len(_failures)} check(s) did not pass")
        for msg in _failures:
            print(f"  - {msg}")
        sys.exit(1)

    print("All checks passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
