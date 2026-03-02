"""Auto-detect source type from database schema or directory structure."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def detect_source_type(path: str) -> str:
    """Inspect the given path and return the matching source type name.

    For SQLite files, checks table names.
    For directories, checks file structure.

    Raises ValueError if detection fails.
    """
    p = Path(path)

    if p.is_dir():
        # Claude SDK: session subdirectories with JSONL files
        if any(p.glob("*/*.jsonl")):
            return "claude-agent-sdk"
        # JSON import: directory of .json files
        if any(p.glob("*.json")):
            return "json-import"
        raise ValueError(
            f"Cannot auto-detect source from directory: {path}. "
            "Expected JSONL session files or JSON import files."
        )

    if not p.is_file():
        raise ValueError(f"Path does not exist: {path}")

    # SQLite file — inspect tables
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        conn.close()
    except sqlite3.OperationalError as e:
        raise ValueError(f"Cannot open as SQLite database: {path} ({e})") from e

    if "agno_sessions" in tables:
        return "agno"
    if "message_store" in tables:
        return "langchain"
    if "chat_completions" in tables:
        return "autogen"
    if "StorageSession" in tables or "StorageEvent" in tables:
        return "adk"

    raise ValueError(
        f"Cannot auto-detect source type from SQLite tables: {sorted(tables)}"
    )
