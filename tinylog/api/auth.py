"""API Key authentication middleware."""

from __future__ import annotations

import hmac

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response


# Paths that skip auth
_PUBLIC_PATHS = {"/api/health", "/api/config"}


class AdminKeyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, admin_key: str):
        super().__init__(app)
        self.admin_key = admin_key

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip auth if no key configured
        if not self.admin_key:
            return await call_next(request)

        # Skip for non-API routes and public paths
        path = request.url.path
        if not path.startswith("/api/") or path in _PUBLIC_PATHS:
            return await call_next(request)

        # Check key
        provided = request.headers.get("X-Admin-Key", "")
        if not hmac.compare_digest(provided, self.admin_key):
            return JSONResponse(status_code=401, content={"detail": "Invalid or missing admin key"})

        return await call_next(request)
