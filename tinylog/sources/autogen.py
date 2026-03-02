"""AutoGenSource: read-only adapter for AutoGen's runtime_logging SQLite database."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
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
    stringify_content,
    ts_to_date,
)


def _parse_ts(ts_str: str | None) -> float | None:
    """Parse a timestamp string to unix timestamp. Tries common formats."""
    if not ts_str:
        return None
    # Try ISO format first
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            dt = datetime.strptime(ts_str.strip(), fmt).replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except ValueError:
            continue
    # Try parsing as a float directly
    try:
        return float(ts_str)
    except (ValueError, TypeError):
        return None


def _extract_messages_from_request(request_json: Any) -> list[dict]:
    """Extract messages array from an OpenAI-format request JSON."""
    data = parse_json(request_json)
    if not data or not isinstance(data, dict):
        return []
    return data.get("messages", []) or []


def _extract_response_data(response_json: Any) -> dict:
    """Extract assistant message, usage, and model from response JSON."""
    data = parse_json(response_json)
    if not data or not isinstance(data, dict):
        return {}
    return data


def _get_assistant_message(response_data: dict) -> dict | None:
    """Get the assistant message from the response choices."""
    choices = response_data.get("choices", [])
    if not choices:
        return None
    return choices[0].get("message")


def _get_usage(response_data: dict) -> dict:
    """Get token usage from response."""
    return response_data.get("usage", {}) or {}


def _extract_tool_calls_from_message(msg: dict) -> list[dict] | None:
    """Extract tool_calls from an OpenAI-format message."""
    from .utils import extract_openai_tool_calls
    return extract_openai_tool_calls(msg)


def _build_conversation(completions: list[dict]) -> list[Message]:
    """Build a conversation message list from a session's chat_completions rows.

    Strategy: take the LAST request's messages (full history), then append
    the last response's assistant message.
    """
    if not completions:
        return []

    # Sort by start_time
    sorted_comps = sorted(completions, key=lambda c: c.get("start_time") or "")

    last_comp = sorted_comps[-1]
    request_msgs = _extract_messages_from_request(last_comp.get("request"))
    response_data = _extract_response_data(last_comp.get("response"))
    assistant_msg = _get_assistant_message(response_data)

    messages: list[Message] = []
    idx = 0

    for m in request_msgs:
        role = m.get("role", "unknown")
        if role == "system":
            continue
        content = m.get("content", "")
        tool_calls = _extract_tool_calls_from_message(m)

        messages.append(Message(
            index=idx,
            role=role,
            content=stringify_content(content),
            created_at=None,
            tool_calls=tool_calls,
            tool_name=m.get("name") if role == "tool" else None,
            tool_call_id=m.get("tool_call_id"),
        ))
        idx += 1

    # Append the final assistant response if not already in request messages
    if assistant_msg:
        content = assistant_msg.get("content", "") or ""
        tool_calls = _extract_tool_calls_from_message(assistant_msg)
        messages.append(Message(
            index=idx,
            role="assistant",
            content=stringify_content(content),
            created_at=_parse_ts(last_comp.get("end_time")),
            tool_calls=tool_calls,
        ))

    return messages


def _collect_tool_names(completions: list[dict]) -> list[str]:
    """Collect unique tool names from all response tool_calls in a session."""
    names: list[str] = []
    seen: set[str] = set()
    for comp in completions:
        response_data = _extract_response_data(comp.get("response"))
        assistant_msg = _get_assistant_message(response_data)
        if not assistant_msg:
            continue
        for tc in assistant_msg.get("tool_calls", []) or []:
            fn = tc.get("function", {})
            name = fn.get("name", "")
            if name and name not in seen:
                seen.add(name)
                names.append(name)
    return names


def _first_user_query(completions: list[dict]) -> str:
    """Get the first user message from the earliest completion's request."""
    if not completions:
        return ""
    sorted_comps = sorted(completions, key=lambda c: c.get("start_time") or "")
    request_msgs = _extract_messages_from_request(sorted_comps[0].get("request"))
    for m in request_msgs:
        if m.get("role") == "user":
            content = m.get("content", "")
            if isinstance(content, str):
                return content[:200]
    return ""


def _session_tokens(completions: list[dict]) -> tuple[int, int, int]:
    """Sum token usage across all completions. Returns (total, input, output)."""
    total = prompt = completion = 0
    for comp in completions:
        usage = _get_usage(_extract_response_data(comp.get("response")))
        total += usage.get("total_tokens", 0) or 0
        prompt += usage.get("prompt_tokens", 0) or 0
        completion += usage.get("completion_tokens", 0) or 0
    return total, prompt, completion


def _session_duration(completions: list[dict]) -> float | None:
    """Calculate session duration from first start_time to last end_time."""
    starts = [_parse_ts(c.get("start_time")) for c in completions]
    ends = [_parse_ts(c.get("end_time")) for c in completions]
    valid_starts = [s for s in starts if s is not None]
    valid_ends = [e for e in ends if e is not None]
    if not valid_starts or not valid_ends:
        return None
    return max(valid_ends) - min(valid_starts)


def _session_cost(completions: list[dict]) -> float:
    """Sum cost across all completions."""
    return sum(c.get("cost", 0) or 0 for c in completions)


class AutoGenSource(DataSource):
    """Read-only adapter for AutoGen's runtime_logging SQLite database."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = open_readonly_db(db_path)

    def _fetch_all_completions(self) -> list[dict]:
        """Fetch all rows from chat_completions as dicts."""
        rows = self._conn.execute(
            "SELECT * FROM chat_completions ORDER BY start_time"
        ).fetchall()
        return [dict(r) for r in rows]

    def _group_by_session(self, rows: list[dict]) -> dict[str, list[dict]]:
        """Group completion rows by session_id."""
        groups: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            sid = row.get("session_id") or "unknown"
            groups[sid].append(row)
        return groups

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
            conditions.append("start_time >= ?")
            params.append(datetime.fromtimestamp(date_from, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
        if date_to is not None:
            conditions.append("start_time <= ?")
            params.append(datetime.fromtimestamp(date_to, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
        if keyword:
            conditions.append("(request LIKE ? OR response LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Get all matching completions grouped by session
        rows = self._conn.execute(
            f"SELECT * FROM chat_completions {where} ORDER BY start_time",
            params,
        ).fetchall()
        rows = [dict(r) for r in rows]

        sessions = self._group_by_session(rows)

        # Build summaries
        summaries: list[SessionSummary] = []
        for session_id, comps in sessions.items():
            sorted_comps = sorted(comps, key=lambda c: c.get("start_time") or "")
            created_at = _parse_ts(sorted_comps[0].get("start_time")) or 0.0
            updated_at = _parse_ts(sorted_comps[-1].get("end_time"))
            total_tokens, input_tokens, output_tokens = _session_tokens(comps)
            duration = _session_duration(comps)

            # Get model from last response
            response_data = _extract_response_data(sorted_comps[-1].get("response"))
            model = response_data.get("model")

            # Count messages: build conversation to get accurate count
            conv = _build_conversation(comps)

            summaries.append(SessionSummary(
                session_id=session_id,
                created_at=created_at,
                updated_at=updated_at,
                first_query=_first_user_query(comps),
                message_count=len(conv),
                model=model,
                status="COMPLETED",
                total_tokens=total_tokens,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration=round(duration, 2) if duration is not None else None,
                ttft=None,  # AutoGen doesn't track TTFT
                tool_names=_collect_tool_names(comps),
                has_images=False,
            ))

        # Sort
        if sort == "created_at_asc":
            summaries.sort(key=lambda s: s.created_at)
        elif sort == "tokens_desc":
            summaries.sort(key=lambda s: s.total_tokens, reverse=True)
        elif sort == "tokens_asc":
            summaries.sort(key=lambda s: s.total_tokens)
        else:  # created_at_desc
            summaries.sort(key=lambda s: s.created_at, reverse=True)

        total = len(summaries)
        offset = (page - 1) * page_size
        page_items = summaries[offset : offset + page_size]

        return page_items, total

    def get_session(self, session_id: str) -> SessionDetail | None:
        rows = self._conn.execute(
            "SELECT * FROM chat_completions WHERE session_id = ? ORDER BY start_time",
            (session_id,),
        ).fetchall()
        if not rows:
            return None

        comps = [dict(r) for r in rows]
        sorted_comps = sorted(comps, key=lambda c: c.get("start_time") or "")
        created_at = _parse_ts(sorted_comps[0].get("start_time")) or 0.0

        total_tokens, input_tokens, output_tokens = _session_tokens(comps)
        duration = _session_duration(comps)
        cost = _session_cost(comps)

        response_data = _extract_response_data(sorted_comps[-1].get("response"))
        model = response_data.get("model")

        messages = _build_conversation(comps)

        # Collect all tools with results from response tool_calls
        tools: list[dict] = []
        for comp in sorted_comps:
            resp = _extract_response_data(comp.get("response"))
            assistant_msg = _get_assistant_message(resp)
            if not assistant_msg:
                continue
            for tc in assistant_msg.get("tool_calls", []) or []:
                fn = tc.get("function", {})
                tools.append({
                    "tool_call_id": tc.get("id"),
                    "tool_name": fn.get("name"),
                    "tool_args": fn.get("arguments"),
                    "result": None,  # AutoGen doesn't store tool results in chat_completions
                    "created_at": _parse_ts(comp.get("end_time")),
                })

        # Try to match tool results from request messages
        for comp in sorted_comps:
            req_msgs = _extract_messages_from_request(comp.get("request"))
            for m in req_msgs:
                if m.get("role") == "tool" and m.get("tool_call_id"):
                    for t in tools:
                        if t["tool_call_id"] == m["tool_call_id"] and t["result"] is None:
                            t["result"] = m.get("content")
                            break

        metrics = {
            "total_tokens": total_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "duration": round(duration, 2) if duration is not None else None,
            "cost": round(cost, 6) if cost else None,
        }

        return SessionDetail(
            session_id=session_id,
            created_at=created_at,
            model=model,
            metrics=metrics,
            messages=messages,
            tools=tools,
            files=[],
        )

    def get_daily_metrics(self, date_from: str, date_to: str) -> list[DailyMetrics]:
        ts_from, ts_to = date_range_to_ts(date_from, date_to)

        dt_from = datetime.fromtimestamp(ts_from, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        dt_to = datetime.fromtimestamp(ts_to, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        rows = self._conn.execute(
            """SELECT * FROM chat_completions
               WHERE start_time >= ? AND start_time < ?
               ORDER BY start_time""",
            (dt_from, dt_to),
        ).fetchall()
        rows = [dict(r) for r in rows]

        sessions = self._group_by_session(rows)

        # Group sessions by date (based on first completion's start_time)
        daily: dict[str, dict] = defaultdict(new_daily_bucket)

        for session_id, comps in sessions.items():
            sorted_comps = sorted(comps, key=lambda c: c.get("start_time") or "")
            created_ts = _parse_ts(sorted_comps[0].get("start_time"))
            if created_ts is None:
                continue

            date = ts_to_date(created_ts)
            d = daily[date]
            d["sessions"] += 1

            total, inp, out = _session_tokens(comps)
            d["total_tokens"] += total
            d["input_tokens"] += inp
            d["output_tokens"] += out

            duration = _session_duration(comps)
            if duration is not None:
                d["durations"].append(duration)

            conv = _build_conversation(comps)
            d["messages"] += len(conv)

        return build_daily_metrics(daily)

    def get_tool_stats(self, date_from: str, date_to: str) -> dict:
        ts_from, ts_to = date_range_to_ts(date_from, date_to)

        dt_from = datetime.fromtimestamp(ts_from, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        dt_to = datetime.fromtimestamp(ts_to, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        rows = self._conn.execute(
            """SELECT * FROM chat_completions
               WHERE start_time >= ? AND start_time < ?
               ORDER BY start_time""",
            (dt_from, dt_to),
        ).fetchall()
        rows = [dict(r) for r in rows]

        summary: dict[str, int] = defaultdict(int)
        daily_tools: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for row in rows:
            created_ts = _parse_ts(row.get("start_time"))
            if created_ts is None:
                continue
            date = ts_to_date(created_ts)

            response_data = _extract_response_data(row.get("response"))
            assistant_msg = _get_assistant_message(response_data)
            if not assistant_msg:
                continue
            for tc in assistant_msg.get("tool_calls", []) or []:
                fn = tc.get("function", {})
                name = fn.get("name", "unknown")
                summary[name] += 1
                daily_tools[date][name] += 1

        return build_tool_stats_result(summary, daily_tools)


# Register this source adapter
from . import register_source  # noqa: E402

register_source("autogen", AutoGenSource)
