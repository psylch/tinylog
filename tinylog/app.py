"""FastAPI application factory."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .api.auth import AdminKeyMiddleware
from .api.sessions import router as sessions_router
from .api.statistics import router as statistics_router
from .api.files import router as files_router
from .config import Config
from .db import TinyLogDB
from .sources.agno import AgnoSource


def create_app(config: Config) -> FastAPI:
    app = FastAPI(title="TinyLog", version="0.1.0")

    # Auth middleware
    app.add_middleware(AdminKeyMiddleware, admin_key=config.admin_key)

    # Data source
    if config.source_type == "agno":
        if not config.db_path:
            raise ValueError("db_path is required for agno source type")
        source = AgnoSource(config.db_path)
    else:
        raise ValueError(f"Unknown source type: {config.source_type}")

    app.state.source = source
    app.state.config = config

    # TinyLog's own DB
    tinylog_db = TinyLogDB(config.data_dir)
    app.state.tinylog_db = tinylog_db

    # API routes
    app.include_router(sessions_router)
    app.include_router(statistics_router)
    app.include_router(files_router)

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    @app.get("/api/config")
    async def frontend_config():
        return {
            "theme": config.theme,
            "title": config.title,
            "auth_required": bool(config.admin_key),
        }

    # Static files (frontend) — mount last so API routes take priority
    frontend_dir = Path(__file__).parent / "frontend"
    if frontend_dir.exists() and (frontend_dir / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

    return app
