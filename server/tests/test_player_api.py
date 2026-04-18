"""
Tests for players API router — integration tests with FastAPI TestClient.

Uses mocked service layer for isolated endpoint testing.
"""

import os
import shutil
import sqlite3
import tempfile
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from server.app import app
from server.pipeline.db.queries import insert_game_logs, upsert_player, upsert_team
from server.pipeline.db.schema import init_db
from server.services import player_service


@pytest.fixture
def test_db():
    """Provide a temp SQLite DB with test data - 20+ games for hit rates."""
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "test.db")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    init_db(conn)

    lakers_id = 1610612747
    nuggets_id = 1610612743
    lebron_id = 2544
    jokic_id = 203999

    upsert_team(conn, lakers_id, "LAL", "Los Angeles Lakers")
    upsert_team(conn, nuggets_id, "DEN", "Denver Nuggets")
    upsert_player(conn, lebron_id, "LeBron James", True, "F", lakers_id)
    upsert_player(conn, jokic_id, "Nikola Jokic", True, "C", nuggets_id)

    # LeBron game logs - 20+ non-DNP games for hitrate computation
    game_logs = []
    for i in range(25):
        day = (24 + i) % 28 + 1
        month = 10 if i < 5 else 11 if i < 15 else 12
        game_date = f"2023-{month:02d}-{day:02d}"
        pts = 30 - (i % 10) + 5
        is_dnp = 1 if i == 12 else 0  # One DNP game

        game_logs.append({
            "player_id": lebron_id,
            "game_id": f"0022301{i+1:03d}",
            "season": "2023-24",
            "game_date": game_date,
            "matchup": "LAL @ DEN" if i % 2 == 0 else "LAL vs. PHX",
            "wl": "W" if i % 3 != 2 else "L",
            "min": 0 if is_dnp else 35 - (i % 5),
            "pts": 0 if is_dnp else pts,
            "reb": 0 if is_dnp else 8 - (i % 5),
            "ast": 0 if is_dnp else 9 - (i % 6),
            "stl": 0 if is_dnp else 1 + (i % 2),
            "blk": 0 if is_dnp else 1,
            "fg3m": 0 if is_dnp else 2 + (i % 3),
            "fgm": 0 if is_dnp else 10 + (i % 6),
            "fga": 0 if is_dnp else 20 + (i % 8),
            "ftm": 0 if is_dnp else 5 + (i % 3),
            "fta": 0 if is_dnp else 7 + (i % 4),
            "oreb": 0 if is_dnp else 1,
            "dreb": 0 if is_dnp else 7 - (i % 4),
            "tov": 0 if is_dnp else 3 + (i % 2),
            "pf": 0 if is_dnp else 2,
            "plus_minus": 0 if is_dnp else 5 - (i % 10),
            "is_dnp": is_dnp,
        })

    insert_game_logs(conn, pd.DataFrame(game_logs))
    conn.commit()
    conn.close()

    yield db_path
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture
def client(test_db, monkeypatch):
    """Provide FastAPI TestClient with patched DB."""
    monkeypatch.setattr(player_service, "DB_PATH", test_db)
    # Ensure model_artifact is set on app state
    app.state.model_artifact = None
    return TestClient(app)


class TestListPlayers:
    """GET /api/players"""

    def test_list_players_returns_active(self, client):
        """Returns list of active players."""
        response = client.get("/api/players")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_list_players_search(self, client):
        """Search case-insensitive on full_name."""
        response = client.get("/api/players?search=LeBron")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any("LeBron" in p["full_name"] for p in data)

    def test_list_players_search_no_results(self, client):
        """Search with no matches returns empty list."""
        response = client.get("/api/players?search=XYZNOTFOUND")
        assert response.status_code == 200
        assert response.json() == []


class TestGetPlayer:
    """GET /api/players/{player_id}"""

    def test_get_player_returns_with_lines(self, client):
        """Single player with default_lines."""
        response = client.get("/api/players/2544")
        assert response.status_code == 200
        data = response.json()
        assert data["player_id"] == 2544
        assert data["full_name"] == "LeBron James"
        assert "default_lines" in data

    def test_get_player_404(self, client):
        """Unknown player returns 404 per D-12."""
        response = client.get("/api/players/99999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Player not found"


class TestGetPlayerProps:
    """GET /api/players/{player_id}/props"""

    def test_get_props_returns_structure(self, client):
        """Props endpoint returns player_id, default_lines, top_props."""
        response = client.get("/api/players/2544/props")
        assert response.status_code == 200
        data = response.json()
        assert data["player_id"] == 2544
        assert "default_lines" in data
        assert "top_props" in data

    def test_get_props_no_artifact_returns_200(self, client):
        """Model not loaded returns 200 with empty top_props per D-10."""
        app.state.model_artifact = None
        response = client.get("/api/players/2544/props")
        assert response.status_code == 200
        data = response.json()
        assert data["top_props"] == []

    def test_get_props_unknown_player_returns_empty(self, client):
        """Unknown player returns 200 with empty props (graceful degradation)."""
        response = client.get("/api/players/99999/props")
        assert response.status_code == 200
        data = response.json()
        assert data["player_id"] == 99999
        assert data["default_lines"] == {}
        assert data["top_props"] == []


class TestGetPlayerGamelogs:
    """GET /api/players/{player_id}/gamelogs"""

    def test_get_gamelogs_returns_list(self, client):
        """Returns list of game log dicts."""
        response = client.get("/api/players/2544/gamelogs")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 25  # All 25 games (including DNP)

    def test_get_gamelogs_with_limit(self, client):
        """Limit param controls number of results."""
        response = client.get("/api/players/2544/gamelogs?limit=5")
        assert response.status_code == 200
        assert len(response.json()) == 5

    def test_get_gamelogs_unknown_player_returns_empty(self, client):
        """Unknown player returns empty list (service doesn't raise)."""
        response = client.get("/api/players/99999/gamelogs")
        assert response.status_code == 200
        assert response.json() == []


class TestGetPlayerHitrates:
    """GET /api/players/{player_id}/hitrates"""

    def test_get_hitrates_requires_stat(self, client):
        """Stat query param required."""
        response = client.get("/api/players/2544/hitrates")
        assert response.status_code == 422  # Validation error

    def test_get_hitrates_returns_structure(self, client):
        """Returns player_id, stat, line, hit_rates."""
        response = client.get("/api/players/2544/hitrates?stat=pts")
        assert response.status_code == 200
        data = response.json()
        assert data["player_id"] == 2544
        assert data["stat"] == "pts"
        assert "line" in data
        assert "hit_rates" in data


class TestGetPlayerLines:
    """GET /api/players/{player_id}/lines"""

    def test_get_lines_returns_structure(self, client):
        """Returns player_id and lines dict."""
        response = client.get("/api/players/2544/lines")
        assert response.status_code == 200
        data = response.json()
        assert data["player_id"] == 2544
        assert "lines" in data

    def test_get_lines_404_unknown_player(self, client):
        """Unknown player returns 404."""
        response = client.get("/api/players/99999/lines")
        assert response.status_code == 404
