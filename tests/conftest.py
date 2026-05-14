"""Shared pytest fixtures."""

import pytest
import pytest_asyncio
import respx
from httpx import AsyncClient

from app.main import create_app


@pytest.fixture
def mock_ip_api():
    """Context manager that mocks all HTTP calls to ip-api.com."""
    with respx.mock(base_url="http://ip-api.com") as mock:
        yield mock


@pytest_asyncio.fixture
async def client(mock_ip_api):
    """Async test client with a real app but mocked HTTP backend."""
    app = create_app()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
