"""FastAPI application entry point: lifespan, CORS, logging, and router registration."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from hand2notes.storage.database import init_db

from .middleware import RequestLoggingMiddleware, configure_logging, register_exception_handlers

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    await init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="hand2notes API",
        version="0.1.0",
        description="Local pipeline backend converting handwritten notes to an Obsidian vault.",
        lifespan=lifespan,
    )

    # Local-only desktop app: the Electron renderer may present any localhost/file origin.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)
    register_exception_handlers(app)

    @app.get("/health")
    @app.get(f"{API_PREFIX}/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    _register_routers(app)
    return app


def _register_routers(app: FastAPI) -> None:
    """Mount feature routers as they are implemented (sessions/pipeline/config in Phase 3+)."""
    # from .routers import sessions, pipeline, config
    # app.include_router(sessions.router, prefix=API_PREFIX)
    # app.include_router(pipeline.router, prefix=API_PREFIX)
    # app.include_router(config.router, prefix=API_PREFIX)
    return None


app = create_app()
