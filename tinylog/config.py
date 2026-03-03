"""Configuration loading: env vars with optional TOML file."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-untyped]


@dataclass
class Config:
    host: str = "0.0.0.0"
    port: int = 7892
    admin_key: str = ""
    source_type: str = "auto"
    db_path: str = ""
    data_dir: str = "./tinylog_data"
    theme: str = "dark"
    title: str = "TinyLog"


def load_config(
    *,
    db_path: str | None = None,
    source_type: str | None = None,
    port: int | None = None,
    host: str | None = None,
    admin_key: str | None = None,
    data_dir: str | None = None,
) -> Config:
    """Load config from TOML file, then env vars, then CLI args (highest priority)."""
    cfg = Config()

    # 1. Try loading tinylog.toml from cwd
    toml_path = Path("tinylog.toml")
    if toml_path.exists():
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
        server = data.get("server", {})
        cfg.host = server.get("host", cfg.host)
        cfg.port = server.get("port", cfg.port)
        cfg.admin_key = server.get("admin_key", cfg.admin_key)
        source = data.get("source", {})
        cfg.source_type = source.get("type", cfg.source_type)
        cfg.db_path = source.get("db_path", cfg.db_path)
        storage = data.get("storage", {})
        cfg.data_dir = storage.get("data_dir", cfg.data_dir)
        ui = data.get("ui", {})
        cfg.theme = ui.get("theme", cfg.theme)
        cfg.title = ui.get("title", cfg.title)

    # 2. Env vars override TOML
    cfg.host = os.getenv("TINYLOG_HOST", cfg.host)
    cfg.port = int(os.getenv("TINYLOG_PORT", str(cfg.port)))
    cfg.admin_key = os.getenv("TINYLOG_ADMIN_KEY", cfg.admin_key)
    cfg.source_type = os.getenv("TINYLOG_SOURCE_TYPE", cfg.source_type)
    cfg.db_path = os.getenv("TINYLOG_DB", cfg.db_path)
    cfg.data_dir = os.getenv("TINYLOG_DATA_DIR", cfg.data_dir)
    cfg.theme = os.getenv("TINYLOG_THEME", cfg.theme)
    cfg.title = os.getenv("TINYLOG_TITLE", cfg.title)

    # 3. CLI args override everything (None means not provided)
    if db_path is not None:
        cfg.db_path = db_path
    if port is not None:
        cfg.port = port
    if host is not None:
        cfg.host = host
    if admin_key is not None:
        cfg.admin_key = admin_key
    if source_type is not None:
        cfg.source_type = source_type
    if data_dir is not None:
        cfg.data_dir = data_dir

    return cfg
