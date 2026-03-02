"""Sessions API routes."""

from __future__ import annotations

import logging
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query, Request

logger = logging.getLogger("tinylog")

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("")
async def list_sessions(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = Query("created_at_desc"),
    date_from: float | None = Query(None),
    date_to: float | None = Query(None),
    keyword: str | None = Query(None),
):
    try:
        source = request.app.state.source
        items, total = source.list_sessions(
            page=page,
            page_size=page_size,
            date_from=date_from,
            date_to=date_to,
            keyword=keyword,
            sort=sort,
        )
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [asdict(item) for item in items],
        }
    except Exception as e:
        logger.exception("Failed to list sessions")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}")
async def get_session(request: Request, session_id: str):
    try:
        source = request.app.state.source
        detail = source.get_session(session_id)
        if detail is None:
            raise HTTPException(status_code=404, detail="Session not found")

        # Merge files from tinylog.db
        tinylog_db = request.app.state.tinylog_db
        if tinylog_db:
            files = tinylog_db.get_files_for_session(session_id)
            detail.files = [
                {
                    "id": f["id"],
                    "filename": f["filename"],
                    "mime_type": f["mime_type"],
                    "size": f["size"],
                    "url": f"/api/files/{f['id']}",
                }
                for f in files
            ]

        result = asdict(detail)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get session %s", session_id)
        raise HTTPException(status_code=500, detail=str(e))
