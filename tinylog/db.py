"""TinyLog's own SQLite database for files metadata."""

from __future__ import annotations

import sqlite3
from pathlib import Path


_SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    size INTEGER NOT NULL,
    session_id TEXT,
    stored_path TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_files_session_id ON files (session_id);
CREATE INDEX IF NOT EXISTS idx_files_created_at ON files (created_at);
"""


class TinyLogDB:
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.files_dir = self.data_dir / "files"
        self.files_dir.mkdir(exist_ok=True)
        db_path = self.data_dir / "tinylog.db"
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)

    def insert_file(
        self,
        file_id: str,
        filename: str,
        mime_type: str,
        size: int,
        session_id: str | None,
        stored_path: str,
        created_at: float,
    ) -> None:
        self._conn.execute(
            "INSERT INTO files (id, filename, mime_type, size, session_id, stored_path, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (file_id, filename, mime_type, size, session_id, stored_path, created_at),
        )
        self._conn.commit()

    def list_files(
        self, page: int = 1, page_size: int = 20, session_id: str | None = None
    ) -> tuple[list[dict], int]:
        where = ""
        params: list = []
        if session_id:
            where = "WHERE session_id = ?"
            params.append(session_id)

        total = self._conn.execute(
            f"SELECT COUNT(*) FROM files {where}", params
        ).fetchone()[0]

        offset = (page - 1) * page_size
        rows = self._conn.execute(
            f"SELECT * FROM files {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ).fetchall()

        items = [dict(row) for row in rows]
        return items, total

    def get_file(self, file_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM files WHERE id = ?", (file_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_files_for_session(self, session_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM files WHERE session_id = ? ORDER BY created_at",
            (session_id,),
        ).fetchall()
        return [dict(row) for row in rows]
