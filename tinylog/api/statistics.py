"""Statistics API routes."""

from __future__ import annotations

import logging
import re
from dataclasses import asdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, Request

logger = logging.getLogger("tinylog")

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

router = APIRouter(prefix="/api/statistics", tags=["statistics"])


def _period_range(period: str) -> tuple[str, str, str, str]:
    """Return (current_from, current_to, prev_from, prev_to) as date strings."""
    now = datetime.now(tz=timezone.utc)
    today = now.strftime("%Y-%m-%d")

    if period == "today":
        current_from = today
        current_to = today
        yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        prev_from = yesterday
        prev_to = yesterday
    elif period == "7d":
        current_from = (now - timedelta(days=6)).strftime("%Y-%m-%d")
        current_to = today
        prev_from = (now - timedelta(days=13)).strftime("%Y-%m-%d")
        prev_to = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    elif period == "30d":
        current_from = (now - timedelta(days=29)).strftime("%Y-%m-%d")
        current_to = today
        prev_from = (now - timedelta(days=59)).strftime("%Y-%m-%d")
        prev_to = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    else:  # "all"
        current_from = "2020-01-01"
        current_to = today
        prev_from = "2019-01-01"
        prev_to = "2019-12-31"

    return current_from, current_to, prev_from, prev_to


def _calc_trend(current: float | int, previous: float | int) -> float | None:
    if previous == 0:
        return None
    return round((current - previous) / previous * 100, 1)


@router.get("/overview")
async def overview(
    request: Request,
    period: str = Query("7d"),
):
    try:
        source = request.app.state.source
        cur_from, cur_to, prev_from, prev_to = _period_range(period)

        cur_daily = source.get_daily_metrics(cur_from, cur_to)
        prev_daily = source.get_daily_metrics(prev_from, prev_to)

        def _sum_metrics(daily_list):
            sessions = sum(d.sessions for d in daily_list)
            messages = sum(d.messages for d in daily_list)
            total_tokens = sum(d.total_tokens for d in daily_list)
            input_tokens = sum(d.input_tokens for d in daily_list)
            output_tokens = sum(d.output_tokens for d in daily_list)
            durations = [d.avg_duration for d in daily_list if d.avg_duration is not None]
            ttfts = [d.avg_ttft for d in daily_list if d.avg_ttft is not None]
            avg_duration = round(sum(durations) / len(durations), 2) if durations else None
            avg_ttft = round(sum(ttfts) / len(ttfts), 3) if ttfts else None
            return {
                "sessions": sessions,
                "messages": messages,
                "total_tokens": total_tokens,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "avg_duration": avg_duration,
                "avg_ttft": avg_ttft,
            }

        current = _sum_metrics(cur_daily)
        previous = _sum_metrics(prev_daily)

        trends = {}
        for key in ["sessions", "messages", "total_tokens"]:
            trends[key] = _calc_trend(current[key], previous[key])
        if current["avg_ttft"] is not None and previous.get("avg_ttft") is not None:
            trends["avg_ttft"] = _calc_trend(current["avg_ttft"], previous["avg_ttft"])

        # Tool stats for the current period
        tool_stats = source.get_tool_stats(cur_from, cur_to)

        return {
            "period": period,
            "current": current,
            "previous": previous,
            "trends": trends,
            "tool_calls": {
                "total": sum(tool_stats["summary"].values()),
                "by_tool": tool_stats["summary"],
            },
        }
    except Exception as e:
        logger.exception("Failed to get overview")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily")
async def daily(
    request: Request,
    date_from: str = Query(...),
    date_to: str = Query(...),
):
    if not DATE_RE.match(date_from):
        raise HTTPException(status_code=400, detail="Invalid date_from format, expected YYYY-MM-DD")
    if not DATE_RE.match(date_to):
        raise HTTPException(status_code=400, detail="Invalid date_to format, expected YYYY-MM-DD")
    try:
        source = request.app.state.source
        metrics = source.get_daily_metrics(date_from, date_to)
        return {"data": [asdict(m) for m in metrics]}
    except Exception as e:
        logger.exception("Failed to get daily metrics")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools")
async def tools(
    request: Request,
    date_from: str = Query(...),
    date_to: str = Query(...),
):
    if not DATE_RE.match(date_from):
        raise HTTPException(status_code=400, detail="Invalid date_from format, expected YYYY-MM-DD")
    if not DATE_RE.match(date_to):
        raise HTTPException(status_code=400, detail="Invalid date_to format, expected YYYY-MM-DD")
    try:
        source = request.app.state.source
        return source.get_tool_stats(date_from, date_to)
    except Exception as e:
        logger.exception("Failed to get tool stats")
        raise HTTPException(status_code=500, detail=str(e))
