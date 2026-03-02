"""Files API routes."""

from __future__ import annotations

import time
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request, UploadFile, File

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("")
async def list_files(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session_id: str | None = Query(None),
):
    tinylog_db = request.app.state.tinylog_db
    if not tinylog_db:
        return {"total": 0, "page": page, "page_size": page_size, "items": []}

    items, total = tinylog_db.list_files(page=page, page_size=page_size, session_id=session_id)
    for item in items:
        item["url"] = f"/api/files/{item['id']}"
        item.pop("stored_path", None)
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.get("/{file_id}")
async def get_file(request: Request, file_id: str):
    tinylog_db = request.app.state.tinylog_db
    if not tinylog_db:
        raise HTTPException(status_code=404, detail="File not found")

    file_meta = tinylog_db.get_file(file_id)
    if not file_meta:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = Path(file_meta["stored_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    from fastapi.responses import FileResponse
    return FileResponse(
        path=str(file_path),
        media_type=file_meta["mime_type"],
        filename=file_meta["filename"],
    )


@router.post("")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    session_id: str | None = Query(None),
):
    tinylog_db = request.app.state.tinylog_db
    if not tinylog_db:
        raise HTTPException(status_code=500, detail="File storage not configured")

    file_id = str(uuid.uuid4())
    content = await file.read()
    size = len(content)

    # Store file to disk
    stored_path = tinylog_db.files_dir / file_id
    stored_path.write_bytes(content)

    tinylog_db.insert_file(
        file_id=file_id,
        filename=file.filename or "upload",
        mime_type=file.content_type or "application/octet-stream",
        size=size,
        session_id=session_id,
        stored_path=str(stored_path),
        created_at=time.time(),
    )

    return {
        "id": file_id,
        "filename": file.filename,
        "mime_type": file.content_type,
        "size": size,
        "url": f"/api/files/{file_id}",
    }
