"""ClaudeSDKSource: read-only adapter for Claude Code / Agent SDK session JSONL files."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .base import (
    DataSource,
    DailyMetrics,
    Message,
    SessionDetail,
    SessionSummary,
)
from .utils import (
    build_daily_metrics,
    build_tool_stats_result,
    date_range_to_ts,
    new_daily_bucket,
    ts_to_date,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_timestamp(ts_str: str | None) -> float | None:
    """ISO-8601 timestamp string to unix epoch seconds."""
    if not ts_str:
        return None
    from datetime import datetime

    try:
        # Handle both "Z" suffix and "+00:00"
        ts_str = ts_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts_str)
        return dt.timestamp()
    except (ValueError, TypeError):
        return None


def _read_jsonl(path: str | Path) -> list[dict]:
    """Read all JSON lines from a file, skipping malformed lines."""
    entries: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def _extract_text(content: Any) -> str:
    """Extract text from a message content field.

    content can be:
    - a plain string (user messages)
    - a list of content blocks (assistant/user messages)
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif block.get("type") == "tool_result":
                    result_content = block.get("content", "")
                    if isinstance(result_content, str):
                        parts.append(result_content)
        return "\n".join(parts)
    return ""


def _extract_thinking(content: Any) -> str | None:
    """Extract thinking blocks from assistant content."""
    if not isinstance(content, list):
        return None
    parts: list[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "thinking":
            text = block.get("thinking", "")
            if text:
                parts.append(text)
    return "\n".join(parts) if parts else None


def _extract_images(content: Any) -> list[dict] | None:
    """Extract image blocks from message content.

    Returns list of dicts with {id, media_type, data} or None.
    """
    if not isinstance(content, list):
        return None
    images: list[dict] = []
    for i, block in enumerate(content):
        if isinstance(block, dict) and block.get("type") == "image":
            source = block.get("source", {})
            if source.get("type") == "base64" and source.get("data"):
                media_type = source.get("media_type", "image/png")
                images.append({
                    "id": f"img-{i}",
                    "media_type": media_type,
                    "data": source["data"],
                })
    return images or None


def _extract_tool_calls(content: Any) -> list[dict] | None:
    """Extract tool_use blocks from assistant content."""
    if not isinstance(content, list):
        return None
    calls: list[dict] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_use":
            calls.append({
                "id": block.get("id"),
                "name": block.get("name"),
                "args": json.dumps(block.get("input", {}), ensure_ascii=False),
            })
    return calls or None


def _extract_tool_result_info(content: Any) -> tuple[str | None, str | None]:
    """Extract tool_use_id and tool_name from a tool_result user message.

    Returns (tool_call_id, tool_name).
    tool_name is not present in tool_result blocks, so we return None for it.
    """
    if not isinstance(content, list):
        return None, None
    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_result":
            return block.get("tool_use_id"), None
    return None, None


def _extract_tool_result_content(content: list) -> str:
    """Extract the actual result content from a tool_result block."""
    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_result":
            inner = block.get("content", "")
            if isinstance(inner, str):
                return inner
            if isinstance(inner, list):
                parts = []
                for part in inner:
                    if isinstance(part, dict) and part.get("type") == "text":
                        parts.append(part.get("text", ""))
                return "\n".join(parts)
    return ""


def _is_conversation_message(entry: dict) -> bool:
    """Return True if the JSONL entry is a user or assistant conversation message."""
    entry_type = entry.get("type")
    if entry_type not in ("user", "assistant"):
        return False
    # Must have a message field
    return bool(entry.get("message"))


def _collect_session_data(entries: list[dict]) -> dict:
    """Process JSONL entries into structured session data.

    Returns dict with keys: messages, model, created_at, updated_at,
    input_tokens, output_tokens, tool_names, first_query.
    """
    messages: list[dict] = []
    tool_results: dict[str, str] = {}  # tool_call_id -> result content
    all_images: list[dict] = []  # collected file entries for images
    has_images = False
    model: str | None = None
    created_at: float | None = None
    updated_at: float | None = None
    total_input_tokens = 0
    total_output_tokens = 0
    tool_names_seen: set[str] = set()
    tool_names_ordered: list[str] = []
    first_query: str = ""

    for entry in entries:
        if not _is_conversation_message(entry):
            continue

        ts = _parse_timestamp(entry.get("timestamp"))
        if ts is not None:
            if created_at is None or ts < created_at:
                created_at = ts
            if updated_at is None or ts > updated_at:
                updated_at = ts

        msg = entry["message"]
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        entry_type = entry["type"]

        # Track model from assistant messages
        if entry_type == "assistant" and msg.get("model"):
            model = msg["model"]

        # Track tokens from assistant messages
        if entry_type == "assistant":
            usage = msg.get("usage", {}) or {}
            total_input_tokens += usage.get("input_tokens", 0) or 0
            total_output_tokens += usage.get("output_tokens", 0) or 0

        # Build message record
        text = _extract_text(content)
        thinking = _extract_thinking(content) if entry_type == "assistant" else None
        tool_calls = _extract_tool_calls(content) if entry_type == "assistant" else None
        tool_call_id, tool_name = (None, None)
        image_blocks = _extract_images(content)

        if entry_type == "user" and isinstance(content, list):
            tool_call_id, tool_name = _extract_tool_result_info(content)

        # Track tool names
        if tool_calls:
            for tc in tool_calls:
                name = tc.get("name", "")
                if name and name not in tool_names_seen:
                    tool_names_seen.add(name)
                    tool_names_ordered.append(name)

        # First user query
        if not first_query and role == "user" and text and not tool_call_id:
            first_query = text[:200]

        # Collect tool_result content for linking to tool_calls later
        if tool_call_id:
            result_content = _extract_tool_result_content(content) if isinstance(content, list) else text
            if result_content:
                tool_results[tool_call_id] = result_content

        # Collect image file entries and track IDs for this message
        msg_image_ids: list[str] | None = None
        if image_blocks:
            has_images = True
            msg_image_ids = []
            for img in image_blocks:
                # Create a unique file ID using message index
                file_id = f"{len(messages)}-{img['id']}"
                msg_image_ids.append(file_id)
                all_images.append({
                    "id": file_id,
                    "media_type": img["media_type"],
                    "data": img["data"],
                })

        # Skip empty messages: assistant messages with only tool_use (no text),
        # and user messages that are only tool_result (no user text).
        if not text and not thinking and tool_call_id and not msg_image_ids:
            # This is a tool_result user message with no visible text — skip as bubble,
            # the result is already linked via tool_results dict
            continue
        if not text and not thinking and not tool_calls and not msg_image_ids:
            # Completely empty message — skip
            continue

        messages.append({
            "role": role,
            "content": text,
            "created_at": ts,
            "thinking": thinking,
            "tool_calls": tool_calls,
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "images": msg_image_ids,
            "token_metrics": msg.get("usage") if entry_type == "assistant" else None,
        })

    return {
        "messages": messages,
        "model": model,
        "created_at": created_at or 0.0,
        "updated_at": updated_at,
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
        "total_tokens": total_input_tokens + total_output_tokens,
        "tool_names": tool_names_ordered,
        "first_query": first_query,
        "tool_results": tool_results,
        "has_images": has_images,
        "all_images": all_images,
    }


# ---------------------------------------------------------------------------
# Index entry (lightweight cache for list_sessions)
# ---------------------------------------------------------------------------

class _SessionIndex:
    """Lightweight index entry for a session."""

    __slots__ = (
        "session_id", "jsonl_path", "created_at", "updated_at",
        "first_query", "message_count", "model", "total_tokens",
        "input_tokens", "output_tokens", "tool_names", "has_images",
    )

    def __init__(self, session_id: str, jsonl_path: str, data: dict):
        self.session_id = session_id
        self.jsonl_path = jsonl_path
        self.created_at = data["created_at"]
        self.updated_at = data["updated_at"]
        self.first_query = data["first_query"]
        self.message_count = len(data["messages"])
        self.model = data["model"]
        self.total_tokens = data["total_tokens"]
        self.input_tokens = data["input_tokens"]
        self.output_tokens = data["output_tokens"]
        self.tool_names = data["tool_names"]
        self.has_images = data["has_images"]


# ---------------------------------------------------------------------------
# Source adapter
# ---------------------------------------------------------------------------

class ClaudeSDKSource(DataSource):
    """Read-only adapter for Claude Code / Agent SDK JSONL session logs.

    Constructor receives a directory path. The directory is expected to
    contain one or more project subdirectories, each with `<session-id>.jsonl`
    files. It also accepts a direct project directory containing JSONL files.
    """

    def __init__(self, dir_path: str):
        self.dir_path = dir_path
        self._index: list[_SessionIndex] = []
        self._build_index()

    def _build_index(self) -> None:
        """Scan for JSONL session files and build a lightweight index."""
        root = Path(self.dir_path)
        jsonl_files: list[Path] = []

        if not root.is_dir():
            return

        # Collect all .jsonl files (may be directly in root or in subdirectories)
        for path in root.rglob("*.jsonl"):
            # Skip subagent files — they are sub-sessions
            if "subagents" in path.parts:
                continue
            jsonl_files.append(path)

        for jsonl_path in jsonl_files:
            session_id = jsonl_path.stem
            try:
                entries = _read_jsonl(jsonl_path)
                if not entries:
                    continue
                data = _collect_session_data(entries)
                if not data["messages"]:
                    continue
                self._index.append(
                    _SessionIndex(session_id, str(jsonl_path), data)
                )
            except Exception:
                continue

        # Sort by created_at descending
        self._index.sort(key=lambda s: s.created_at, reverse=True)

    def _filter_and_sort(
        self,
        date_from: float | None = None,
        date_to: float | None = None,
        keyword: str | None = None,
        sort: str = "created_at_desc",
    ) -> list[_SessionIndex]:
        """Return filtered and sorted index entries."""
        result = self._index

        if date_from is not None:
            result = [s for s in result if s.created_at >= date_from]
        if date_to is not None:
            result = [s for s in result if s.created_at <= date_to]
        if keyword:
            kw = keyword.lower()
            result = [s for s in result if kw in s.first_query.lower()]

        sort_map = {
            "created_at_desc": lambda s: -s.created_at,
            "created_at_asc": lambda s: s.created_at,
            "tokens_desc": lambda s: -s.total_tokens,
            "tokens_asc": lambda s: s.total_tokens,
        }
        key_fn = sort_map.get(sort, lambda s: -s.created_at)
        result = sorted(result, key=key_fn)

        return result

    # ------ DataSource interface ------

    def list_sessions(
        self,
        page: int = 1,
        page_size: int = 20,
        date_from: float | None = None,
        date_to: float | None = None,
        keyword: str | None = None,
        sort: str = "created_at_desc",
    ) -> tuple[list[SessionSummary], int]:
        filtered = self._filter_and_sort(date_from, date_to, keyword, sort)
        total = len(filtered)
        offset = (page - 1) * page_size
        page_items = filtered[offset : offset + page_size]

        items: list[SessionSummary] = []
        for s in page_items:
            items.append(SessionSummary(
                session_id=s.session_id,
                created_at=s.created_at,
                updated_at=s.updated_at,
                first_query=s.first_query,
                message_count=s.message_count,
                model=s.model,
                status="COMPLETED",
                total_tokens=s.total_tokens,
                input_tokens=s.input_tokens,
                output_tokens=s.output_tokens,
                duration=None,
                ttft=None,
                tool_names=s.tool_names,
                has_images=s.has_images,
            ))

        return items, total

    def get_session(self, session_id: str) -> SessionDetail | None:
        # Find the session in the index
        idx_entry = None
        for s in self._index:
            if s.session_id == session_id:
                idx_entry = s
                break
        if idx_entry is None:
            return None

        entries = _read_jsonl(idx_entry.jsonl_path)
        data = _collect_session_data(entries)

        messages: list[Message] = []
        tool_results: dict[str, str] = data.get("tool_results", {})

        # Build Message objects
        for idx, m in enumerate(data["messages"]):
            messages.append(Message(
                index=idx,
                role=m["role"],
                content=m["content"],
                created_at=m.get("created_at"),
                reasoning=m.get("thinking"),
                token_metrics=m.get("token_metrics"),
                tool_calls=m.get("tool_calls"),
                tool_name=m.get("tool_name"),
                tool_call_id=m.get("tool_call_id"),
                images=m.get("images"),
            ))

        # Attach tool results to assistant tool_calls
        for msg in messages:
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    tc_id = tc.get("id")
                    if tc_id and tc_id in tool_results:
                        tc["result"] = tool_results[tc_id]

        # Collect unique tools as tool definitions
        tools: list[dict] = []
        for name in data["tool_names"]:
            tools.append({"tool_name": name})

        metrics = {
            "total_tokens": data["total_tokens"],
            "input_tokens": data["input_tokens"],
            "output_tokens": data["output_tokens"],
        }

        # Build file entries for images (data URLs)
        files: list[dict] = []
        for img in data.get("all_images", []):
            ext = img["media_type"].split("/")[-1]
            files.append({
                "id": img["id"],
                "filename": f"{img['id']}.{ext}",
                "mime_type": img["media_type"],
                "size": len(img["data"]),
                "url": f"data:{img['media_type']};base64,{img['data']}",
            })

        return SessionDetail(
            session_id=session_id,
            created_at=data["created_at"],
            model=data["model"],
            metrics=metrics,
            messages=messages,
            tools=tools,
            files=files,
        )

    def get_daily_metrics(self, date_from: str, date_to: str) -> list[DailyMetrics]:
        ts_from, ts_to = date_range_to_ts(date_from, date_to)

        daily: dict[str, dict] = defaultdict(new_daily_bucket)

        for s in self._index:
            if s.created_at < ts_from or s.created_at >= ts_to:
                continue
            date = ts_to_date(s.created_at)
            d = daily[date]
            d["sessions"] += 1
            d["messages"] += s.message_count
            d["total_tokens"] += s.total_tokens
            d["input_tokens"] += s.input_tokens
            d["output_tokens"] += s.output_tokens

        return build_daily_metrics(daily)

    def get_tool_stats(self, date_from: str, date_to: str) -> dict:
        ts_from, ts_to = date_range_to_ts(date_from, date_to)

        summary: dict[str, int] = defaultdict(int)
        daily_tools: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for s in self._index:
            if s.created_at < ts_from or s.created_at >= ts_to:
                continue
            date = ts_to_date(s.created_at)

            # Need to read actual file for per-tool counts
            try:
                entries = _read_jsonl(s.jsonl_path)
            except Exception:
                continue

            for entry in entries:
                if entry.get("type") != "assistant":
                    continue
                msg = entry.get("message", {})
                content = msg.get("content", [])
                if not isinstance(content, list):
                    continue
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        name = block.get("name", "unknown")
                        summary[name] += 1
                        daily_tools[date][name] += 1

        return build_tool_stats_result(summary, daily_tools)


# Register this source adapter
from . import register_source  # noqa: E402

register_source("claude-agent-sdk", ClaudeSDKSource)
