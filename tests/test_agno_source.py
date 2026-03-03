"""Tests for AgnoSource against fixture data."""
from pathlib import Path

import pytest

from tinylog.sources.agno import AgnoSource

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def source():
    return AgnoSource(str(FIXTURES / "agno_sessions.db"))


class TestListSessions:
    def test_returns_items_and_total(self, source):
        items, total = source.list_sessions(page=1, page_size=10)
        assert total == 2
        assert len(items) <= 10
        assert len(items) > 0

    def test_session_summary_fields(self, source):
        items, _ = source.list_sessions(page=1, page_size=1)
        s = items[0]
        assert s.session_id
        assert isinstance(s.created_at, (int, float))
        assert isinstance(s.first_query, str)
        assert isinstance(s.message_count, int)
        assert s.message_count > 0
        assert isinstance(s.total_tokens, int)

    def test_pagination(self, source):
        items1, total = source.list_sessions(page=1, page_size=1)
        items2, _ = source.list_sessions(page=2, page_size=1)
        assert len(items1) == 1
        assert len(items2) == 1
        assert items1[0].session_id != items2[0].session_id

    def test_sort_created_at_desc(self, source):
        items, _ = source.list_sessions(page=1, page_size=5, sort="created_at_desc")
        for i in range(len(items) - 1):
            assert items[i].created_at >= items[i + 1].created_at

    def test_keyword_search(self, source):
        items, total = source.list_sessions(keyword="session 1")
        assert total == 1
        assert items[0].session_id == "test-session-1"


class TestGetSession:
    def test_returns_session_detail(self, source):
        items, _ = source.list_sessions(page=1, page_size=1)
        sid = items[0].session_id
        detail = source.get_session(sid)
        assert detail is not None
        assert detail.session_id == sid
        assert len(detail.messages) > 0

    def test_filters_system_messages(self, source):
        items, _ = source.list_sessions(page=1, page_size=1)
        detail = source.get_session(items[0].session_id)
        for msg in detail.messages:
            assert msg.role != "system"

    def test_nonexistent_session(self, source):
        detail = source.get_session("nonexistent_session_id_xyz")
        assert detail is None


class TestDailyMetrics:
    def test_returns_daily_data(self, source):
        metrics = source.get_daily_metrics("2020-01-01", "2030-12-31")
        assert len(metrics) > 0
        m = metrics[0]
        assert m.date
        assert isinstance(m.sessions, int)
        assert m.sessions > 0


class TestToolStats:
    def test_returns_tool_distribution(self, source):
        stats = source.get_tool_stats("2020-01-01", "2030-12-31")
        assert "summary" in stats
        assert "daily" in stats
        assert isinstance(stats["summary"], dict)
