"""
AutoCognitix landing proxy — forwards whitelisted routes to the backend API.

Security posture:
  - All endpoints validated with Pydantic models.
  - Body size capped at 64KB before parsing.
  - Rate limiting per client IP (keyed correctly for IPv6).
  - Client IP is derived from the LAST entry of X-Forwarded-For, which nginx
    appends with `$proxy_add_x_forwarded_for` (only trusted when the peer is
    the local nginx sidecar).
  - Upstream 4xx bodies are forwarded verbatim (after content-type check)
    so UI gets actionable validation feedback. 5xx responses are sanitised.
  - Module-level httpx.AsyncClient with split connect/read/write/pool timeouts
    and a module-scope CSRF token cache (reduces backend QPS ~2x).
  - Responses are cached with an LRU+TTL (cachetools), not an unbounded dict.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import time
from contextlib import asynccontextmanager
from ipaddress import ip_address
from typing import Any, Awaitable, Callable, Dict, Iterable, Optional

import httpx
from cachetools import TTLCache
from pydantic import BaseModel, Field, ValidationError, constr
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from starlette.types import ASGIApp

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BACKEND_URL = os.getenv("BACKEND_URL", "https://autocognitix-production.up.railway.app")
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # seconds
CACHE_MAXSIZE = int(os.getenv("CACHE_MAXSIZE", "1000"))
RATE_LIMIT_PER_MINUTE = int(os.getenv("PROXY_RATE_LIMIT", "30"))
MAX_BODY_BYTES = int(os.getenv("PROXY_MAX_BODY_BYTES", str(64 * 1024)))  # 64 KB
MAX_QUERY_PARAMS = 16
MAX_QUERY_VALUE_LEN = 256
CSRF_TTL_SECONDS = int(os.getenv("PROXY_CSRF_TTL", "600"))  # 10 min

# Hosts we trust to have set X-Forwarded-For correctly. The proxy runs behind
# the local nginx sidecar (see nginx.conf: proxy_set_header X-Forwarded-For
# $proxy_add_x_forwarded_for). Only treat XFF as authoritative when the peer
# is one of these.
TRUSTED_PEER_IPS = {"127.0.0.1", "::1"}

# ---------------------------------------------------------------------------
# Logging (JSON-style, correlation via X-Request-ID)
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s rid=%(request_id)s %(message)s",
)


class _RequestIDFilter(logging.Filter):
    """Ensures %(request_id)s is always present on log records."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


log = logging.getLogger("proxy")
log.addFilter(_RequestIDFilter())
logging.getLogger().addFilter(_RequestIDFilter())

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

# Bounded LRU+TTL response cache (anonymous, no user data).
_cache: TTLCache = TTLCache(maxsize=CACHE_MAXSIZE, ttl=CACHE_TTL)

# Rate limit state: {client_ip: {minute_bucket: count}}. No colon parsing =>
# IPv6-safe.
_rate_limits: Dict[str, Dict[int, int]] = {}

# CSRF cache (module scope). asyncio.Lock guards the refresh.
_csrf_cache: Dict[str, Any] = {"token": None, "expires_at": 0.0}
_csrf_lock = asyncio.Lock()

# httpx client gets a lifespan-managed singleton.
_http_client: Optional[httpx.AsyncClient] = None


@asynccontextmanager
async def _lifespan(app: Starlette):
    """Open/close the shared httpx.AsyncClient."""
    global _http_client
    _http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=2.0),
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
        follow_redirects=False,
    )
    try:
        yield
    finally:
        await _http_client.aclose()
        _http_client = None


def _client() -> httpx.AsyncClient:
    if _http_client is None:
        raise RuntimeError("httpx client not initialized (lifespan not started)")
    return _http_client


# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------

_Str = constr(strip_whitespace=True, min_length=1, max_length=128)


class CalculatorRequest(BaseModel):
    vehicle_make: _Str
    vehicle_model: _Str
    vehicle_year: int = Field(ge=1950, le=2030)
    mileage_km: int = Field(ge=0, le=2_000_000)
    condition: constr(strip_whitespace=True, min_length=1, max_length=32)

    model_config = {"extra": "forbid"}


class InspectionRequest(BaseModel):
    vehicle_make: _Str
    vehicle_model: _Str
    vehicle_year: int = Field(ge=1950, le=2030)
    dtc_codes: list[constr(strip_whitespace=True, min_length=1, max_length=16)] = Field(
        min_length=1, max_length=50
    )

    model_config = {"extra": "forbid"}


# Allow-list of query params per GET endpoint.
_GET_PARAM_ALLOWLISTS: Dict[str, set[str]] = {
    "/api/v1/services/search": {"q", "category", "city", "region", "limit", "offset"},
    "/api/v1/dtc/search": {"q", "system", "limit", "offset", "lang"},
}


# ---------------------------------------------------------------------------
# Middleware: body size limit
# ---------------------------------------------------------------------------


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject request bodies larger than MAX_BODY_BYTES before handlers run."""

    def __init__(self, app: ASGIApp, max_bytes: int = MAX_BODY_BYTES) -> None:
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        cl = request.headers.get("content-length")
        if cl is not None:
            try:
                if int(cl) > self.max_bytes:
                    return JSONResponse(
                        {"data": None, "error": {"code": "PAYLOAD_TOO_LARGE", "message": "Request body exceeds limit"}, "meta": None},
                        status_code=413,
                    )
            except ValueError:
                return JSONResponse(
                    {"data": None, "error": {"code": "BAD_HEADER", "message": "Invalid Content-Length"}, "meta": None},
                    status_code=400,
                )
        return await call_next(request)


# ---------------------------------------------------------------------------
# Helpers: client IP, rate limit, cache key, CSRF, response shape
# ---------------------------------------------------------------------------


def _get_client_ip(request: Request) -> str:
    """
    Resolve the real client IP.

    nginx (see nginx.conf) forwards `X-Forwarded-For: $proxy_add_x_forwarded_for`
    which APPENDS $remote_addr. So the client's real IP is always the LAST
    comma-separated value. We only trust XFF when the peer is the local nginx
    sidecar (127.0.0.1 / ::1). Otherwise we fall back to the socket peer.
    """
    peer = request.client.host if request.client else ""
    forwarded = request.headers.get("x-forwarded-for", "").strip()
    if forwarded and peer in TRUSTED_PEER_IPS:
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        if parts:
            candidate = parts[-1]
            try:
                # Validate it's actually an IP — reject garbage like "attacker".
                ip_address(candidate)
                return candidate
            except ValueError:
                log.warning("Malformed XFF last-entry: %r", candidate)
    return peer or "unknown"


def _check_rate_limit(client_ip: str) -> tuple[bool, int, int]:
    """
    Returns (allowed, remaining, reset_epoch_seconds).

    Uses a dict-of-dicts (no string parsing) so IPv6 is safe.
    """
    now = time.time()
    current_minute = int(now // 60)

    per_ip = _rate_limits.get(client_ip)
    if per_ip is None:
        per_ip = {}
        _rate_limits[client_ip] = per_ip

    # Drop stale buckets for this IP (keep current only).
    stale = [m for m in per_ip if m < current_minute]
    for m in stale:
        del per_ip[m]
    if not per_ip:
        # Nothing left? Drop the IP's entry entirely on next pass.
        pass

    count = per_ip.get(current_minute, 0)
    reset_epoch = (current_minute + 1) * 60

    if count >= RATE_LIMIT_PER_MINUTE:
        return False, 0, reset_epoch

    per_ip[current_minute] = count + 1
    remaining = max(0, RATE_LIMIT_PER_MINUTE - per_ip[current_minute])

    # Opportunistic global cleanup: drop empty IP entries.
    if len(_rate_limits) > 10_000:
        for ip in list(_rate_limits.keys()):
            buckets = _rate_limits[ip]
            for m in list(buckets.keys()):
                if m < current_minute - 1:
                    del buckets[m]
            if not buckets:
                del _rate_limits[ip]

    return True, remaining, reset_epoch


def _rate_limited_response(reset_epoch: int) -> JSONResponse:
    retry_after = max(1, reset_epoch - int(time.time()))
    return JSONResponse(
        _envelope(error={"code": "RATE_LIMITED", "message": "Rate limit exceeded"}),
        status_code=429,
        headers={
            "Retry-After": str(retry_after),
            "X-RateLimit-Limit": str(RATE_LIMIT_PER_MINUTE),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(reset_epoch),
        },
    )


def _envelope(data: Any = None, error: Any = None, meta: Any = None) -> Dict[str, Any]:
    return {"data": data, "error": error, "meta": meta}


def _cache_key(path: str, payload: Any) -> str:
    body_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    return f"{path}:{body_hash}"


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id") or f"proxy-{int(time.time() * 1000)}"


def _sanitize_query_params(request: Request, backend_path: str) -> tuple[Optional[Dict[str, str]], Optional[JSONResponse]]:
    raw = list(request.query_params.multi_items())
    if len(raw) > MAX_QUERY_PARAMS:
        return None, JSONResponse(
            _envelope(error={"code": "TOO_MANY_PARAMS", "message": f"max {MAX_QUERY_PARAMS} query params"}),
            status_code=400,
        )
    allow = _GET_PARAM_ALLOWLISTS.get(backend_path)
    cleaned: Dict[str, str] = {}
    for k, v in raw:
        if allow is not None and k not in allow:
            continue
        if len(v) > MAX_QUERY_VALUE_LEN:
            return None, JSONResponse(
                _envelope(error={"code": "PARAM_TOO_LONG", "message": f"param {k!r} exceeds {MAX_QUERY_VALUE_LEN} chars"}),
                status_code=400,
            )
        cleaned[k] = v
    return cleaned, None


async def _get_csrf_token(request_id: str) -> Optional[str]:
    """
    Fetch-or-cache CSRF token. Short TTL + lazy refresh on 403.
    Single-flight via asyncio.Lock to avoid thundering herd.
    """
    now = time.time()
    token = _csrf_cache.get("token")
    if token and _csrf_cache.get("expires_at", 0) > now:
        return token

    async with _csrf_lock:
        # Double-check after acquiring lock.
        now = time.time()
        token = _csrf_cache.get("token")
        if token and _csrf_cache.get("expires_at", 0) > now:
            return token

        try:
            resp = await _client().get(
                f"{BACKEND_URL}/api/v1/health/status",
                headers={"Cache-Control": "no-store", "X-Request-ID": request_id},
            )
            resp.raise_for_status()
        except httpx.TimeoutException:
            log.warning("CSRF fetch timed out", extra={"request_id": request_id})
            return None
        except httpx.HTTPError as exc:
            log.warning("CSRF fetch failed: %s", exc, extra={"request_id": request_id})
            return None

        token = resp.cookies.get("csrf_token")
        if not token:
            log.warning("CSRF cookie missing from backend health response", extra={"request_id": request_id})
            return None
        _csrf_cache["token"] = token
        _csrf_cache["expires_at"] = now + CSRF_TTL_SECONDS
        return token


def _invalidate_csrf() -> None:
    _csrf_cache["token"] = None
    _csrf_cache["expires_at"] = 0.0


def _content_type_is_json(resp: httpx.Response) -> bool:
    ct = resp.headers.get("content-type", "").lower()
    return ct.startswith("application/json")


def _decode_upstream_json(resp: httpx.Response, request_id: str) -> Optional[Any]:
    """Defensive json decode; returns None if body isn't parseable JSON."""
    if not _content_type_is_json(resp):
        log.warning("Upstream non-JSON content-type: %s", resp.headers.get("content-type"),
                    extra={"request_id": request_id})
        return None
    try:
        return resp.json()
    except (json.JSONDecodeError, ValueError) as exc:
        log.warning("Upstream JSON decode failed: %s", exc, extra={"request_id": request_id})
        return None


def _cache_response_headers(etag: str) -> Dict[str, str]:
    return {
        "Cache-Control": f"public, max-age={CACHE_TTL}",
        "ETag": f'"{etag}"',
    }


# ---------------------------------------------------------------------------
# Core proxy logic
# ---------------------------------------------------------------------------


async def _proxy_post(
    request: Request,
    backend_path: str,
    validated_body: BaseModel,
) -> Response:
    request_id = _request_id(request)
    client_ip = _get_client_ip(request)

    allowed, remaining, reset_epoch = _check_rate_limit(client_ip)
    if not allowed:
        return _rate_limited_response(reset_epoch)

    payload = validated_body.model_dump(mode="json")
    cache_key = _cache_key(backend_path, payload)

    cached = _cache.get(cache_key)
    if cached is not None:
        etag = cache_key.split(":", 1)[1][:16]
        headers = {"X-Cache": "HIT", **_cache_response_headers(etag)}
        return JSONResponse(cached, headers=headers)

    async def _send(csrf_token: str) -> httpx.Response:
        return await _client().post(
            f"{BACKEND_URL}{backend_path}",
            json=payload,
            headers={
                "Content-Type": "application/json",
                "X-CSRF-Token": csrf_token,
                "X-Request-ID": request_id,
            },
            cookies={"csrf_token": csrf_token},
        )

    try:
        csrf_token = await _get_csrf_token(request_id)
        if not csrf_token:
            return JSONResponse(
                _envelope(error={"code": "UPSTREAM_UNAVAILABLE", "message": "Could not obtain CSRF token"}),
                status_code=502,
            )
        resp = await _send(csrf_token)

        # If the token was stale, invalidate + single retry.
        if resp.status_code == 403:
            log.info("CSRF rejected, refreshing token", extra={"request_id": request_id})
            _invalidate_csrf()
            csrf_token = await _get_csrf_token(request_id)
            if csrf_token:
                resp = await _send(csrf_token)
    except httpx.TimeoutException:
        log.warning("Upstream timeout on POST %s", backend_path, extra={"request_id": request_id})
        return JSONResponse(
            _envelope(error={"code": "UPSTREAM_TIMEOUT", "message": "Upstream service timed out"}),
            status_code=504,
        )
    except httpx.HTTPError as exc:
        log.warning("Upstream error on POST %s: %s", backend_path, exc, extra={"request_id": request_id})
        return JSONResponse(
            _envelope(error={"code": "UPSTREAM_ERROR", "message": "Upstream service error"}),
            status_code=502,
        )

    # 4xx: forward upstream body verbatim (helps UI show validation errors).
    if 400 <= resp.status_code < 500:
        body = _decode_upstream_json(resp, request_id)
        if body is None:
            # Non-JSON 4xx — don't leak raw HTML. Return sanitised error.
            return JSONResponse(
                _envelope(error={"code": "UPSTREAM_BAD_RESPONSE", "message": "Upstream returned non-JSON error"}),
                status_code=resp.status_code,
            )
        log.info("Upstream 4xx %s on %s", resp.status_code, backend_path,
                 extra={"request_id": request_id})
        return JSONResponse(body, status_code=resp.status_code)

    # 5xx: sanitised error. Log the body for operators.
    if resp.status_code >= 500:
        log.error("Upstream 5xx %s on %s: %s", resp.status_code, backend_path, resp.text[:500],
                  extra={"request_id": request_id})
        return JSONResponse(
            _envelope(error={"code": "UPSTREAM_ERROR", "message": "Upstream service error"}),
            status_code=502,
        )

    # 2xx happy path.
    data = _decode_upstream_json(resp, request_id)
    if data is None:
        return JSONResponse(
            _envelope(error={"code": "UPSTREAM_BAD_RESPONSE", "message": "Upstream returned non-JSON"}),
            status_code=502,
        )
    _cache[cache_key] = data
    etag = cache_key.split(":", 1)[1][:16]
    headers = {
        "X-Cache": "MISS",
        "X-RateLimit-Limit": str(RATE_LIMIT_PER_MINUTE),
        "X-RateLimit-Remaining": str(remaining),
        "X-RateLimit-Reset": str(reset_epoch),
        **_cache_response_headers(etag),
    }
    return JSONResponse(data, headers=headers)


async def _proxy_get(request: Request, backend_path: str) -> Response:
    request_id = _request_id(request)
    client_ip = _get_client_ip(request)

    allowed, remaining, reset_epoch = _check_rate_limit(client_ip)
    if not allowed:
        return _rate_limited_response(reset_epoch)

    params, err = _sanitize_query_params(request, backend_path)
    if err is not None:
        return err

    cache_key = _cache_key(backend_path, params)
    cached = _cache.get(cache_key)
    if cached is not None:
        etag = cache_key.split(":", 1)[1][:16]
        return JSONResponse(cached, headers={"X-Cache": "HIT", **_cache_response_headers(etag)})

    try:
        resp = await _client().get(
            f"{BACKEND_URL}{backend_path}",
            params=params,
            headers={"X-Request-ID": request_id},
        )
    except httpx.TimeoutException:
        log.warning("Upstream timeout on GET %s", backend_path, extra={"request_id": request_id})
        return JSONResponse(
            _envelope(error={"code": "UPSTREAM_TIMEOUT", "message": "Upstream timed out"}),
            status_code=504,
        )
    except httpx.HTTPError as exc:
        log.warning("Upstream error on GET %s: %s", backend_path, exc, extra={"request_id": request_id})
        return JSONResponse(
            _envelope(error={"code": "UPSTREAM_ERROR", "message": "Upstream service error"}),
            status_code=502,
        )

    if 400 <= resp.status_code < 500:
        body = _decode_upstream_json(resp, request_id)
        if body is None:
            return JSONResponse(
                _envelope(error={"code": "UPSTREAM_BAD_RESPONSE", "message": "Upstream returned non-JSON"}),
                status_code=resp.status_code,
            )
        return JSONResponse(body, status_code=resp.status_code)

    if resp.status_code >= 500:
        log.error("Upstream 5xx %s on GET %s: %s", resp.status_code, backend_path, resp.text[:500],
                  extra={"request_id": request_id})
        return JSONResponse(
            _envelope(error={"code": "UPSTREAM_ERROR", "message": "Upstream service error"}),
            status_code=502,
        )

    data = _decode_upstream_json(resp, request_id)
    if data is None:
        return JSONResponse(
            _envelope(error={"code": "UPSTREAM_BAD_RESPONSE", "message": "Upstream returned non-JSON"}),
            status_code=502,
        )
    _cache[cache_key] = data
    etag = cache_key.split(":", 1)[1][:16]
    return JSONResponse(
        data,
        headers={
            "X-Cache": "MISS",
            "X-RateLimit-Limit": str(RATE_LIMIT_PER_MINUTE),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_epoch),
            **_cache_response_headers(etag),
        },
    )


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


async def _parse_and_validate(request: Request, model_cls: type[BaseModel]) -> tuple[Optional[BaseModel], Optional[JSONResponse]]:
    try:
        raw = await request.body()
    except Exception as exc:  # pragma: no cover - Starlette raises specific types
        log.warning("Body read failed: %s", exc, extra={"request_id": _request_id(request)})
        return None, JSONResponse(
            _envelope(error={"code": "BAD_REQUEST", "message": "Unable to read body"}),
            status_code=400,
        )
    if len(raw) > MAX_BODY_BYTES:
        return None, JSONResponse(
            _envelope(error={"code": "PAYLOAD_TOO_LARGE", "message": "Request body exceeds limit"}),
            status_code=413,
        )
    try:
        body = json.loads(raw.decode("utf-8")) if raw else {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, JSONResponse(
            _envelope(error={"code": "INVALID_JSON", "message": "Invalid JSON body"}),
            status_code=400,
        )
    try:
        model = model_cls.model_validate(body)
    except ValidationError as exc:
        return None, JSONResponse(
            _envelope(error={"code": "VALIDATION_ERROR", "message": "Invalid input", "details": exc.errors()}),
            status_code=422,
        )
    return model, None


async def calculator_evaluate(request: Request) -> Response:
    model, err = await _parse_and_validate(request, CalculatorRequest)
    if err is not None:
        return err
    assert model is not None
    return await _proxy_post(request, "/api/v1/calculator/evaluate", model)


async def inspection_evaluate(request: Request) -> Response:
    model, err = await _parse_and_validate(request, InspectionRequest)
    if err is not None:
        return err
    assert model is not None
    return await _proxy_post(request, "/api/v1/inspection/evaluate", model)


async def services_search(request: Request) -> Response:
    return await _proxy_get(request, "/api/v1/services/search")


async def dtc_search(request: Request) -> Response:
    return await _proxy_get(request, "/api/v1/dtc/search")


_DTC_RE = re.compile(r"^[PBCU][0-9A-F]{4}$")


async def dtc_detail(request: Request) -> Response:
    raw_code = request.path_params.get("code", "")
    code = raw_code.strip().upper()
    if not _DTC_RE.match(code):
        return JSONResponse(
            _envelope(error={"code": "INVALID_DTC", "message": "Invalid DTC code format"}),
            status_code=400,
        )
    return await _proxy_get(request, f"/api/v1/dtc/{code}")


async def health(request: Request) -> Response:
    return JSONResponse(_envelope(data={"status": "ok", "service": "landing-proxy"}))


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

routes = [
    Route("/proxy/health", health),
    Route("/proxy/calculator/evaluate", calculator_evaluate, methods=["POST"]),
    Route("/proxy/inspection/evaluate", inspection_evaluate, methods=["POST"]),
    Route("/proxy/services/search", services_search),
    Route("/proxy/dtc/search", dtc_search),
    Route("/proxy/dtc/{code}", dtc_detail),
]

middleware = [
    Middleware(BodySizeLimitMiddleware, max_bytes=MAX_BODY_BYTES),
    Middleware(
        CORSMiddleware,
        allow_origins=[
            "https://autocognitix.hu",
            "https://www.autocognitix.hu",
            "https://autocognitix-landing-production.up.railway.app",
            "http://localhost:8080",
        ],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Request-ID"],
        max_age=600,
    ),
]

app = Starlette(routes=routes, middleware=middleware, lifespan=_lifespan)
