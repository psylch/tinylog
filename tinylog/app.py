"""FastAPI application factory."""

from __future__ import annotations

import logging
from importlib.metadata import version as pkg_version
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api.auth import AdminKeyMiddleware
from .api.sessions import router as sessions_router
from .api.statistics import router as statistics_router
from .api.files import router as files_router
from .config import Config
from .db import TinyLogDB
from .sources import get_source
from .sources.detect import detect_source_type

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


def create_app(config: Config) -> FastAPI:
    _version = pkg_version("tinylog-llm")
    app = FastAPI(title="TinyLog", version=_version)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Auth middleware
    app.add_middleware(AdminKeyMiddleware, admin_key=config.admin_key)

    # Data source — auto-detect if needed
    if not config.db_path:
        raise ValueError("db_path is required")

    source_type = config.source_type
    if source_type == "auto" or not source_type:
        source_type = detect_source_type(config.db_path)

    source_cls = get_source(source_type)
    source = source_cls(config.db_path)

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
        return {"status": "ok", "version": _version}

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
