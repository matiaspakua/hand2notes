"""FastAPI application entry point: lifespan, CORS, logging, and router registration."""

import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from hand2notes.storage.database import init_db

from .middleware import RequestLoggingMiddleware, configure_logging, register_exception_handlers

# Crops and artifact previews are served from a temp directory that stages
# preprocessed images. The Electron renderer can access them at /static/crops/.
_CROPS_DIR = Path(os.environ.get("HAND2NOTES_CROPS_DIR", tempfile.gettempdir())) / "hand2notes_crops"

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
    _mount_static(app)
    return app


def _mount_static(app: FastAPI) -> None:
    _CROPS_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/static/crops", StaticFiles(directory=str(_CROPS_DIR)), name="crops")


def _register_routers(app: FastAPI) -> None:
    from .routers import config, pipeline, sessions
    app.include_router(sessions.router, prefix=API_PREFIX)
    app.include_router(pipeline.router, prefix=API_PREFIX)
    app.include_router(config.router, prefix=API_PREFIX)


app = create_app()
