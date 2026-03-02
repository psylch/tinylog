"""Basic tests for all source adapters."""
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


class TestAgnoSource:
    def test_list_and_get(self):
        from tinylog.sources.agno import AgnoSource
        source = AgnoSource(str(FIXTURES / "agno_sessions.db"))
        items, total = source.list_sessions()
        assert total == 2
        detail = source.get_session(items[0].session_id)
        assert detail is not None
        assert len(detail.messages) > 0


class TestLangChainSource:
    def test_list_and_get(self):
        from tinylog.sources.langchain import LangChainSource
        source = LangChainSource(str(FIXTURES / "langchain.db"))
        items, total = source.list_sessions()
        assert total >= 1
        detail = source.get_session(items[0].session_id)
        assert detail is not None


class TestAutoGenSource:
    def test_list_and_get(self):
        from tinylog.sources.autogen import AutoGenSource
        source = AutoGenSource(str(FIXTURES / "autogen.db"))
        items, total = source.list_sessions()
        assert total >= 1
        detail = source.get_session(items[0].session_id)
        assert detail is not None


class TestADKSource:
    def test_list_and_get(self):
        from tinylog.sources.adk import ADKSource
        source = ADKSource(str(FIXTURES / "adk.db"))
        items, total = source.list_sessions()
        assert total >= 1
        detail = source.get_session(items[0].session_id)
        assert detail is not None


class TestClaudeSDKSource:
    def test_list_and_get(self):
        from tinylog.sources.claude_sdk import ClaudeSDKSource
        source = ClaudeSDKSource(str(FIXTURES / "claude-sdk"))
        items, total = source.list_sessions()
        assert total >= 1
        detail = source.get_session(items[0].session_id)
        assert detail is not None


class TestJSONImportSource:
    def test_list_and_get(self):
        from tinylog.sources.json_import import JSONImportSource
        source = JSONImportSource(str(FIXTURES / "json-import"))
        items, total = source.list_sessions()
        assert total >= 1
        detail = source.get_session(items[0].session_id)
        assert detail is not None
