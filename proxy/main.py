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
import ipaddress
import json
import logging
import os
import re
import time
import uuid
from collections import OrderedDict
from contextlib import asynccontextmanager
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Literal, Optional, Tuple

import httpx
from cachetools import TTLCache
from pydantic import BaseModel, Field, ValidationError, constr, field_validator
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

ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
BACKEND_URL = os.getenv("BACKEND_URL", "")
if not BACKEND_URL:
    if ENVIRONMENT == "production":
        raise RuntimeError(
            "BACKEND_URL must be set when ENVIRONMENT=production "
            "(refusing to silently default to the prod backend)"
        )
    BACKEND_URL = "https://autocognitix-production.up.railway.app"


def _validate_backend_url(url: str) -> None:
    """Wave 6 SSRF fix: reject BACKEND_URL that points at internal/metadata IPs.

    Without this, a misconfigured Railway env or compromised secret store can
    set BACKEND_URL=http://169.254.169.254/... (AWS/GCP metadata) and the
    first CSRF prefetch exfiltrates IAM credentials into the cache.
    """
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
    except Exception as exc:
        raise RuntimeError(f"BACKEND_URL is unparseable: {exc}") from exc
    if parsed.scheme not in ("http", "https"):
        raise RuntimeError(f"BACKEND_URL must be http(s), got scheme={parsed.scheme!r}")
    if ENVIRONMENT == "production" and parsed.scheme != "https":
        raise RuntimeError("BACKEND_URL must use https in production")
    if not parsed.hostname:
        raise RuntimeError("BACKEND_URL is missing hostname")
    # Reject known SSRF targets. This cannot catch all private IPs without a
    # DNS lookup (which we don't want to do at import time), but it blocks the
    # most common cloud-metadata attack vectors plus loopback literals. The
    # hostname autocognitix-production.up.railway.app resolves only at request
    # time; httpx + Railway DNS handle that path.
    SSRF_LITERAL_DENY = (
        "169.254.169.254",   # AWS, GCP, Azure metadata (also Railway internal)
        "metadata.google.internal",
        "metadata.azure.com",
        "metadata.gce",
        "127.0.0.1", "localhost", "0.0.0.0",
        "::1",
    )
    if ENVIRONMENT == "production":
        host_lower = parsed.hostname.lower()
        if host_lower in SSRF_LITERAL_DENY or host_lower.startswith("169.254."):
            raise RuntimeError(f"BACKEND_URL points at forbidden host: {host_lower!r}")


_validate_backend_url(BACKEND_URL)
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # seconds
CACHE_MAXSIZE = int(os.getenv("CACHE_MAXSIZE", "1000"))
# NOTE: this limit is PER WORKER PROCESS. The proxy runs with uvicorn
# --workers 1 (see start.sh), so the limit == advertised value. If workers>1
# is ever enabled, the effective rate limit multiplies by N — either move
# _rate_limits to Redis or divide this value by worker count at startup.
RATE_LIMIT_PER_MINUTE = int(os.getenv("PROXY_RATE_LIMIT", "30"))
MAX_BODY_BYTES = int(os.getenv("PROXY_MAX_BODY_BYTES", str(64 * 1024)))  # 64 KB
MAX_RESPONSE_BYTES = int(os.getenv("PROXY_MAX_RESPONSE_BYTES", str(5 * 1024 * 1024)))  # 5 MB
MAX_QUERY_PARAMS = 16
MAX_QUERY_VALUE_LEN = 256
CSRF_TTL_SECONDS = int(os.getenv("PROXY_CSRF_TTL", "600"))  # 10 min
NEGATIVE_CACHE_TTL = int(os.getenv("PROXY_NEGATIVE_CACHE_TTL", "60"))  # seconds
NEGATIVE_CACHE_MAXSIZE = int(os.getenv("PROXY_NEGATIVE_CACHE_MAXSIZE", "10000"))
RATE_LIMIT_MAX_ENTRIES = int(os.getenv("PROXY_RATE_LIMIT_MAX_ENTRIES", "10000"))
# Total wall-time per upstream request. httpx Timeout(read=...) is per-chunk —
# a slow-drip backend (e.g. 8KB every 14s) can hold a connection open for hours
# before the body cap is reached. asyncio.wait_for(_read_capped) bounds it.
PROXY_REQUEST_TOTAL_TIMEOUT = float(os.getenv("PROXY_REQUEST_TOTAL_TIMEOUT", "30.0"))

# Hosts we trust to have set X-Forwarded-For correctly. The proxy runs behind
# the local nginx sidecar (see nginx.conf: proxy_set_header X-Forwarded-For
# $proxy_add_x_forwarded_for). Only treat XFF as authoritative when the peer
# is one of these.
#
# Why CIDR (RFC 7239 + RFC 4291 §2.5.5.2): in containers / dual-stack stacks
# the peer can present as `::ffff:127.0.0.1` (IPv4-mapped IPv6) or via the
# Docker bridge network (172.17.0.0/16). A literal-string set misses these and
# silently drops XFF parsing — that means rate-limit keys collapse onto the
# loopback peer IP and the WHOLE proxy becomes trivially bypassable from
# outside the sidecar topology.
TRUSTED_PEER_NETWORKS: list[ipaddress._BaseNetwork] = [
    ipaddress.ip_network("127.0.0.0/8"),            # IPv4 loopback (RFC 1122)
    ipaddress.ip_network("::1/128"),                # IPv6 loopback
    ipaddress.ip_network("::ffff:127.0.0.0/104"),   # IPv4-mapped IPv6 loopback (RFC 4291)
]
# Optional: extra trusted networks via env, comma-separated CIDRs.
# e.g. PROXY_TRUSTED_PEER_CIDRS="172.17.0.0/16,10.0.0.0/8"
_extra_cidrs = os.getenv("PROXY_TRUSTED_PEER_CIDRS", "").strip()
if _extra_cidrs:
    for _cidr in _extra_cidrs.split(","):
        _cidr = _cidr.strip()
        if not _cidr:
            continue
        try:
            TRUSTED_PEER_NETWORKS.append(ipaddress.ip_network(_cidr, strict=False))
        except ValueError:
            logging.getLogger("proxy").warning("Ignoring malformed PROXY_TRUSTED_PEER_CIDRS entry: %r", _cidr)


def _is_trusted_peer(client_host: str) -> bool:
    """
    True when the socket peer falls inside one of TRUSTED_PEER_NETWORKS.

    We CIDR-match instead of string-equality because the peer can legitimately
    present as `127.0.0.1`, `::1`, `::ffff:127.0.0.1`, or a Docker bridge IP
    depending on how the listener is bound. A string set misses the IPv4-mapped
    IPv6 form and any container-network address.
    """
    if not client_host:
        return False
    try:
        ip = ipaddress.ip_address(client_host)
    except ValueError:
        return False
    return any(ip in net for net in TRUSTED_PEER_NETWORKS)


# Backwards-compat shim: some tests / external code still reference the old
# string set. Keep it in sync with the canonical loopback CIDRs so anyone
# inspecting it still sees the right semantics; do NOT use it for trust checks.
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

# Negative cache for upstream 404s on identifier lookups (e.g. /proxy/dtc/<code>).
# Without this, an attacker can crawl arbitrary unknown codes and force a
# round-trip to the backend on every request — a trivial cache-bypass DoS.
# 60s TTL is short enough that a real backend recovery (codes added to the DB)
# becomes visible to clients within one minute.
_negative_cache: TTLCache = TTLCache(maxsize=NEGATIVE_CACHE_MAXSIZE, ttl=NEGATIVE_CACHE_TTL)

# Rate limit state: OrderedDict so we can FIFO-evict the OLDEST entry when we
# exceed RATE_LIMIT_MAX_ENTRIES. Key = (client_ip, minute_bucket); value = count.
#
# Why FIFO over LRU: LRU evicts the LEAST-recently-touched entry. Under attack,
# attacker traffic is the most-recently-touched, so legitimate users (whose
# entries are quietly aging in the background) get evicted first — and then
# they re-enter with a fresh counter, which means the rate limiter helps the
# legit user reset and helps the attacker stay above the limit. FIFO eviction
# (popitem(last=False)) drops whatever was inserted earliest, regardless of
# recent activity, so an attacker burst can't selectively wipe innocents.
_rate_limits: "OrderedDict[Tuple[str, int], int]" = OrderedDict()

# CSRF cache (module scope). asyncio.Lock guards the refresh.
_csrf_cache: Dict[str, Any] = {"token": None, "expires_at": 0.0}
_csrf_lock = asyncio.Lock()

# httpx client gets a lifespan-managed singleton.
_http_client: Optional[httpx.AsyncClient] = None


# Wave 6 race fix: track in-flight requests so lifespan drain waits for them
# before closing the httpx client. Previously `aclose()` fired while in-flight
# `async with .stream()` contexts held connections → every deploy produced 502s
# and mid-body truncation.
_inflight_counter = 0
_inflight_zero_event = asyncio.Event()
_inflight_zero_event.set()  # starts at 0
_shutting_down = False


def _inflight_inc() -> None:
    global _inflight_counter
    _inflight_counter += 1
    _inflight_zero_event.clear()


def _inflight_dec() -> None:
    global _inflight_counter
    _inflight_counter -= 1
    if _inflight_counter <= 0:
        _inflight_counter = 0
        _inflight_zero_event.set()


@asynccontextmanager
async def _lifespan(app: Starlette):
    """Open/close the shared httpx.AsyncClient with an in-flight drain."""
    global _http_client, _shutting_down
    _shutting_down = False  # Reset for test suites that re-enter lifespan
    _http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=2.0),
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
        follow_redirects=False,
        http2=False,  # Lock to HTTP/1.1 so a transitive `h2` install can't silently flip protocol.
    )
    try:
        yield
    finally:
        _shutting_down = True
        # Drain in-flight upstream calls before closing the client. Bounded by
        # PROXY_REQUEST_TOTAL_TIMEOUT so shutdown cannot hang forever.
        try:
            await asyncio.wait_for(_inflight_zero_event.wait(), timeout=PROXY_REQUEST_TOTAL_TIMEOUT + 2.0)
        except asyncio.TimeoutError:
            log.warning("Lifespan drain timed out with %d in-flight requests", _inflight_counter)
        # Swap-then-close so new callers see `None` (raises cleanly) instead of
        # a closed client (raises cryptically).
        client = _http_client
        _http_client = None
        try:
            await client.aclose()
        except Exception:  # pragma: no cover - shutdown path
            pass


def _client() -> httpx.AsyncClient:
    if _shutting_down or _http_client is None:
        raise RuntimeError("httpx client not initialized (lifespan not started)")
    return _http_client


# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------

_Str = constr(strip_whitespace=True, min_length=1, max_length=128)


_FuelType = Literal["gasoline", "diesel", "hybrid", "electric", "lpg", "cng", "other"]


# Validator regex for DTC codes. Mirrors `_DTC_RE` defined later at route level —
# the Pydantic layer applies this to POST payloads (inspection) so null bytes,
# CRLF, and SQL-injection attempts are rejected BEFORE reaching the backend.
# Wave 6 fuzz audit found the POST path had no DTC pattern check — only the
# GET `/proxy/dtc/{code}` handler did.
_DTC_CODE_RE = re.compile(r"^[PBCU][0-9]{4}$")

# Control-character + NUL filter for string inputs. Pydantic's strip_whitespace
# only strips ASCII space/tab/newline at boundaries — embedded NUL/C0 control
# chars survive. Wave 6 fuzz flagged e.g. "Toyota\x00\r\n" bypassing validation.
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _strip_control_chars(v: str) -> str:
    """Raise ValueError if string contains control chars or NUL; used by model validators."""
    if _CONTROL_CHAR_RE.search(v):
        raise ValueError("string contains invalid control characters")
    return v


class CalculatorRequest(BaseModel):
    vehicle_make: _Str
    vehicle_model: _Str
    vehicle_year: int = Field(ge=1950, le=2030)
    mileage_km: int = Field(ge=0, le=2_000_000)
    condition: constr(strip_whitespace=True, min_length=1, max_length=32)
    repair_cost_huf: Optional[int] = Field(default=None, ge=0, le=99_999_999)
    fuel_type: Optional[_FuelType] = None

    model_config = {"extra": "forbid"}

    @field_validator("vehicle_make", "vehicle_model", "condition")
    @classmethod
    def _no_control_chars(cls, v: str) -> str:
        return _strip_control_chars(v)


class InspectionRequest(BaseModel):
    vehicle_make: _Str
    vehicle_model: _Str
    vehicle_year: int = Field(ge=1950, le=2030)
    dtc_codes: list[constr(strip_whitespace=True, min_length=1, max_length=16)] = Field(
        min_length=1, max_length=50
    )
    repair_cost_huf: Optional[int] = Field(default=None, ge=0, le=99_999_999)
    fuel_type: Optional[_FuelType] = None
    symptoms: Optional[List[constr(strip_whitespace=True, min_length=1, max_length=128)]] = Field(
        default=None, max_length=20
    )

    model_config = {"extra": "forbid"}

    @field_validator("vehicle_make", "vehicle_model")
    @classmethod
    def _no_control_chars(cls, v: str) -> str:
        return _strip_control_chars(v)

    @field_validator("dtc_codes")
    @classmethod
    def _validate_dtc_codes(cls, codes: List[str]) -> List[str]:
        """Wave 6 fuzz fix: enforce DTC format on POST payloads (not just GET).

        Previous: `constr(max_length=16)` accepted `P0001\x00ADMIN`, CR/LF, etc.
        Now: each code must match [PBCU][0-9]{4} after upper() — same contract
        as /proxy/dtc/{code}. Also dedupe preserving order (fuzz flagged that
        50 identical codes multiplied backend lookup load).
        """
        validated = []
        seen = set()
        for raw in codes:
            code = raw.strip().upper()
            if not _DTC_CODE_RE.match(code):
                raise ValueError(f"invalid DTC code format: {raw!r}")
            if code in seen:
                continue  # dedupe
            seen.add(code)
            validated.append(code)
        if not validated:
            raise ValueError("dtc_codes must contain at least one unique valid code")
        return validated

    @field_validator("symptoms")
    @classmethod
    def _symptoms_no_control(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return None
        return [_strip_control_chars(s) for s in v]


# Allow-list of query params per GET endpoint.
# Identifier routes (e.g. /api/v1/dtc/{code}) get an EMPTY allow-list so unknown
# query params get stripped before the cache key is computed — otherwise an
# attacker can vary `?x=1`, `?x=2`, ... to bypass the negative cache and force
# a backend round-trip per request.
_GET_PARAM_ALLOWLISTS: Dict[str, set[str]] = {
    "/api/v1/services/search": {"q", "category", "city", "region", "limit", "offset"},
    "/api/v1/dtc/search": {"q", "system", "limit", "offset", "lang"},
    "/api/v1/dtc/{code}": set(),  # path-param route, no query allowed
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
        if cl is None:
            # Wave 6 fuzz fix: reject body-carrying methods without Content-Length.
            # Without this, an attacker sends `Transfer-Encoding: chunked` with
            # no CL and the middleware's length guard is skipped — Starlette's
            # request.body() then buffers GBs of chunked data into RAM before
            # the post-read length check fires.
            if request.method in ("POST", "PUT", "PATCH"):
                return JSONResponse(
                    {"data": None, "error": {"code": "LENGTH_REQUIRED", "message": "Content-Length header is required"}, "meta": None},
                    status_code=411,
                )
            return await call_next(request)
        # Reject Transfer-Encoding explicitly — nginx de-chunks before forwarding
        # so any TE header reaching the app is a smuggling artifact.
        te = request.headers.get("transfer-encoding", "").lower()
        if te and te != "identity":
            return JSONResponse(
                {"data": None, "error": {"code": "BAD_HEADER", "message": "Transfer-Encoding not accepted"}, "meta": None},
                status_code=400,
            )
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
    comma-separated value. We only trust XFF when the peer is inside one of
    TRUSTED_PEER_NETWORKS (covers loopback in IPv4, IPv6, IPv4-mapped IPv6 form,
    and operator-configured container bridges). Otherwise we fall back to the
    socket peer.
    """
    peer = request.client.host if request.client else ""
    forwarded = request.headers.get("x-forwarded-for", "").strip()
    if forwarded and _is_trusted_peer(peer):
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        if parts:
            candidate = parts[-1]
            try:
                # Validate it's actually an IP — reject garbage like "attacker".
                ipaddress.ip_address(candidate)
                return candidate
            except ValueError:
                log.warning("Malformed XFF last-entry: %r", candidate)
    return peer or "unknown"


def _check_rate_limit(client_ip: str) -> tuple[bool, int, int]:
    """
    Returns (allowed, remaining, reset_epoch_seconds).

    Implementation: single OrderedDict keyed by (ip, minute_bucket). Keys are
    inserted in arrival order; FIFO eviction drops the oldest entry once the
    table grows past RATE_LIMIT_MAX_ENTRIES. See module-level comment for why
    FIFO beats LRU under attack.
    """
    now = time.time()
    current_minute = int(now // 60)
    key = (client_ip, current_minute)
    reset_epoch = (current_minute + 1) * 60

    count = _rate_limits.get(key, 0)
    if count >= RATE_LIMIT_PER_MINUTE:
        return False, 0, reset_epoch

    new_count = count + 1
    if key in _rate_limits:
        # Update count without changing insertion order (anchored to first hit).
        _rate_limits[key] = new_count
    else:
        _rate_limits[key] = new_count
        # FIFO eviction once we exceed the cap. popitem(last=False) drops the
        # OLDEST inserted key — never the most recently active legit user.
        while len(_rate_limits) > RATE_LIMIT_MAX_ENTRIES:
            _rate_limits.popitem(last=False)

    remaining = max(0, RATE_LIMIT_PER_MINUTE - new_count)
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


_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9\-]{1,64}$")


def _sanitize_request_id(raw: Optional[str]) -> str:
    """
    Accept the client's X-Request-ID only if it matches a strict alnum+dash
    grammar bounded at 64 chars. Anything else (control chars, newlines,
    quotes, length abuse) is replaced with a server-generated id.

    Why: the value is interpolated into log lines via %(request_id)s. A
    client-supplied "\\n2026-04-21 [CRITICAL] root: pwned" would inject a
    forged log entry (OWASP Logging Cheat Sheet, CWE-117). Strict allow-list
    is the only safe pattern here.
    """
    if raw and _REQUEST_ID_RE.fullmatch(raw):
        return raw
    return f"proxy-{uuid.uuid4().hex[:16]}"


def _request_id(request: Request) -> str:
    return _sanitize_request_id(request.headers.get("x-request-id"))


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

    # Wave 6 fix: bound lock acquisition so a slow CSRF refresh cannot
    # serialize every POST request. Without this, a backend /health/status
    # hang blocks all POSTs for up to 25s each → effective DoS via single
    # slow upstream dependency.
    try:
        await asyncio.wait_for(_csrf_lock.acquire(), timeout=PROXY_REQUEST_TOTAL_TIMEOUT)
    except asyncio.TimeoutError:
        log.warning("CSRF lock acquisition timed out", extra={"request_id": request_id})
        return None
    try:
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
            log.warning("CSRF fetch failed: %s", type(exc).__name__, extra={"request_id": request_id})
            return None

        token = resp.cookies.get("csrf_token")
        if not token:
            log.warning("CSRF cookie missing from backend health response", extra={"request_id": request_id})
            return None
        # Wave 6 race fix: single atomic swap (no torn read between token
        # set + expires_at set). expires_at MUST be the time after the await
        # completed, not before it.
        _csrf_cache["token"] = token
        _csrf_cache["expires_at"] = time.time() + CSRF_TTL_SECONDS
        return token
    finally:
        _csrf_lock.release()


def _invalidate_csrf() -> None:
    """Invalidate cached CSRF token. Safe under _csrf_lock only."""
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


async def _read_capped(resp: httpx.Response, request_id: str, backend_path: str) -> bytes:
    """
    Read the response body but never accumulate more than MAX_RESPONSE_BYTES.

    A truncated body will fail downstream JSON decoding, which we already
    handle by returning a sanitised 502 — i.e. the cap acts as a hard memory
    bound on a single upstream interaction. This protects the proxy from a
    misbehaving (or compromised) backend that streams an enormous body.

    Counter to "5MB might break large DTC list responses": 5MB serialised JSON
    is ~tens of thousands of records; the backend should never return that
    much from a single landing-page endpoint, and the limit is env-overridable
    (PROXY_MAX_RESPONSE_BYTES) for the rare exception.
    """
    body = b""
    truncated = False
    async for chunk in resp.aiter_bytes(chunk_size=8192):
        if len(body) + len(chunk) > MAX_RESPONSE_BYTES:
            # Take just enough to hit the cap, then mark truncated and stop.
            remaining = MAX_RESPONSE_BYTES - len(body)
            if remaining > 0:
                body += chunk[:remaining]
            truncated = True
            break
        body += chunk
    if truncated:
        log.warning(
            "Upstream response exceeded %d bytes on %s, truncating",
            MAX_RESPONSE_BYTES, backend_path,
            extra={"request_id": request_id},
        )
    return body


def _decode_json_bytes(body: bytes, content_type: str, request_id: str) -> Optional[Any]:
    """Defensive json decode for raw bytes (mirrors _decode_upstream_json)."""
    if not content_type.lower().startswith("application/json"):
        log.warning("Upstream non-JSON content-type: %s", content_type,
                    extra={"request_id": request_id})
        return None
    try:
        return json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        log.warning("Upstream JSON decode failed: %s", exc, extra={"request_id": request_id})
        return None


# CSRF rejection codes the BACKEND uses to signal "your token was bad".
# We MUST distinguish these from a generic 403 (auth/permissions failure):
# auto-refreshing on a permissions failure leaks an unrelated retry attempt
# and masks the real error from the client.
_CSRF_REJECT_CODES = frozenset({"CSRF_INVALID", "CSRF_EXPIRED", "CSRF_MISSING"})


def _is_csrf_rejection(body: Any) -> bool:
    """
    True iff the upstream JSON body looks like a CSRF-specific 403.
    Body shape we expect: {"data": null, "error": {"code": "CSRF_INVALID", ...}, ...}
    Any other 403 (perms, IP block, generic auth) returns False so we PROPAGATE
    rather than refresh-and-retry.
    """
    if not isinstance(body, dict):
        return False
    err = body.get("error")
    if not isinstance(err, dict):
        return False
    code = err.get("code")
    return isinstance(code, str) and code in _CSRF_REJECT_CODES


def _cache_response_headers(etag: str) -> Dict[str, str]:
    return {
        "Cache-Control": f"public, max-age={CACHE_TTL}",
        "ETag": f'"{etag}"',
    }


# ---------------------------------------------------------------------------
# Core proxy logic
# ---------------------------------------------------------------------------


async def _stream_request(method: str, url: str, **kwargs) -> Tuple[httpx.Response, bytes, str]:
    """
    Issue a streamed HTTP call and read at most MAX_RESPONSE_BYTES of body.

    Returns: (response, body_bytes, content_type). The Response is fully
    consumed by the time we return.
    """
    request_id = kwargs.pop("__request_id", "-")
    backend_path = kwargs.pop("__backend_path", url)
    async with _client().stream(method, url, **kwargs) as resp:
        try:
            body = await asyncio.wait_for(
                _read_capped(resp, request_id, backend_path),
                timeout=PROXY_REQUEST_TOTAL_TIMEOUT,
            )
        except asyncio.TimeoutError as exc:
            # Translate to httpx.ReadTimeout so existing httpx.TimeoutException
            # handlers in _proxy_get / _proxy_post catch it cleanly.
            raise httpx.ReadTimeout(
                f"total wall-time exceeded {PROXY_REQUEST_TOTAL_TIMEOUT}s for {backend_path}"
            ) from exc
        ct = resp.headers.get("content-type", "")
        return resp, body, ct


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

    async def _send(csrf_token: str) -> Tuple[httpx.Response, bytes, str]:
        return await _stream_request(
            "POST",
            f"{BACKEND_URL}{backend_path}",
            json=payload,
            headers={
                "Content-Type": "application/json",
                "X-CSRF-Token": csrf_token,
                "X-Request-ID": request_id,
            },
            cookies={"csrf_token": csrf_token},
            __request_id=request_id,
            __backend_path=backend_path,
        )

    try:
        csrf_token = await _get_csrf_token(request_id)
        if not csrf_token:
            return JSONResponse(
                _envelope(error={"code": "UPSTREAM_UNAVAILABLE", "message": "Could not obtain CSRF token"}),
                status_code=502,
            )
        resp, body_bytes, ct = await _send(csrf_token)

        # If we get 403, ONLY refresh-and-retry when the upstream explicitly
        # signals a CSRF-specific code. A generic 403 (perms, IP block) is
        # propagated as-is — refreshing then is wasted backend QPS and masks
        # the real reason the request was denied.
        if resp.status_code == 403:
            decoded_403 = _decode_json_bytes(body_bytes, ct, request_id)
            if _is_csrf_rejection(decoded_403):
                log.info("CSRF rejected by backend, refreshing token", extra={"request_id": request_id})
                _invalidate_csrf()
                csrf_token = await _get_csrf_token(request_id)
                if csrf_token:
                    resp, body_bytes, ct = await _send(csrf_token)
            else:
                log.info("Non-CSRF 403 on %s, propagating", backend_path,
                         extra={"request_id": request_id})
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
        body = _decode_json_bytes(body_bytes, ct, request_id)
        if body is None:
            # Non-JSON 4xx — don't leak raw HTML. Return sanitised error.
            return JSONResponse(
                _envelope(error={"code": "UPSTREAM_BAD_RESPONSE", "message": "Upstream returned non-JSON error"}),
                status_code=resp.status_code,
            )
        log.info("Upstream 4xx %s on %s", resp.status_code, backend_path,
                 extra={"request_id": request_id})
        return JSONResponse(body, status_code=resp.status_code)

    # 5xx: sanitised error. Log a slice for operators.
    if resp.status_code >= 500:
        # Decode body bytes safely; never leak raw upstream payload to client.
        try:
            preview = body_bytes[:500].decode("utf-8", errors="replace")
        except Exception:  # pragma: no cover - decode is total with errors=replace
            preview = "<undecodable>"
        log.error("Upstream 5xx %s on %s: %s", resp.status_code, backend_path, preview,
                  extra={"request_id": request_id})
        return JSONResponse(
            _envelope(error={"code": "UPSTREAM_ERROR", "message": "Upstream service error"}),
            status_code=502,
        )

    # 2xx happy path.
    data = _decode_json_bytes(body_bytes, ct, request_id)
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


async def _proxy_get(
    request: Request,
    backend_path: str,
    *,
    use_negative_cache: bool = False,
    param_allow_key: Optional[str] = None,
) -> Response:
    """
    Generic GET proxy.

    use_negative_cache: when True, upstream 404s are cached for
    NEGATIVE_CACHE_TTL seconds against (backend_path, params). This is for
    identifier-shaped routes (e.g. /api/v1/dtc/<code>) where an attacker can
    cheaply enumerate non-existent IDs and force a backend round-trip per
    request. Counter to "negative caching could mask backend recovery": TTL
    is 60s by default and the user is welcome to retry — they will see fresh
    state within the minute.
    """
    request_id = _request_id(request)
    client_ip = _get_client_ip(request)

    allowed, remaining, reset_epoch = _check_rate_limit(client_ip)
    if not allowed:
        return _rate_limited_response(reset_epoch)

    params, err = _sanitize_query_params(request, param_allow_key or backend_path)
    if err is not None:
        return err

    cache_key = _cache_key(backend_path, params)
    cached = _cache.get(cache_key)
    if cached is not None:
        etag = cache_key.split(":", 1)[1][:16]
        return JSONResponse(cached, headers={"X-Cache": "HIT", **_cache_response_headers(etag)})

    if use_negative_cache:
        neg = _negative_cache.get(cache_key)
        if neg is not None:
            return JSONResponse(
                neg,
                status_code=404,
                headers={"X-Cache": "HIT-NEG"},
            )

    try:
        resp, body_bytes, ct = await _stream_request(
            "GET",
            f"{BACKEND_URL}{backend_path}",
            params=params,
            headers={"X-Request-ID": request_id},
            __request_id=request_id,
            __backend_path=backend_path,
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
        body = _decode_json_bytes(body_bytes, ct, request_id)
        if body is None:
            return JSONResponse(
                _envelope(error={"code": "UPSTREAM_BAD_RESPONSE", "message": "Upstream returned non-JSON"}),
                status_code=resp.status_code,
            )
        # Negative-cache 404s only for routes that opted in.
        if use_negative_cache and resp.status_code == 404:
            _negative_cache[cache_key] = body
        return JSONResponse(body, status_code=resp.status_code)

    if resp.status_code >= 500:
        try:
            preview = body_bytes[:500].decode("utf-8", errors="replace")
        except Exception:  # pragma: no cover
            preview = "<undecodable>"
        log.error("Upstream 5xx %s on GET %s: %s", resp.status_code, backend_path, preview,
                  extra={"request_id": request_id})
        return JSONResponse(
            _envelope(error={"code": "UPSTREAM_ERROR", "message": "Upstream service error"}),
            status_code=502,
        )

    data = _decode_json_bytes(body_bytes, ct, request_id)
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
        # Wave 6 fuzz fix: a 6KB JSON depth-bomb (`{"a":` × 1000) raises
        # RecursionError, not JSONDecodeError — previous handler fell through
        # to Starlette's 500 + stack trace. Also reject NaN/Infinity via
        # parse_constant (Python's json.loads allows them by default; they
        # then produce invalid RFC-8259 on re-serialization and poison cache).
        body = (
            json.loads(
                raw.decode("utf-8"),
                parse_constant=lambda c: (_ for _ in ()).throw(ValueError(f"non-finite JSON literal: {c}")),
            )
            if raw
            else {}
        )
    except (json.JSONDecodeError, UnicodeDecodeError, RecursionError, ValueError):
        return None, JSONResponse(
            _envelope(error={"code": "INVALID_JSON", "message": "Invalid JSON body"}),
            status_code=400,
        )
    try:
        model = model_cls.model_validate(body)
    except ValidationError as exc:
        # Wave 6 OWASP/fuzz fix: strip `input`, `ctx`, `url` from Pydantic
        # error dicts. Those fields reflect raw attacker payload back to the
        # client — reflected content disclosure, latent XSS if any error UI
        # uses innerHTML.
        safe_details = [
            {"loc": e.get("loc", []), "msg": e.get("msg", ""), "code": e.get("type", "")}
            for e in exc.errors()
        ]
        return None, JSONResponse(
            _envelope(error={"code": "VALIDATION_ERROR", "message": "Invalid input", "details": safe_details}),
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


# Per SAE J2012, OBD-II DTC codes are [PBCU] + 4 decimal digits. The previous
# pattern allowed hex (A-F) which diverged from JS validation, the database
# schema, and the build script — codes accepted at the proxy were rejected
# everywhere else. Aligned to digits-only to match shared/js/tool-common.js,
# scripts/build-dtc-database.py, and tests/unit/workshop-finder.test.js.
_DTC_RE = re.compile(r"^[PBCU][0-9]{4}$")


async def dtc_detail(request: Request) -> Response:
    raw_code = request.path_params.get("code", "")
    code = raw_code.strip().upper()
    if not _DTC_RE.match(code):
        return JSONResponse(
            _envelope(error={"code": "INVALID_DTC", "message": "Invalid DTC code format"}),
            status_code=400,
        )
    # use_negative_cache=True: an attacker enumerating P0001..PFFFF would
    # otherwise force one backend round-trip per code. 60s TTL caches the 404
    # so a brute-force scan hits the proxy memory, not the database.
    return await _proxy_get(
        request,
        f"/api/v1/dtc/{code}",
        use_negative_cache=True,
        param_allow_key="/api/v1/dtc/{code}",
    )


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
