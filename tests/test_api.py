"""Tests for API endpoints using httpx TestClient."""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from tinylog.config import Config
from tinylog.app import create_app

DB_PATH = "/Users/lichihao/Workspaces/projectWorkspace/huihifi_ai/ai-tuning/aituning-be/agno_sessions.db"


@pytest.fixture
def client():
    if not os.path.exists(DB_PATH):
        pytest.skip("agno_sessions.db not found")
    with tempfile.TemporaryDirectory() as tmpdir:
        config = Config(db_path=DB_PATH, data_dir=tmpdir)
        app = create_app(config)
        yield TestClient(app)


class TestHealth:
    def test_health_check(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestConfig:
    def test_frontend_config(self, client):
        r = client.get("/api/config")
        assert r.status_code == 200
        data = r.json()
        assert "theme" in data
        assert "title" in data


class TestSessions:
    def test_list_sessions(self, client):
        r = client.get("/api/sessions")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 113
        assert len(data["items"]) <= 20
        item = data["items"][0]
        assert "session_id" in item
        assert "first_query" in item
        assert "total_tokens" in item

    def test_list_sessions_pagination(self, client):
        r = client.get("/api/sessions?page=1&page_size=5")
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) == 5
        assert data["page"] == 1

    def test_get_session_detail(self, client):
        # Get first session ID
        r = client.get("/api/sessions?page_size=1")
        sid = r.json()["items"][0]["session_id"]

        r = client.get(f"/api/sessions/{sid}")
        assert r.status_code == 200
        data = r.json()
        assert data["session_id"] == sid
        assert "messages" in data
        assert len(data["messages"]) > 0

    def test_get_session_not_found(self, client):
        r = client.get("/api/sessions/nonexistent_xyz")
        assert r.status_code == 404


class TestStatistics:
    def test_overview(self, client):
        r = client.get("/api/statistics/overview?period=all")
        assert r.status_code == 200
        data = r.json()
        assert "current" in data
        assert "trends" in data
        assert data["current"]["sessions"] > 0

    def test_daily(self, client):
        r = client.get("/api/statistics/daily?date_from=2025-01-01&date_to=2026-12-31")
        assert r.status_code == 200
        data = r.json()
        assert len(data["data"]) > 0

    def test_tools(self, client):
        r = client.get("/api/statistics/tools?date_from=2025-01-01&date_to=2026-12-31")
        assert r.status_code == 200
        data = r.json()
        assert "summary" in data


class TestAuth:
    def test_auth_required(self):
        if not os.path.exists(DB_PATH):
            pytest.skip("agno_sessions.db not found")
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config(db_path=DB_PATH, data_dir=tmpdir, admin_key="test-secret")
            app = create_app(config)
            c = TestClient(app)

            # Without key
            r = c.get("/api/sessions")
            assert r.status_code == 401

            # With key
            r = c.get("/api/sessions", headers={"X-Admin-Key": "test-secret"})
            assert r.status_code == 200

            # Health should work without key
            r = c.get("/api/health")
            assert r.status_code == 200

            # Config should work without key
            r = c.get("/api/config")
            assert r.status_code == 200


class TestFiles:
    def test_list_files_empty(self, client):
        r = client.get("/api/files")
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_upload_and_get_file(self, client):
        r = client.post(
            "/api/files",
            files={"file": ("test.txt", b"hello world", "text/plain")},
        )
        assert r.status_code == 200
        data = r.json()
        file_id = data["id"]
        assert data["filename"] == "test.txt"

        # Retrieve
        r = client.get(f"/api/files/{file_id}")
        assert r.status_code == 200
        assert r.content == b"hello world"

        # List should have 1
        r = client.get("/api/files")
        assert r.json()["total"] == 1
