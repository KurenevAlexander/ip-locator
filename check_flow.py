"""
check_flow.py — End-to-end smoke test for the IP Geolocation service.

Starts the uvicorn server in a background thread, runs a series of real HTTP
requests against it, prints coloured results, then shuts the server down.

Usage:
    poetry run python check_flow.py

No external dependencies beyond what is already in pyproject.toml.
"""

import asyncio
import json
import sys
import threading
import time

import httpx
import uvicorn

from app.main import create_app

# ---------------------------------------------------------------------------
# Colour helpers (no deps)
# ---------------------------------------------------------------------------
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def ok(msg: str) -> None:
    print(f"  {GREEN}✓{RESET}  {msg}")


def fail(msg: str) -> None:
    print(f"  {RED}✗{RESET}  {msg}")


def info(msg: str) -> None:
    print(f"  {CYAN}→{RESET}  {msg}")


def section(title: str) -> None:
    print(f"\n{BOLD}{YELLOW}{'─' * 60}{RESET}")
    print(f"{BOLD}{YELLOW}  {title}{RESET}")
    print(f"{BOLD}{YELLOW}{'─' * 60}{RESET}")


def dump(data: dict) -> None:
    print(DIM + json.dumps(data, indent=4, ensure_ascii=False) + RESET)


# ---------------------------------------------------------------------------
# Server lifecycle
# ---------------------------------------------------------------------------

HOST = "127.0.0.1"
PORT = 8765
BASE_URL = f"http://{HOST}:{PORT}"


def _run_server() -> None:
    application = create_app()
    config = uvicorn.Config(
        app=application,
        host=HOST,
        port=PORT,
        log_level="warning",   # suppress uvicorn request logs — we print our own
    )
    server = uvicorn.Server(config)
    server.run()


def start_server() -> threading.Thread:
    thread = threading.Thread(target=_run_server, daemon=True)
    thread.start()
    # Wait until the server is ready
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            httpx.get(f"{BASE_URL}/docs", timeout=1)
            return thread
        except httpx.RequestError:
            time.sleep(0.2)
    print(f"{RED}Server did not start in time.{RESET}")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

async def run_checks() -> int:
    """Run all checks. Returns number of failures."""
    failures = 0

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10) as client:

        # ------------------------------------------------------------------ 1
        section("1 · OpenAPI & Interactive Docs")

        r = await client.get("/openapi.json")
        if r.status_code == 200:
            spec = r.json()
            ok(f"GET /openapi.json → 200  (title: \"{spec['info']['title']}\", version: {spec['info']['version']})")
        else:
            fail(f"GET /openapi.json → {r.status_code}")
            failures += 1

        r = await client.get("/docs")
        if r.status_code == 200:
            ok("GET /docs (Swagger UI) → 200")
        else:
            fail(f"GET /docs → {r.status_code}")
            failures += 1

        r = await client.get("/redoc")
        if r.status_code == 200:
            ok("GET /redoc (ReDoc) → 200")
        else:
            fail(f"GET /redoc → {r.status_code}")
            failures += 1

        # ------------------------------------------------------------------ 2
        section("2 · Happy Path — IPv4 (8.8.8.8 — Google DNS)")

        r = await client.get("/v1/geo/8.8.8.8")
        info(f"GET /v1/geo/8.8.8.8 → {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            dump(data)
            ok(f"ip={data['ip']}  country={data['country']}  city={data['city']}")
            ok(f"coordinates=({data['coordinates']['lat']}, {data['coordinates']['lon']})")
            ok(f"timezone={data['timezone']}  isp={data['isp']}")
            ok(f"ip_version={data['ip_version']}")
        else:
            fail(f"Unexpected status {r.status_code}: {r.text}")
            failures += 1

        # ------------------------------------------------------------------ 3
        section("3 · Happy Path — IPv4 (1.1.1.1 — Cloudflare DNS)")

        r = await client.get("/v1/geo/1.1.1.1")
        info(f"GET /v1/geo/1.1.1.1 → {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            dump(data)
            ok(f"ip={data['ip']}  country={data['country']}  city={data['city']}")
        else:
            fail(f"Unexpected status {r.status_code}: {r.text}")
            failures += 1

        # ------------------------------------------------------------------ 4
        section("4 · Happy Path — IPv6 (2001:4860:4860::8888 — Google DNS)")

        r = await client.get("/v1/geo/2001:4860:4860::8888")
        info(f"GET /v1/geo/2001:4860:4860::8888 → {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            dump(data)
            ok(f"ip={data['ip']}  country={data['country']}  ip_version={data['ip_version']}")
        else:
            fail(f"Unexpected status {r.status_code}: {r.text}")
            failures += 1

        # ------------------------------------------------------------------ 5
        section("5 · GET /v1/geo/me — auto-detect client IP")

        # Without proxy headers → will use 127.0.0.1 (loopback = private)
        r = await client.get("/v1/geo/me")
        info(f"GET /v1/geo/me (no headers, loopback) → {r.status_code}")
        if r.status_code == 400:
            data = r.json()
            ok(f"Correctly rejected loopback: error={data['error']}")
            dump(data)
        else:
            fail(f"Expected 400 for loopback IP, got {r.status_code}: {r.text}")
            failures += 1

        # With X-Forwarded-For → should resolve the real IP
        r = await client.get("/v1/geo/me", headers={"X-Forwarded-For": "8.8.8.8"})
        info(f"GET /v1/geo/me (X-Forwarded-For: 8.8.8.8) → {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            dump(data)
            ok(f"Resolved client IP: {data['ip']}  country={data['country']}")
        else:
            fail(f"Unexpected status {r.status_code}: {r.text}")
            failures += 1

        # With X-Real-IP
        r = await client.get("/v1/geo/me", headers={"X-Real-IP": "1.1.1.1"})
        info(f"GET /v1/geo/me (X-Real-IP: 1.1.1.1) → {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            ok(f"Resolved via X-Real-IP: {data['ip']}  country={data['country']}")
        else:
            fail(f"Unexpected status {r.status_code}: {r.text}")
            failures += 1

        # ------------------------------------------------------------------ 6
        section("6 · Error Handling — Invalid IP")

        for bad_ip in ["not-an-ip", "999.999.999.999", "abc.def.ghi.jkl"]:
            r = await client.get(f"/v1/geo/{bad_ip}")
            data = r.json()
            if r.status_code == 400 and data.get("error") == "invalid_ip":
                ok(f"'{bad_ip}' → 400 invalid_ip ✓")
            else:
                fail(f"'{bad_ip}' → {r.status_code} {data}")
                failures += 1

        # ------------------------------------------------------------------ 7
        section("7 · Error Handling — Private / Reserved IP")

        for private_ip in ["10.0.0.1", "192.168.1.100", "172.16.0.1", "127.0.0.1"]:
            r = await client.get(f"/v1/geo/{private_ip}")
            data = r.json()
            if r.status_code == 400 and data.get("error") == "private_ip":
                ok(f"'{private_ip}' → 400 private_ip ✓")
            else:
                fail(f"'{private_ip}' → {r.status_code} {data}")
                failures += 1

        # ------------------------------------------------------------------ 8
        section("8 · Response Schema Validation")

        r = await client.get("/v1/geo/8.8.4.4")
        if r.status_code == 200:
            data = r.json()
            required_fields = [
                "ip", "country", "country_code", "region", "region_code",
                "city", "zip_code", "coordinates", "timezone", "isp", "org", "ip_version",
            ]
            missing = [f for f in required_fields if f not in data]
            if not missing:
                ok(f"All {len(required_fields)} required fields present in response")
            else:
                fail(f"Missing fields: {missing}")
                failures += 1

            coord_fields = ["lat", "lon"]
            missing_coord = [f for f in coord_fields if f not in data.get("coordinates", {})]
            if not missing_coord:
                ok("coordinates.lat and coordinates.lon present")
            else:
                fail(f"Missing coordinate fields: {missing_coord}")
                failures += 1

            if data["ip_version"] in (4, 6):
                ok(f"ip_version is valid integer: {data['ip_version']}")
            else:
                fail(f"ip_version unexpected value: {data['ip_version']}")
                failures += 1
        else:
            fail(f"Schema check skipped — GET /v1/geo/8.8.4.4 returned {r.status_code}")
            failures += 1

    return failures


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print(f"\n{BOLD}{'═' * 60}{RESET}")
    print(f"{BOLD}  IP Geolocation Service — End-to-End Check{RESET}")
    print(f"{BOLD}{'═' * 60}{RESET}")
    print(f"\n  Starting server on {BASE_URL} …")

    start_server()
    print(f"  {GREEN}Server is up.{RESET}\n")

    failures = asyncio.run(run_checks())

    print(f"\n{BOLD}{'═' * 60}{RESET}")
    if failures == 0:
        print(f"{BOLD}{GREEN}  ALL CHECKS PASSED ✓{RESET}")
    else:
        print(f"{BOLD}{RED}  {failures} CHECK(S) FAILED ✗{RESET}")
    print(f"{BOLD}{'═' * 60}{RESET}\n")

    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    main()
