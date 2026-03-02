"""ADKSource: read-only adapter for Google ADK's DatabaseSessionService SQLite DB."""

from __future__ import annotations

import json
from collections import defaultdict
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
    open_readonly_db,
    parse_json,
    ts_to_date,
)


def _parse_event_data(raw: Any) -> dict:
    """Parse event_data JSON, returning empty dict on failure."""
    data = parse_json(raw)
    return data if isinstance(data, dict) else {}


def _extract_parts(event_data: dict) -> list[dict]:
    """Extract content.parts from an event_data dict."""
    content = event_data.get("content")
    if not content or not isinstance(content, dict):
        return []
    parts = content.get("parts")
    return parts if isinstance(parts, list) else []


def _event_role(event_data: dict) -> str:
    """Map ADK author to normalized role: 'user' stays 'user', anything else is 'assistant'."""
    author = event_data.get("author", "")
    return "user" if author == "user" else "assistant"


def _parts_text(parts: list[dict]) -> str:
    """Concatenate all text parts."""
    texts = []
    for p in parts:
        if "text" in p:
            texts.append(p["text"])
    return "\n".join(texts)


def _parts_tool_calls(parts: list[dict]) -> list[dict] | None:
    """Extract functionCall parts into tool_calls list."""
    calls = []
    for p in parts:
        fc = p.get("functionCall")
        if fc and isinstance(fc, dict):
            calls.append({
                "id": fc.get("id"),
                "name": fc.get("name"),
                "args": json.dumps(fc.get("args", {}), ensure_ascii=False) if fc.get("args") else None,
            })
    return calls or None


def _parts_tool_response(parts: list[dict]) -> tuple[str | None, str | None, str | None]:
    """Extract first functionResponse → (tool_name, tool_call_id, result_json)."""
    for p in parts:
        fr = p.get("functionResponse")
        if fr and isinstance(fr, dict):
            result = fr.get("response")
            return (
                fr.get("name"),
                fr.get("id"),
                json.dumps(result, ensure_ascii=False) if result is not None else None,
            )
    return None, None, None


def _event_usage(event_data: dict) -> dict | None:
    """Extract usage_metadata as token_metrics dict."""
    usage = event_data.get("usage_metadata")
    if not usage or not isinstance(usage, dict):
        return None
    total = usage.get("total_token_count", 0) or 0
    prompt = usage.get("prompt_token_count", 0) or 0
    candidates = usage.get("candidates_token_count", 0) or 0
    if total == 0 and prompt == 0 and candidates == 0:
        return None
    return {
        "total_tokens": total,
        "input_tokens": prompt,
        "output_tokens": candidates,
    }


class ADKSource(DataSource):
    """Read-only adapter for Google ADK's DatabaseSessionService SQLite DB."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = open_readonly_db(db_path)

    # ------------------------------------------------------------------
    # list_sessions
    # ------------------------------------------------------------------

    def list_sessions(
        self,
        page: int = 1,
        page_size: int = 20,
        date_from: float | None = None,
        date_to: float | None = None,
        keyword: str | None = None,
        sort: str = "created_at_desc",
    ) -> tuple[list[SessionSummary], int]:
        conditions: list[str] = []
        params: list[Any] = []

        if date_from is not None:
            conditions.append("s.create_time >= ?")
            params.append(date_from)
        if date_to is not None:
            conditions.append("s.create_time <= ?")
            params.append(date_to)
        if keyword:
            # Search in event_data text across related events
            conditions.append(
                "EXISTS (SELECT 1 FROM StorageEvent e2 "
                "WHERE e2.app_name = s.app_name AND e2.user_id = s.user_id "
                "AND e2.session_id = s.id AND e2.event_data LIKE ?)"
            )
            params.append(f"%{keyword}%")

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        sort_map = {
            "created_at_desc": "s.create_time DESC",
            "created_at_asc": "s.create_time ASC",
        }
        order_by = sort_map.get(sort, "s.create_time DESC")

        # Count
        total = self._conn.execute(
            f"SELECT COUNT(*) FROM StorageSession s {where}", params
        ).fetchone()[0]

        # Fetch page
        offset = (page - 1) * page_size
        rows = self._conn.execute(
            f"""SELECT s.app_name, s.user_id, s.id, s.state,
                       s.create_time, s.update_time
                FROM StorageSession s {where}
                ORDER BY {order_by}
                LIMIT ? OFFSET ?""",
            params + [page_size, offset],
        ).fetchall()

        # Fetch ALL events for the page's sessions in one query (avoid N+1)
        session_ids = [row["id"] for row in rows]
        events_by_session: dict[str, list] = defaultdict(list)
        if session_ids:
            placeholders = ",".join("?" * len(session_ids))
            all_events = self._conn.execute(
                f"""SELECT app_name, user_id, session_id, event_data, timestamp
                    FROM StorageEvent
                    WHERE session_id IN ({placeholders})
                    ORDER BY timestamp""",
                session_ids,
            ).fetchall()
            for ev in all_events:
                events_by_session[ev["session_id"]].append(ev)

        items: list[SessionSummary] = []
        for row in rows:
            events = events_by_session[row["id"]]

            first_query = ""
            message_count = 0
            total_tokens = 0
            input_tokens = 0
            output_tokens = 0
            tool_names_seen: set[str] = set()
            tool_names_list: list[str] = []

            for ev in events:
                ed = _parse_event_data(ev["event_data"])
                parts = _extract_parts(ed)
                role = _event_role(ed)

                # Count only events that have content parts (skip empty/system events)
                has_content = bool(parts)
                if has_content:
                    message_count += 1

                # First user query
                if not first_query and role == "user":
                    text = _parts_text(parts)
                    if text:
                        first_query = text[:200]

                # Tokens
                usage = _event_usage(ed)
                if usage:
                    total_tokens += usage["total_tokens"]
                    input_tokens += usage["input_tokens"]
                    output_tokens += usage["output_tokens"]

                # Tool names
                for p in parts:
                    fc = p.get("functionCall")
                    if fc and isinstance(fc, dict):
                        name = fc.get("name", "")
                        if name and name not in tool_names_seen:
                            tool_names_seen.add(name)
                            tool_names_list.append(name)

            duration = None
            if row["create_time"] and row["update_time"]:
                duration = row["update_time"] - row["create_time"]
                if duration < 0:
                    duration = None

            items.append(SessionSummary(
                session_id=row["id"],
                created_at=row["create_time"] or 0,
                updated_at=row["update_time"],
                first_query=first_query,
                message_count=message_count,
                model=None,  # ADK schema doesn't store model info in sessions
                status="COMPLETED",
                total_tokens=total_tokens,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration=duration,
                ttft=None,  # Not available in ADK schema
                tool_names=tool_names_list,
                has_images=False,
            ))

        return items, total

    # ------------------------------------------------------------------
    # get_session
    # ------------------------------------------------------------------

    def get_session(self, session_id: str) -> SessionDetail | None:
        row = self._conn.execute(
            "SELECT * FROM StorageSession WHERE id = ?", (session_id,)
        ).fetchone()
        if not row:
            return None

        events = self._conn.execute(
            """SELECT event_data, timestamp FROM StorageEvent
               WHERE app_name = ? AND user_id = ? AND session_id = ?
               ORDER BY timestamp""",
            (row["app_name"], row["user_id"], row["id"]),
        ).fetchall()

        messages: list[Message] = []
        tools: list[dict] = []
        total_tokens = 0
        input_tokens = 0
        output_tokens = 0

        # Collect tool results by call id for later matching
        tool_results: dict[str, Any] = {}

        # First pass: collect functionResponse results
        for ev in events:
            ed = _parse_event_data(ev["event_data"])
            parts = _extract_parts(ed)
            for p in parts:
                fr = p.get("functionResponse")
                if fr and isinstance(fr, dict):
                    call_id = fr.get("id")
                    if call_id:
                        tool_results[call_id] = fr.get("response")

        # Second pass: build messages
        idx = 0
        for ev in events:
            ed = _parse_event_data(ev["event_data"])
            parts = _extract_parts(ed)
            if not parts:
                # Still collect usage from events without content
                usage = _event_usage(ed)
                if usage:
                    total_tokens += usage["total_tokens"]
                    input_tokens += usage["input_tokens"]
                    output_tokens += usage["output_tokens"]
                continue

            role = _event_role(ed)
            text = _parts_text(parts)
            tool_calls = _parts_tool_calls(parts)
            tool_name_resp, tool_call_id_resp, _ = _parts_tool_response(parts)

            # Attach results to tool_calls
            if tool_calls:
                for tc in tool_calls:
                    tc_id = tc.get("id")
                    if tc_id and tc_id in tool_results:
                        tc["result"] = json.dumps(tool_results[tc_id], ensure_ascii=False) if tool_results[tc_id] is not None else None

                # Also build tools list
                for tc in tool_calls:
                    tools.append({
                        "tool_call_id": tc.get("id"),
                        "tool_name": tc.get("name"),
                        "tool_args": tc.get("args"),
                        "result": tc.get("result"),
                        "created_at": ev["timestamp"],
                    })

            usage = _event_usage(ed)
            if usage:
                total_tokens += usage["total_tokens"]
                input_tokens += usage["input_tokens"]
                output_tokens += usage["output_tokens"]

            # For functionResponse events, build a "tool" role message
            if tool_name_resp:
                fr_resp = _parts_tool_response(parts)
                messages.append(Message(
                    index=idx,
                    role="tool",
                    content=fr_resp[2] or "",
                    created_at=ev["timestamp"],
                    tool_name=tool_name_resp,
                    tool_call_id=tool_call_id_resp,
                ))
                idx += 1
                continue

            messages.append(Message(
                index=idx,
                role=role,
                content=text,
                created_at=ev["timestamp"],
                token_metrics=usage,
                tool_calls=tool_calls,
            ))
            idx += 1

        metrics = {
            "total_tokens": total_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }

        return SessionDetail(
            session_id=session_id,
            created_at=row["create_time"] or 0,
            model=None,
            metrics=metrics,
            messages=messages,
            tools=tools,
            files=[],
        )

    # ------------------------------------------------------------------
    # get_daily_metrics
    # ------------------------------------------------------------------

    def get_daily_metrics(self, date_from: str, date_to: str) -> list[DailyMetrics]:
        ts_from, ts_to = date_range_to_ts(date_from, date_to)

        rows = self._conn.execute(
            """SELECT s.id, s.app_name, s.user_id, s.create_time, s.update_time
               FROM StorageSession s
               WHERE s.create_time >= ? AND s.create_time < ?
               ORDER BY s.create_time""",
            (ts_from, ts_to),
        ).fetchall()

        daily: dict[str, dict] = defaultdict(new_daily_bucket)

        # Fetch ALL events for the date range's sessions in one query (avoid N+1)
        session_ids = [row["id"] for row in rows]
        events_by_session: dict[str, list] = defaultdict(list)
        if session_ids:
            placeholders = ",".join("?" * len(session_ids))
            all_events = self._conn.execute(
                f"""SELECT session_id, event_data FROM StorageEvent
                    WHERE session_id IN ({placeholders})""",
                session_ids,
            ).fetchall()
            for ev in all_events:
                events_by_session[ev["session_id"]].append(ev)

        for row in rows:
            date = ts_to_date(row["create_time"])
            d = daily[date]
            d["sessions"] += 1

            if row["create_time"] and row["update_time"]:
                dur = row["update_time"] - row["create_time"]
                if dur >= 0:
                    d["durations"].append(dur)

            events = events_by_session[row["id"]]

            for ev in events:
                ed = _parse_event_data(ev["event_data"])
                parts = _extract_parts(ed)
                if parts:
                    d["messages"] += 1
                usage = _event_usage(ed)
                if usage:
                    d["total_tokens"] += usage["total_tokens"]
                    d["input_tokens"] += usage["input_tokens"]
                    d["output_tokens"] += usage["output_tokens"]

        return build_daily_metrics(daily)

    # ------------------------------------------------------------------
    # get_tool_stats
    # ------------------------------------------------------------------

    def get_tool_stats(self, date_from: str, date_to: str) -> dict:
        ts_from, ts_to = date_range_to_ts(date_from, date_to)

        rows = self._conn.execute(
            """SELECT e.event_data, s.create_time
               FROM StorageEvent e
               JOIN StorageSession s
                 ON e.app_name = s.app_name AND e.user_id = s.user_id AND e.session_id = s.id
               WHERE s.create_time >= ? AND s.create_time < ?""",
            (ts_from, ts_to),
        ).fetchall()

        summary: dict[str, int] = defaultdict(int)
        daily_tools: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for row in rows:
            ed = _parse_event_data(row["event_data"])
            parts = _extract_parts(ed)
            date = ts_to_date(row["create_time"])
            for p in parts:
                fc = p.get("functionCall")
                if fc and isinstance(fc, dict):
                    name = fc.get("name", "unknown")
                    summary[name] += 1
                    daily_tools[date][name] += 1

        return build_tool_stats_result(summary, daily_tools)


# Register this source adapter
from . import register_source  # noqa: E402

register_source("adk", ADKSource)
