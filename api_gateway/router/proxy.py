# routers/proxy.py
import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response
from config import SERVICE_MAP, PROXY_TIMEOUT

router = APIRouter()

# Headers that must not be forwarded — they're connection-specific
# and would confuse the backend or break HTTP semantics
HOP_BY_HOP_HEADERS = {
    "connection", "transfer-encoding", "te",
    "trailer", "upgrade", "keep-alive",
    "proxy-authenticate", "proxy-authorization"
}

def resolve_service(path: str) -> tuple[str, str]:
    """
    Match incoming path to a backend service.
    Returns (backend_base_url, stripped_path).

    /services/users/123  →  ("http://localhost:8001", "/users/123")

    Tries longest prefix first to avoid ambiguous matches.
    e.g. /users/orders should match /users not /orders
    """
    # Strip the /services gateway prefix
    if path.startswith("/services"):
        path = path[len("/services"):]

    # Match longest prefix first
    for prefix in sorted(SERVICE_MAP.keys(), key=len, reverse=True):
        if path.startswith(prefix):
            backend_url = SERVICE_MAP[prefix]
            return backend_url, path

    raise HTTPException(
        status_code=404,
        detail=f"No backend service found for path: {path}"
    )

def clean_headers(headers: dict) -> dict:
    """Remove hop-by-hop headers before forwarding."""
    return {
        k: v for k, v in headers.items()
        if k.lower() not in HOP_BY_HOP_HEADERS
    }

@router.api_route(
    "/services/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"]
)
async def proxy(request: Request, path: str):
    """
    Catch-all proxy route.
    Forwards any method to the appropriate backend service.
    """
    backend_url, service_path = resolve_service(request.url.path)

    # Preserve query string — e.g. /users?page=2&limit=10
    query_string = request.url.query
    target_url   = f"{backend_url}{service_path}"
    if query_string:
        target_url += f"?{query_string}"

    # Forward cleaned headers + inject tracing headers
    headers = clean_headers(dict(request.headers))
    headers["x-forwarded-for"] = request.client.host
    headers["x-request-id"]    = str(request.state.user.id)  # user id as trace

    # Read body (empty for GET, present for POST/PUT)
    body = await request.body()

    try:
        async with httpx.AsyncClient(timeout=PROXY_TIMEOUT) as client:
            backend_response = await client.request(
                method  = request.method,
                url     = target_url,
                headers = headers,
                content = body,
            )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail=f"Backend service timed out after {PROXY_TIMEOUT}s."
        )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Backend service is unreachable."
        )

    # Pass backend response straight through — status, body, headers
    return Response(
        content    = backend_response.content,
        status_code= backend_response.status_code,
        headers    = dict(backend_response.headers),
        media_type = backend_response.headers.get("content-type")
    )