"""Structured logging middleware and global error handlers.

Every request and every pipeline failure produces a structured log line and a
RFC 7807 problem+json error envelope, per constitution Principle II (Observable Pipeline).
"""

import json
import logging
import sys
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("hand2notes")

_PROBLEM_CONTENT_TYPE = "application/problem+json"


def configure_logging(level: int = logging.INFO) -> None:
    """Emit single-line JSON logs to stdout."""
    if logger.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if isinstance(record.args, dict):
            payload.update(record.args)
        for key in ("request_id", "method", "path", "status", "duration_ms", "stage"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, default=str)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log method, path, status, and duration for every request."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        response.headers["X-Request-ID"] = request_id
        return response


def _problem_body(
    status: int,
    type_: str,
    title: str,
    detail: str,
    request: Request,
    **extra,
) -> dict:
    """Build an RFC 7807 problem+json body."""
    body = {
        "type": f"urn:hand2notes:error:{type_}",
        "title": title,
        "status": status,
        "detail": detail,
        "instance": str(request.url),
        "request_id": getattr(request.state, "request_id", None),
    }
    body.update(extra)
    return body


# Keep legacy helper for backward compatibility with existing callers
def _error_body(status: int, code: str, message: str, request: Request) -> dict:
    return _problem_body(status, code, code.replace("_", " ").title(), message, request)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach handlers that return RFC 7807 problem+json error envelopes."""

    @app.exception_handler(StarletteHTTPException)
    async def _http_exc(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_problem_body(
                exc.status_code,
                "http_error",
                f"HTTP {exc.status_code}",
                str(exc.detail),
                request,
            ),
            media_type=_PROBLEM_CONTENT_TYPE,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_exc(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_problem_body(
                422,
                "validation_error",
                "Request Validation Failed",
                "One or more request fields failed validation.",
                request,
                errors=exc.errors(),
            ),
            media_type=_PROBLEM_CONTENT_TYPE,
        )

    @app.exception_handler(Exception)
    async def _unhandled_exc(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error", extra={"path": request.url.path})
        return JSONResponse(
            status_code=500,
            content=_problem_body(
                500,
                "internal_error",
                "Internal Server Error",
                "An unexpected error occurred. Check server logs for details.",
                request,
            ),
            media_type=_PROBLEM_CONTENT_TYPE,
        )

    # Pipeline-specific error type
    from hand2notes.pipeline.orchestrator import PipelineError

    @app.exception_handler(PipelineError)
    async def _pipeline_exc(request: Request, exc: PipelineError) -> JSONResponse:
        logger.error("pipeline_error", extra={"path": request.url.path, "detail": str(exc)})
        return JSONResponse(
            status_code=500,
            content=_problem_body(
                500,
                "pipeline_error",
                "Pipeline Stage Failure",
                str(exc),
                request,
            ),
            media_type=_PROBLEM_CONTENT_TYPE,
        )
