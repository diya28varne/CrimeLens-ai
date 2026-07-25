"""Global exception handlers mapping domain errors to API error envelope."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from crimelens_domain.shared.errors import AppError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=exc.http_status,
            content={
                "error": {
                    "code": exc.details.get("code", exc.code)
                    if isinstance(exc.details, dict)
                    else exc.code,
                    "message": exc.message,
                    "details": {k: v for k, v in exc.details.items() if k != "code"},
                    "request_id": request_id,
                }
            },
        )
