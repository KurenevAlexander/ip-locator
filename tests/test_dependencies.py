"""Unit tests for get_client_ip dependency."""

from unittest.mock import MagicMock

from app.dependencies import get_client_ip


def _make_request(headers: dict | None = None, client_host: str | None = "203.0.113.10"):
    """Build a minimal mock Request with headers and client info."""
    req = MagicMock()
    req.headers = headers or {}
    req.client = MagicMock(host=client_host) if client_host else None
    return req


def test_x_forwarded_for_takes_precedence():
    req = _make_request(
        headers={"X-Forwarded-For": "8.8.8.8, 10.0.0.1", "X-Real-IP": "1.1.1.1"}
    )
    # Current behaviour: leftmost entry of X-Forwarded-For is returned.
    # (Trusted-proxy hardening is intentionally deferred — see DEVELOPMENT_NOTES.)
    assert get_client_ip(req) == "8.8.8.8"


def test_x_forwarded_for_single_value():
    req = _make_request(headers={"X-Forwarded-For": "8.8.8.8"})
    assert get_client_ip(req) == "8.8.8.8"


def test_x_forwarded_for_strips_whitespace():
    req = _make_request(headers={"X-Forwarded-For": "  8.8.8.8  ,  10.0.0.1"})
    assert get_client_ip(req) == "8.8.8.8"


def test_x_real_ip_used_when_no_forwarded_for():
    req = _make_request(headers={"X-Real-IP": "1.1.1.1"})
    assert get_client_ip(req) == "1.1.1.1"


def test_falls_back_to_request_client_host():
    req = _make_request(headers={}, client_host="203.0.113.10")
    assert get_client_ip(req) == "203.0.113.10"


def test_falls_back_to_loopback_when_no_client():
    req = _make_request(headers={}, client_host=None)
    assert get_client_ip(req) == "127.0.0.1"
