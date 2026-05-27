from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


_PHI_ROUTE_PREFIXES = ("/api/v1/patients", "/api/v1/admin")
_SKIP_AUDIT_PATHS = ("/health", "/metrics", "/api/v1/auth/refresh")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "frame-ancestors 'none';"
        )
        return response


class AuditMiddleware(BaseHTTPMiddleware):
    """Log every request that touches a PHI route.

    Fires after the response so the HTTP status is known.
    Does NOT log request bodies (which may contain PHI).
    Uses the route path template (e.g. /patients/{patient_id}), not the
    resolved URL, so no identifiers appear in the structured log line.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        path = request.url.path
        if any(path.startswith(p) for p in _SKIP_AUDIT_PATHS):
            return response

        is_phi_route = any(path.startswith(p) for p in _PHI_ROUTE_PREFIXES)
        if not is_phi_route:
            return response

        # Structured log line — no PHI, no query params, no body
        import logging
        logger = logging.getLogger("doulashield.audit")
        logger.info(
            "phi_access method=%s path=%s status=%d ip=%s",
            request.method,
            path,
            response.status_code,
            request.client.host if request.client else "unknown",
        )
        return response
