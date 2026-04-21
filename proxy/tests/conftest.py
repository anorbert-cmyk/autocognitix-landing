"""
Shared fixtures for proxy/ tests.

Design notes
------------
- We import `proxy.main` as `main` (via pyproject.toml pythonpath=".").
- Each test gets a fresh copy of `_cache` and `_rate_limits` via the
  `clean_state` autouse fixture. Tests MUST NOT rely on state from other tests.
- We NEVER hit the real BACKEND_URL. All outbound httpx traffic is intercepted
  by `respx` (wire-level mock). That way we exercise the real CSRF+POST flow
  through `httpx.AsyncClient` without a live dependency.
- `TestClient` from Starlette runs the ASGI app in-process. It handles X-Forwarded-For
  correctly as a raw header (see last-XFF test for the key behavior we defend).
"""

from __future__ import annotations

import os
import sys
import importlib
from pathlib import Path

import pytest

# Ensure proxy/ is on sys.path even if pyproject.toml pythonpath is not picked up
# (e.g. when running pytest from a different cwd).
_PROXY_DIR = Path(__file__).resolve().parent.parent
if str(_PROXY_DIR) not in sys.path:
    sys.path.insert(0, str(_PROXY_DIR))


@pytest.fixture(scope="session")
def anyio_backend():
    # pytest-asyncio honours this indirectly; harmless for pytest-asyncio users.
    return "asyncio"


@pytest.fixture()
def proxy_module():
    """
    Import `main` fresh for each test and return it.

    We DON'T use importlib.reload in the hot path because Starlette keeps route
    objects by identity; reloading would invalidate routes held by TestClient.
    Instead, we clear the module-level dicts via the `clean_state` fixture.
    """
    import main  # type: ignore
    return main


@pytest.fixture(autouse=True)
def clean_state(proxy_module):
    """Reset the in-memory cache and rate-limit counters between tests."""
    proxy_module._cache.clear()
    proxy_module._rate_limits.clear()
    yield
    proxy_module._cache.clear()
    proxy_module._rate_limits.clear()


@pytest.fixture()
def client(proxy_module):
    """
    Synchronous Starlette TestClient — fine for our needs because the ASGI app
    runs request handlers on the test event loop internally.
    """
    from starlette.testclient import TestClient
    return TestClient(proxy_module.app)


@pytest.fixture()
def backend_url(proxy_module):
    return proxy_module.BACKEND_URL
