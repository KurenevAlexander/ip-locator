"""FastAPI dependency functions shared across routers."""

from fastapi import Request


def get_client_ip(request: Request) -> str:
    """Detect the real client IP address from the incoming request.

    Resolution order:

    1. ``X-Forwarded-For`` header — leftmost entry (original client IP),
       set by reverse proxies such as nginx or AWS ALB.
    2. ``X-Real-IP`` header — set by nginx ``proxy_set_header X-Real-IP``.
    3. Direct connection IP from ``request.client.host``.

    Args:
        request: The current FastAPI/Starlette request object.

    Returns:
        The detected client IP address as a string.
        Falls back to ``"127.0.0.1"`` if no source yields an address
        (e.g. during unit tests without a real connection).
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For may be a comma-separated list; take the leftmost (original client)
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    if request.client:
        return request.client.host

    return "127.0.0.1"
