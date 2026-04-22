"""
Proxy service tests — landing-proxy (Starlette + httpx).

Scope
-----
The proxy sits between the static landing pages and the AutoCognitix backend.
It adds:
  1) Per-IP rate limiting (30 req/min by default)
  2) Input validation for calculator & inspection POST bodies
  3) DTC code regex filtering
  4) CSRF-token forwarding to the backend
  5) A tiny in-memory cache for GET + POST responses
  6) Response sanitization (we must NEVER echo backend stack traces to clients)

These tests exercise ONLY the proxy. All outbound httpx traffic is mocked via
respx so tests are hermetic and deterministic.

The critical one — `test_rate_limit_uses_last_xff_not_first` — is a regression
guard. An attacker controls the FIRST XFF entry (it's just a request header),
but cannot control the LAST entry because the trusted reverse proxy appends it.
Reading the FIRST entry means an attacker can rotate IPs and defeat rate limiting.
"""

from __future__ import annotations

import json
import time
from typing import Any

import httpx
import pytest
import respx


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #


def _valid_calculator_body() -> dict[str, Any]:
    return {
        "vehicle_make": "Toyota",
        "vehicle_model": "Corolla",
        "vehicle_year": 2018,
        "mileage_km": 120000,
        "condition": "good",
    }


def _valid_inspection_body() -> dict[str, Any]:
    return {
        "vehicle_make": "Toyota",
        "vehicle_model": "Corolla",
        "vehicle_year": 2018,
        "dtc_codes": ["P0420"],
    }


def _stub_csrf(respx_mock: respx.MockRouter, backend_url: str) -> None:
    """Make the CSRF GET endpoint return a Set-Cookie with csrf_token."""
    respx_mock.get(f"{backend_url}/api/v1/health/status").mock(
        return_value=httpx.Response(
            200,
            json={"status": "ok"},
            headers={"set-cookie": "csrf_token=test-csrf-abc; Path=/"},
        )
    )


# --------------------------------------------------------------------------- #
# TEST 1 — Rate limit: 429 after 30 requests/minute                           #
# --------------------------------------------------------------------------- #


def test_rate_limit_429_after_30_requests_in_minute(client, proxy_module):
    """
    After RATE_LIMIT_PER_MINUTE (30) requests from the same IP within one
    minute, the 31st request MUST return 429.

    We hit a cheap route (/proxy/health) so we don't depend on respx stubs here.
    Wait — /proxy/health does not call _check_rate_limit. Use a GET route that
    does: /proxy/services/search. Stub the backend to return 200 quickly.
    """
    limit = proxy_module.RATE_LIMIT_PER_MINUTE
    assert limit == 30, "Test fixture assumes default 30 req/min"

    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{proxy_module.BACKEND_URL}/api/v1/services/search").mock(
            return_value=httpx.Response(200, json={"results": []})
        )

        ip = "203.0.113.5"  # TEST-NET-3, will never collide with real traffic
        # First 30 requests: all must be < 400 (not rate-limited).
        for i in range(limit):
            r = client.get(
                "/proxy/services/search",
                headers={"x-forwarded-for": ip},
            )
            assert r.status_code < 400, f"request {i + 1} unexpectedly failed: {r.status_code}"

        # 31st request: MUST be 429.
        r = client.get(
            "/proxy/services/search",
            headers={"x-forwarded-for": ip},
        )
        assert r.status_code == 429
        # Production uses the canonical `{data, error, meta}` envelope.
        body = r.json()
        assert body["data"] is None
        assert body["error"]["code"] == "RATE_LIMITED"
        assert body["error"]["message"] == "Rate limit exceeded"


# --------------------------------------------------------------------------- #
# TEST 2 — CRITICAL: rate limit must key off the LAST XFF entry, not FIRST    #
# --------------------------------------------------------------------------- #


def test_rate_limit_uses_last_xff_not_first(client, proxy_module):
    """
    SECURITY REGRESSION GUARD.

    Threat model: XFF = "attacker-controlled, attacker-controlled, ..., trusted-proxy-IP".
    The client writes any XFF it wants. The trusted reverse proxy APPENDS its
    view of the real client IP as the LAST entry. Therefore:

        - first XFF entry  = ATTACKER-CONTROLLED    (spoofable, must NOT be used as rate-limit key)
        - last XFF entry   = TRUSTED                (set by the reverse proxy, is the real client IP)

    Current `_get_client_ip()` reads `split(",")[0]` which is the FIRST entry —
    this is a bug. An attacker can rotate the first entry on every request and
    bypass rate limiting entirely. Security-sentinel's fix switches this to
    read `split(",")[-1].strip()`.

    This test FAILS against the buggy code and PASSES against the fixed code.
    That is by design — it's how we know the fix stuck and doesn't regress.

    The test works as follows:
      - Send 30 requests where FIRST XFF rotates (fake-client-001, -002, ...)
        but LAST XFF is always 198.51.100.42 (the real attacker's IP through
        the reverse proxy).
      - If the proxy keys rate-limit by FIRST XFF: all 30 are "different IPs"
        -> none get blocked -> the 31st also goes through -> TEST FAILS.
      - If the proxy keys rate-limit by LAST XFF: all 30 share one counter
        -> the 31st hits 429 -> TEST PASSES.
    """
    limit = proxy_module.RATE_LIMIT_PER_MINUTE

    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{proxy_module.BACKEND_URL}/api/v1/services/search").mock(
            return_value=httpx.Response(200, json={"results": []})
        )

        real_ip = "198.51.100.42"  # TEST-NET-2

        for i in range(limit):
            rotating_fake = f"192.0.2.{(i % 250) + 1}"  # TEST-NET-1
            xff = f"{rotating_fake}, 10.0.0.1, {real_ip}"
            r = client.get(
                "/proxy/services/search",
                headers={"x-forwarded-for": xff},
            )
            assert r.status_code < 400, (
                f"request {i + 1} with XFF '{xff}' got {r.status_code} unexpectedly"
            )

        # 31st request with a DIFFERENT rotating first-XFF but the SAME last-XFF.
        # If rate limiting uses the last entry (correct), this must be 429.
        xff = f"192.0.2.251, 10.0.0.1, {real_ip}"
        r = client.get(
            "/proxy/services/search",
            headers={"x-forwarded-for": xff},
        )
        assert r.status_code == 429, (
            "SECURITY REGRESSION: rate limiter is keying off the FIRST XFF entry "
            "(attacker-controlled) instead of the LAST entry (trusted-proxy-set). "
            "An attacker can rotate the first XFF and bypass rate limiting. "
            "Fix `_get_client_ip()` to use split(',')[-1].strip()."
        )


# --------------------------------------------------------------------------- #
# TEST 3 — Invalid JSON body returns 400                                      #
# --------------------------------------------------------------------------- #


def test_invalid_json_body_returns_400(client):
    r = client.post(
        "/proxy/calculator/evaluate",
        content=b"this is { not json",
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 400
    # Envelope: {data, error: {code, message}, meta}. See rules/api.md.
    body = r.json()
    assert body["data"] is None
    assert body["error"]["code"] == "INVALID_JSON"
    assert body["error"]["message"] == "Invalid JSON body"
    assert body["meta"] is None


# --------------------------------------------------------------------------- #
# TEST 4 — Missing required field returns 422 with field names                #
# --------------------------------------------------------------------------- #
# Note: 422 (Unprocessable Entity) — not 400 — is the correct status for a
# syntactically-valid body that fails semantic validation (RFC 4918 §11.2,
# FastAPI/Pydantic convention). 400 is reserved for malformed syntax (see
# test_invalid_json_body_returns_400). Production wraps Pydantic's
# ValidationError in the canonical envelope with `details` = exc.errors().


def _field_names_from_errors(details: list[dict]) -> set[str]:
    """Extract the top-level field name from each Pydantic error entry."""
    names: set[str] = set()
    for d in details or []:
        loc = d.get("loc") or []
        if loc:
            names.add(str(loc[0]))
    return names


def test_missing_required_field_returns_422(client):
    body = _valid_calculator_body()
    body.pop("condition")  # missing required field
    body.pop("mileage_km")

    r = client.post("/proxy/calculator/evaluate", json=body)
    assert r.status_code == 422
    payload = r.json()
    assert payload["data"] is None
    err = payload["error"]
    assert err["code"] == "VALIDATION_ERROR"
    # Must name BOTH missing fields in the structured `details` list.
    missing = _field_names_from_errors(err.get("details", []))
    assert "condition" in missing, f"expected 'condition' in {missing}"
    assert "mileage_km" in missing, f"expected 'mileage_km' in {missing}"
    # And must NOT leak internals — stringify the WHOLE response to be safe.
    dump = str(payload).lower()
    assert "traceback" not in dump
    assert "/proxy/" not in dump  # no file-path leak
    # The top-level message stays short and human-readable.
    assert isinstance(err["message"], str) and len(err["message"]) < 200


def test_missing_required_field_returns_422_inspection(client):
    body = _valid_inspection_body()
    body.pop("dtc_codes")
    r = client.post("/proxy/inspection/evaluate", json=body)
    assert r.status_code == 422
    payload = r.json()
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    missing = _field_names_from_errors(payload["error"].get("details", []))
    assert "dtc_codes" in missing, f"expected 'dtc_codes' in {missing}"


# --------------------------------------------------------------------------- #
# TEST 5 — DTC regex rejects lowercase, short codes, and injection attempts    #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "code",
    [
        # NOTE: 'p0420' was deliberately removed. The handler uppercases the
        # path param before the regex check, so lowercase P-codes ARE valid.
        # (The test file's own comment acknowledged this irony.) It is
        # exercised positively in `test_dtc_regex_accepts_valid_codes` below.
        "P042",        # too short
        "P04200",      # too long
        "Z0420",       # bad prefix (not P/B/C/U)
        "P042G",       # non-digit final char (per SAE J2012)
        "PABCD",       # hex letters not allowed (Wave 5: aligned with JS/DB schema)
        "P0420;DROP",  # SQL-injection attempt
        "P 0420",      # embedded space
        "P0420/../../etc/passwd",  # path traversal (becomes a 404 route miss)
        "<script>",    # XSS payload
        "",            # empty path segment -> 404 route miss
    ],
)
def test_dtc_regex_rejects_malformed_and_injection_codes(client, code):
    r = client.get(f"/proxy/dtc/{code}")
    # Path segments with "/" produce 404 routing mismatch, which is ALSO a reject.
    assert r.status_code in (400, 404), (
        f"DTC code {code!r} should be rejected (400) or routed away (404), "
        f"got {r.status_code}"
    )
    if r.status_code == 400:
        err = r.json()["error"]
        # Envelope: error is a dict, not a bare string.
        assert err["code"] == "INVALID_DTC"
        assert "Invalid DTC" in err["message"]


@pytest.mark.parametrize("code", ["P0420", "p0420", "B0001", "U1234", "C9999"])
def test_dtc_regex_accepts_valid_codes(client, code, proxy_module):
    """Complement to the reject test — make sure we aren't over-rejecting.

    Per SAE J2012 + Wave 5 cross-stack alignment: codes are [PBCU] + 4 decimal
    digits. Hex letters (A-F) used to be accepted at the proxy/nginx layer but
    rejected by the JS validator and DB lookup — codes were undisplayable
    despite passing the proxy. Fixed in Wave 5.
    """
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{proxy_module.BACKEND_URL}/api/v1/dtc/{code.upper()}").mock(
            return_value=httpx.Response(200, json={"code": code.upper()})
        )
        r = client.get(f"/proxy/dtc/{code}")
        assert r.status_code == 200, (
            f"valid DTC code {code!r} was unexpectedly rejected"
        )


# --------------------------------------------------------------------------- #
# TEST 6 — Backend 5xx does not leak stack trace                              #
# --------------------------------------------------------------------------- #


def test_backend_5xx_does_not_leak_stack_trace(client, proxy_module):
    """
    When the upstream backend returns a 500 with a Python traceback in the body,
    the proxy MUST return sanitized JSON. No 'Traceback', no '.py', no sql,
    no file paths. Production maps upstream 5xx -> 502 (bad gateway) — the
    client is NOT told the specifics of the upstream failure.
    """
    leaky_body = (
        'Traceback (most recent call last):\n'
        '  File "/app/backend/main.py", line 42, in handler\n'
        '    raise ValueError("db password: supersecret123")\n'
        'ValueError: db password: supersecret123'
    )

    with respx.mock(assert_all_called=False) as mock:
        _stub_csrf(mock, proxy_module.BACKEND_URL)
        mock.post(
            f"{proxy_module.BACKEND_URL}/api/v1/calculator/evaluate"
        ).mock(
            return_value=httpx.Response(
                500,
                text=leaky_body,
                headers={"content-type": "text/plain"},
            )
        )

        r = client.post("/proxy/calculator/evaluate", json=_valid_calculator_body())

    # Upstream 5xx -> proxy returns 502 with a sanitised envelope.
    assert r.status_code == 502
    # Response body must be JSON, not text/plain passthrough.
    assert r.headers.get("content-type", "").startswith("application/json")
    body_text = r.text
    body = r.json()
    # No traceback-like tokens anywhere in the response body.
    for forbidden in ("Traceback", 'File "', ".py\", line", "supersecret", "password"):
        assert forbidden not in body_text, (
            f"Response leaked sensitive token {forbidden!r}:\n{body_text}"
        )
    # Envelope shape: {data, error: {code, message}, meta}. `error` must be
    # a short, opaque dict — no upstream payload pass-through.
    assert body["data"] is None
    err = body["error"]
    assert isinstance(err, dict)
    assert err["code"] == "UPSTREAM_ERROR"
    assert isinstance(err["message"], str) and "service" in err["message"].lower()
    # No raw "traceback" key leaked at any level.
    assert "traceback" not in body_text.lower()


# --------------------------------------------------------------------------- #
# TEST 7 — Cache hit/miss header behaviour                                    #
# --------------------------------------------------------------------------- #


def test_cache_hit_miss_header_behavior(client, proxy_module):
    """
    First GET for a (path, query) tuple -> X-Cache: MISS.
    Second GET for the SAME (path, query) -> X-Cache: HIT (served from in-memory
    cache; backend is NOT called again).
    """
    backend_route = f"{proxy_module.BACKEND_URL}/api/v1/services/search"

    with respx.mock(assert_all_called=False) as mock:
        route = mock.get(backend_route).mock(
            return_value=httpx.Response(200, json={"results": [1, 2, 3]})
        )

        r1 = client.get("/proxy/services/search?q=pest", headers={"x-forwarded-for": "1.1.1.1"})
        assert r1.status_code == 200
        assert r1.headers["X-Cache"] == "MISS"

        r2 = client.get("/proxy/services/search?q=pest", headers={"x-forwarded-for": "1.1.1.1"})
        assert r2.status_code == 200
        assert r2.headers["X-Cache"] == "HIT"
        # Crucially: backend was only called ONCE even though we made two proxy calls.
        assert route.call_count == 1

        # Different query -> MISS again (keyed off params).
        r3 = client.get("/proxy/services/search?q=budapest", headers={"x-forwarded-for": "1.1.1.1"})
        assert r3.status_code == 200
        assert r3.headers["X-Cache"] == "MISS"
        assert route.call_count == 2


# --------------------------------------------------------------------------- #
# TEST 8 — CORS preflight rejects unauthorized origin                         #
# --------------------------------------------------------------------------- #


def test_cors_preflight_rejects_unauthorized_origin(client):
    """
    CORSMiddleware must not echo Access-Control-Allow-Origin for unlisted origins.
    Starlette's implementation returns 400 for disallowed preflights.
    """
    r = client.options(
        "/proxy/calculator/evaluate",
        headers={
            "origin": "https://evil.example.com",
            "access-control-request-method": "POST",
            "access-control-request-headers": "content-type",
        },
    )
    # Either an explicit reject (400) or no ACAO echo — both are acceptable per spec.
    assert "access-control-allow-origin" not in {
        k.lower() for k in r.headers.keys()
    } or r.headers.get("access-control-allow-origin") != "https://evil.example.com"


def test_cors_preflight_accepts_allowlisted_origin(client):
    r = client.options(
        "/proxy/calculator/evaluate",
        headers={
            "origin": "https://autocognitix.hu",
            "access-control-request-method": "POST",
            "access-control-request-headers": "content-type",
        },
    )
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "https://autocognitix.hu"


# --------------------------------------------------------------------------- #
# TEST 9 — Body over 64 KB rejected (middleware)                              #
# --------------------------------------------------------------------------- #


def test_body_over_64kb_rejected(client):
    """
    DoS guard: oversized JSON bodies must be rejected before we even attempt
    to parse them. The proxy has BodySizeLimitMiddleware + an in-handler
    `len(raw) > MAX_BODY_BYTES` guard.

    Historical bug in this test: the payload used
      `{"vehicle_make": oversized, **_valid_calculator_body()}`
    which places _valid_calculator_body()'s `vehicle_make="Toyota"` AFTER the
    oversized value, silently overwriting it and producing a ~119-byte body.
    Fixed by building a raw oversized payload that doesn't rely on key order.
    """
    # Build a body whose serialised size is definitively > 64 KB without
    # depending on dict-merge order. We use a dedicated `_pad` key; the
    # handler will reject on size BEFORE schema validation runs, so the
    # presence of an unknown key is harmless.
    padding = "x" * (70 * 1024)
    payload = json.dumps({"_pad": padding}).encode()
    assert len(payload) > 64 * 1024, f"payload only {len(payload)} bytes — test setup bug"

    r = client.post(
        "/proxy/calculator/evaluate",
        content=payload,
        headers={"content-type": "application/json"},
    )
    # 413 Payload Too Large is the RFC-correct response.
    # 400 is acceptable if a middleware wraps it as a validation error.
    assert r.status_code in (400, 413), (
        f"Oversized body should be rejected (400/413), got {r.status_code}."
    )
    # When 413, the envelope must still be well-formed.
    if r.status_code == 413:
        body = r.json()
        assert body["error"]["code"] == "PAYLOAD_TOO_LARGE"


# --------------------------------------------------------------------------- #
# TEST 10 — CSRF token is fetched and forwarded                               #
# --------------------------------------------------------------------------- #


def test_csrf_token_fetched_and_forwarded(client, proxy_module):
    """
    For every POST the proxy must:
      1) GET /api/v1/health/status to receive a csrf_token cookie
      2) POST the user's body to the backend with:
         - header X-CSRF-Token: <token>
         - cookie csrf_token=<token>

    If either is missing, the backend will reject the request. This test is
    the only thing that catches a silent CSRF regression in the proxy.
    """
    captured: dict[str, Any] = {}

    def capture_and_echo(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["x_csrf"] = request.headers.get("x-csrf-token")
        captured["cookie"] = request.headers.get("cookie")
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(200, json={"ok": True})

    with respx.mock(assert_all_called=False) as mock:
        _stub_csrf(mock, proxy_module.BACKEND_URL)
        mock.post(
            f"{proxy_module.BACKEND_URL}/api/v1/calculator/evaluate"
        ).mock(side_effect=capture_and_echo)

        r = client.post("/proxy/calculator/evaluate", json=_valid_calculator_body())

    assert r.status_code == 200
    assert captured["x_csrf"] == "test-csrf-abc"
    assert "csrf_token=test-csrf-abc" in (captured["cookie"] or "")
    assert captured["body"]["vehicle_make"] == "Toyota"


def test_csrf_fetch_failure_returns_502(client, proxy_module):
    """If the backend doesn't give us a csrf cookie, we must NOT proceed."""
    with respx.mock(assert_all_called=False) as mock:
        # No Set-Cookie in the CSRF response -> token is None.
        mock.get(f"{proxy_module.BACKEND_URL}/api/v1/health/status").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )
        r = client.post("/proxy/calculator/evaluate", json=_valid_calculator_body())
    assert r.status_code == 502
    err = r.json()["error"]
    assert err["code"] == "UPSTREAM_UNAVAILABLE"
    assert "CSRF" in err["message"]
