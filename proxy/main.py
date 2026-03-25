import os
import json
import time
import hashlib
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.middleware.cors import CORSMiddleware
import httpx

BACKEND_URL = os.getenv("BACKEND_URL", "https://autocognitix-production.up.railway.app")
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour
RATE_LIMIT_PER_MINUTE = int(os.getenv("PROXY_RATE_LIMIT", "30"))

# Simple in-memory cache
_cache = {}
_rate_limits = {}

def _cache_key(path, body):
    """Generate cache key from request path + body hash"""
    body_hash = hashlib.md5(json.dumps(body, sort_keys=True).encode()).hexdigest()
    return f"{path}:{body_hash}"

def _check_rate_limit(client_ip):
    """Simple per-IP rate limiting"""
    now = time.time()
    minute_key = f"{client_ip}:{int(now/60)}"
    count = _rate_limits.get(minute_key, 0)
    if count >= RATE_LIMIT_PER_MINUTE:
        return False
    _rate_limits[minute_key] = count + 1
    # Cleanup old entries
    for k in list(_rate_limits.keys()):
        if int(k.split(":")[-1]) < int(now/60) - 1:
            del _rate_limits[k]
    return True

async def _get_csrf_token(client):
    """Get CSRF token from backend by making a GET request"""
    resp = await client.get(f"{BACKEND_URL}/api/v1/health/status")
    csrf_cookie = resp.cookies.get("csrf_token")
    return csrf_cookie

async def _proxy_post(request, backend_path):
    """Proxy a POST request to the backend with CSRF handling"""
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)

    try:
        body = await request.json()
    except:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    # Check cache
    cache_key = _cache_key(backend_path, body)
    cached = _cache.get(cache_key)
    if cached and time.time() - cached["ts"] < CACHE_TTL:
        return JSONResponse(cached["data"], headers={"X-Cache": "HIT"})

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Get CSRF token
        csrf_token = await _get_csrf_token(client)
        if not csrf_token:
            return JSONResponse({"error": "Failed to obtain CSRF token"}, status_code=502)

        # Step 2: POST with CSRF
        headers = {
            "Content-Type": "application/json",
            "X-CSRF-Token": csrf_token,
            "X-Request-ID": f"proxy-{int(time.time()*1000)}",
        }
        cookies = {"csrf_token": csrf_token}

        resp = await client.post(
            f"{BACKEND_URL}{backend_path}",
            json=body,
            headers=headers,
            cookies=cookies,
        )

        if resp.status_code >= 400:
            return JSONResponse(
                {"error": f"Backend returned {resp.status_code}", "detail": resp.text},
                status_code=resp.status_code
            )

        data = resp.json()

        # Cache successful response
        _cache[cache_key] = {"data": data, "ts": time.time()}

        # Cleanup old cache entries
        now = time.time()
        for k in list(_cache.keys()):
            if now - _cache[k]["ts"] > CACHE_TTL * 2:
                del _cache[k]

        return JSONResponse(data, headers={"X-Cache": "MISS"})

async def _proxy_get(request, backend_path):
    """Proxy a GET request (no CSRF needed)"""
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)

    params = dict(request.query_params)
    cache_key = _cache_key(backend_path, params)
    cached = _cache.get(cache_key)
    if cached and time.time() - cached["ts"] < CACHE_TTL:
        return JSONResponse(cached["data"], headers={"X-Cache": "HIT"})

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{BACKEND_URL}{backend_path}", params=params)
        if resp.status_code >= 400:
            return JSONResponse(
                {"error": f"Backend returned {resp.status_code}"},
                status_code=resp.status_code
            )
        data = resp.json()
        _cache[cache_key] = {"data": data, "ts": time.time()}
        return JSONResponse(data, headers={"X-Cache": "MISS"})

# Route handlers
async def calculator_evaluate(request):
    return await _proxy_post(request, "/api/v1/calculator/evaluate")

async def inspection_evaluate(request):
    return await _proxy_post(request, "/api/v1/inspection/evaluate")

async def services_search(request):
    return await _proxy_get(request, "/api/v1/services/search")

async def dtc_search(request):
    return await _proxy_get(request, "/api/v1/dtc/search")

async def dtc_detail(request):
    code = request.path_params["code"]
    return await _proxy_get(request, f"/api/v1/dtc/{code}")

async def health(request):
    return JSONResponse({"status": "ok", "service": "landing-proxy"})

routes = [
    Route("/proxy/health", health),
    Route("/proxy/calculator/evaluate", calculator_evaluate, methods=["POST"]),
    Route("/proxy/inspection/evaluate", inspection_evaluate, methods=["POST"]),
    Route("/proxy/services/search", services_search),
    Route("/proxy/dtc/search", dtc_search),
    Route("/proxy/dtc/{code}", dtc_detail),
]

app = Starlette(routes=routes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)
