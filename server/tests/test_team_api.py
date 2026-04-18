"""
Tests for teams API router — integration tests with FastAPI TestClient.
"""

import os
import shutil
import sqlite3
import tempfile

import pytest
from fastapi.testclient import TestClient

from server.app import app
from server.pipeline.db.queries import upsert_team
from server.pipeline.db.schema import init_db
from server.services import team_service


@pytest.fixture
def team_test_db():
    """Provide a temp SQLite DB with team data."""
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "test.db")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    init_db(conn)

    upsert_team(conn, 1610612747, "LAL", "Los Angeles Lakers")
    upsert_team(conn, 1610612743, "DEN", "Denver Nuggets")
    conn.commit()
    conn.close()

    yield db_path
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture
def team_client(team_test_db, monkeypatch):
    """Provide FastAPI TestClient with patched DB."""
    monkeypatch.setattr(team_service, "DB_PATH", team_test_db)
    return TestClient(app)


class TestListTeams:
    """GET /api/teams"""

    def test_list_teams_returns_all(self, team_client):
        """Returns list of all teams."""
        response = team_client.get("/api/teams")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2


class TestGetTeam:
    """GET /api/teams/{team_id}"""

    def test_get_team_returns_detail(self, team_client):
        """Returns single team with team_id, abbreviation, full_name."""
        response = team_client.get("/api/teams/1610612747")
        assert response.status_code == 200
        data = response.json()
        assert data["team_id"] == 1610612747
        assert data["abbreviation"] == "LAL"
        assert data["full_name"] == "Los Angeles Lakers"

    def test_get_team_404(self, team_client):
        """Unknown team returns 404."""
        response = team_client.get("/api/teams/99999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Team not found"
