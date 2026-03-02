"""Test auto-detection of source types."""
from pathlib import Path

from tinylog.sources.detect import detect_source_type

FIXTURES = Path(__file__).parent / "fixtures"


def test_detect_agno():
    assert detect_source_type(str(FIXTURES / "agno_sessions.db")) == "agno"


def test_detect_langchain():
    assert detect_source_type(str(FIXTURES / "langchain.db")) == "langchain"


def test_detect_autogen():
    assert detect_source_type(str(FIXTURES / "autogen.db")) == "autogen"


def test_detect_adk():
    assert detect_source_type(str(FIXTURES / "adk.db")) == "adk"


def test_detect_claude_sdk():
    assert detect_source_type(str(FIXTURES / "claude-sdk")) == "claude-agent-sdk"


def test_detect_json_import():
    assert detect_source_type(str(FIXTURES / "json-import")) == "json-import"
