import subprocess
import sys
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def pytest_configure(config):
    """Auto-generate fixtures if missing."""
    if not (FIXTURES_DIR / "agno_sessions.db").exists():
        subprocess.run(
            [sys.executable, str(Path(__file__).parent / "create_fixtures.py")],
            check=True,
        )
