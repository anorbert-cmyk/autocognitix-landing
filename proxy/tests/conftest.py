"""
Shared fixtures for proxy/ tests.

Design notes
------------
- We import `proxy.main` as `main` (via pyproject.toml pythonpath=".").
- Each test gets a fresh copy of `_cache`, `_rate_limits`, and `_csrf_cache`
  via the `clean_state` autouse fixture. Tests MUST NOT rely on state from
  other tests.
- We NEVER hit the real BACKEND_URL. All outbound httpx traffic is intercepted
  by `respx` (wire-level mock). That way we exercise the real CSRF+POST flow
  through `httpx.AsyncClient` without a live dependency.
- `TestClient` from Starlette runs the ASGI app in-process. CRUCIAL: we must
  use `with TestClient(app) as c:` so Starlette's lifespan fires and the
  module-level `_http_client` (httpx.AsyncClient) gets initialised. Without
  the context manager, every outbound request raises
  `RuntimeError: httpx client not initialized (lifespan not started)`.
  (See `main._lifespan` + `main._client`.)
"""

from __future__ import annotations

import sys
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
    """
    Reset ALL module-level mutable state between tests:
      - response cache
      - negative cache (404 short-TTL cache for identifier routes)
      - rate-limit counters
      - CSRF token cache (otherwise a test that populates the token poisons
        the failure-path test that expects a None token)
    """
    proxy_module._cache.clear()
    proxy_module._negative_cache.clear()
    proxy_module._rate_limits.clear()
    proxy_module._csrf_cache["token"] = None
    proxy_module._csrf_cache["expires_at"] = 0.0
    yield
    proxy_module._cache.clear()
    proxy_module._negative_cache.clear()
    proxy_module._rate_limits.clear()
    proxy_module._csrf_cache["token"] = None
    proxy_module._csrf_cache["expires_at"] = 0.0


@pytest.fixture()
def client(proxy_module):
    """
    Starlette TestClient inside a `with` block so that lifespan startup
    (which constructs the shared `httpx.AsyncClient`) actually runs.

    Using `TestClient(app)` without `with` leaves `_http_client = None` and
    every outbound request raises RuntimeError — the root cause of 16/23
    pre-fix test failures.
    """
    from starlette.testclient import TestClient
    with TestClient(proxy_module.app) as c:
        yield c


@pytest.fixture()
def backend_url(proxy_module):
    return proxy_module.BACKEND_URL
