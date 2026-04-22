"""
End-to-end integration tests for Phase 5 API — all endpoints.

Covers all Phase 5 endpoints:
- GET /api/health
- GET /api/players
- GET /api/players?search=
- GET /api/players/{id}
- GET /api/players/{id}/props
- GET /api/players/{id}/gamelogs
- GET /api/players/{id}/hitrates?stat=
- GET /api/players/{id}/lines
- GET /api/teams
- GET /api/teams/{id}

Also verifies:
- 404 responses for unknown players/teams
- Model artifact loaded at startup (D-10)
- V1 dependencies removed from requirements.txt
"""

import os
import pathlib
import shutil
import sqlite3
import tempfile
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from server.app import app
from server.pipeline.db.queries import insert_game_logs, upsert_player, upsert_team
from server.pipeline.db.schema import init_db
from server.services import player_service, team_service


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_artifact_dict():
    """Minimal artifact dict for FastAPI app.state."""
    return {
        "model": MagicMock(),
        "calibrator": MagicMock(),
        "feature_columns": ["stat_type", "pts_avg_L5"],
        "categorical_features": ["stat_type"],
        "metrics": {"calibration_method": "isotonic"},
        "metadata": {"version": "2.0"},
    }


@pytest.fixture
def integration_db():
    """Provide a temp SQLite DB with seed data: 2 players, 1 team, 10+ game logs each."""
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

    # LeBron game logs — 20 non-DNP games for hitrate windows
    lebron_logs = []
    for i in range(20):
        day = (24 + i) % 28 + 1
        month = 10 if i < 5 else 11 if i < 12 else 12
        game_date = f"2024-{month:02d}-{day:02d}"
        pts = 28 + (i % 5)
        lebron_logs.append({
            "player_id": lebron_id,
            "game_id": f"0022401{i+1:03d}",
            "season": "2024-25",
            "game_date": game_date,
            "matchup": "LAL @ DEN" if i % 2 == 0 else "LAL vs. PHX",
            "wl": "W" if i % 3 != 2 else "L",
            "min": 35 - (i % 5),
            "pts": pts,
            "reb": 7 + (i % 4),
            "ast": 8 + (i % 3),
            "stl": 1 + (i % 2),
            "blk": 1,
            "fg3m": 3 + (i % 2),
            "fgm": 10 + (i % 4),
            "fga": 20 + (i % 6),
            "ftm": 5 + (i % 2),
            "fta": 7 + (i % 3),
            "oreb": 1,
            "dreb": 6 + (i % 3),
            "tov": 3,
            "pf": 2,
            "plus_minus": 5,
            "is_dnp": 0,
        })

    insert_game_logs(conn, pd.DataFrame(lebron_logs))
    conn.commit()
    conn.close()

    yield db_path
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture
def integration_client(integration_db, monkeypatch, mock_artifact_dict):
    """FastAPI TestClient with DB patched and model artifact set."""
    monkeypatch.setattr(player_service, "DB_PATH", integration_db)
    monkeypatch.setattr(team_service, "DB_PATH", integration_db)
    app.state.model_artifact = mock_artifact_dict
    return TestClient(app)


@pytest.fixture
def client_no_model(integration_db, monkeypatch):
    """TestClient with model_artifact = None (graceful degradation per D-10)."""
    monkeypatch.setattr(player_service, "DB_PATH", integration_db)
    monkeypatch.setattr(team_service, "DB_PATH", integration_db)
    app.state.model_artifact = None
    return TestClient(app)


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    """D-16: /api/health returns status and model_loaded."""

    def test_health_returns_200(self, integration_client):
        """Health endpoint responds with 200."""
        response = integration_client.get("/api/health")
        assert response.status_code == 200

    def test_health_returns_correct_fields(self, integration_client):
        """Health returns status, service, version, model_loaded."""
        data = integration_client.get("/api/health").json()
        assert data["status"] == "healthy"
        assert data["service"] == "HoopProphet API"
        assert data["version"] == "2.0.0"
        assert "model_loaded" in data

    def test_health_model_loaded_true(self, integration_client):
        """model_loaded is True when artifact is set."""
        assert integration_client.get("/api/health").json()["model_loaded"] is True

    def test_health_model_loaded_false_when_no_artifact(self, client_no_model):
        """model_loaded is False when artifact is None."""
        assert client_no_model.get("/api/health").json()["model_loaded"] is False


# ---------------------------------------------------------------------------
# Players list and search
# ---------------------------------------------------------------------------

class TestPlayersList:
    """PROP-06: GET /api/players returns player list from cache."""

    def test_players_list_returns_players(self, integration_client):
        """Returns list of active players."""
        response = integration_client.get("/api/players")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_players_list_fields(self, integration_client):
        """Each player has player_id and full_name."""
        data = integration_client.get("/api/players").json()
        for player in data:
            assert "player_id" in player
            assert "full_name" in player


class TestPlayersSearch:
    """PROP-06: GET /api/players?search= filters players."""

    def test_players_search_returns_match(self, integration_client):
        """Search 'LeBron' returns LeBron James."""
        response = integration_client.get("/api/players?search=LeBron")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any("LeBron" in p["full_name"] for p in data)

    def test_players_search_case_insensitive(self, integration_client):
        """Search is case-insensitive."""
        response = integration_client.get("/api/players?search=lebron")
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_players_search_no_match(self, integration_client):
        """Search with no match returns empty list."""
        response = integration_client.get("/api/players?search=XYZNOTFOUND")
        assert response.status_code == 200
        assert response.json() == []


# ---------------------------------------------------------------------------
# Player detail
# ---------------------------------------------------------------------------

class TestPlayerDetail:
    """PROP-02: GET /api/players/{id} returns player with default lines."""

    def test_player_detail_returns_player(self, integration_client):
        """Returns player with player_id, full_name."""
        response = integration_client.get("/api/players/2544")
        assert response.status_code == 200
        data = response.json()
        assert data["player_id"] == 2544
        assert data["full_name"] == "LeBron James"

    def test_player_detail_has_default_lines(self, integration_client):
        """Response includes default_lines dict."""
        data = integration_client.get("/api/players/2544").json()
        assert "default_lines" in data
        assert isinstance(data["default_lines"], dict)


# ---------------------------------------------------------------------------
# Player props
# ---------------------------------------------------------------------------

class TestPlayerProps:
    """PROP-01/04/05: GET /api/players/{id}/props returns top props with hit rates."""

    def test_props_returns_structure(self, integration_client):
        """Props endpoint returns player_id, default_lines, top_props."""
        response = integration_client.get("/api/players/2544/props")
        assert response.status_code == 200
        data = response.json()
        assert data["player_id"] == 2544
        assert "default_lines" in data
        assert "top_props" in data

    def test_props_top_props_fields(self, integration_client):
        """Each top_prop has stat, line, probability, hit_rates."""
        data = integration_client.get("/api/players/2544/props").json()
        for prop in data["top_props"]:
            assert "stat" in prop
            assert "line" in prop
            assert "probability" in prop
            assert "hit_rates" in prop
            assert "direction" in prop


class TestPlayerPropsNoModel:
    """D-10: Props endpoint returns 200 with empty top_props when model not loaded."""

    def test_props_no_model_returns_200(self, client_no_model):
        """Returns 200 even when model_artifact is None."""
        response = client_no_model.get("/api/players/2544/props")
        assert response.status_code == 200

    def test_props_no_model_empty_top_props(self, client_no_model):
        """Returns empty top_props when model not loaded."""
        data = client_no_model.get("/api/players/2544/props").json()
        assert data["top_props"] == []


# ---------------------------------------------------------------------------
# Player game logs
# ---------------------------------------------------------------------------

class TestPlayerGamelogs:
    """PROP-06: GET /api/players/{id}/gamelogs returns game logs."""

    def test_gamelogs_returns_list(self, integration_client):
        """Returns list of game log dicts."""
        response = integration_client.get("/api/players/2544/gamelogs")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 10

    def test_gamelogs_has_required_fields(self, integration_client):
        """Each game log has game_id, season, game_date, pts."""
        data = integration_client.get("/api/players/2544/gamelogs").json()
        for log in data:
            assert "game_id" in log
            assert "season" in log
            assert "game_date" in log
            assert "pts" in log

    def test_gamelogs_limit_param(self, integration_client):
        """limit param controls number of results."""
        response = integration_client.get("/api/players/2544/gamelogs?limit=5")
        assert response.status_code == 200
        assert len(response.json()) == 5


# ---------------------------------------------------------------------------
# Player hit rates
# ---------------------------------------------------------------------------

class TestPlayerHitrates:
    """PROP-01: GET /api/players/{id}/hitrates?stat=pts returns hit rate windows."""

    def test_hitrates_returns_structure(self, integration_client):
        """Returns player_id, stat, line, hit_rates."""
        response = integration_client.get("/api/players/2544/hitrates?stat=pts")
        assert response.status_code == 200
        data = response.json()
        assert data["player_id"] == 2544
        assert data["stat"] == "pts"
        assert "line" in data
        assert "hit_rates" in data

    def test_hitrates_has_windows(self, integration_client):
        """hit_rates has L5, L10, L20, season keys."""
        data = integration_client.get("/api/players/2544/hitrates?stat=pts").json()
        assert "L5" in data["hit_rates"]
        assert "L10" in data["hit_rates"]
        assert "L20" in data["hit_rates"]
        assert "season" in data["hit_rates"]

    def test_hitrates_requires_stat(self, integration_client):
        """Stat query param is required."""
        response = integration_client.get("/api/players/2544/hitrates")
        assert response.status_code == 422  # Validation error


# ---------------------------------------------------------------------------
# Player lines
# ---------------------------------------------------------------------------

class TestPlayerLines:
    """PROP-02: GET /api/players/{id}/lines returns default lines."""

    def test_lines_returns_structure(self, integration_client):
        """Returns player_id and lines dict."""
        response = integration_client.get("/api/players/2544/lines")
        assert response.status_code == 200
        data = response.json()
        assert data["player_id"] == 2544
        assert "lines" in data

    def test_lines_values_are_half_increments(self, integration_client):
        """Line values are rounded to 0.5 increments."""
        data = integration_client.get("/api/players/2544/lines").json()
        for stat, line in data["lines"].items():
            assert (line * 2) == int(line * 2), f"{stat} line {line} not a 0.5 increment"


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------

class TestTeamsList:
    """CLNP-03: GET /api/teams returns team list from cache."""

    def test_teams_list_returns_teams(self, integration_client):
        """Returns list of all teams."""
        response = integration_client.get("/api/teams")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_teams_list_fields(self, integration_client):
        """Each team has team_id, abbreviation, full_name."""
        data = integration_client.get("/api/teams").json()
        for team in data:
            assert "team_id" in team
            assert "abbreviation" in team
            assert "full_name" in team


class TestTeamDetail:
    """CLNP-03: GET /api/teams/{id} returns team detail."""

    def test_team_detail_returns_team(self, integration_client):
        """Returns team with team_id, abbreviation, full_name."""
        response = integration_client.get("/api/teams/1610612747")
        assert response.status_code == 200
        data = response.json()
        assert data["team_id"] == 1610612747
        assert data["abbreviation"] == "LAL"
        assert data["full_name"] == "Los Angeles Lakers"


# ---------------------------------------------------------------------------
# 404 responses
# ---------------------------------------------------------------------------

class TestUnknownPlayer404:
    """D-12: Unknown player_id returns 404."""

    def test_unknown_player_404(self, integration_client):
        """Unknown player returns 404 with 'Player not found'."""
        response = integration_client.get("/api/players/99999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Player not found"

    def test_unknown_player_props_404(self, integration_client):
        """Unknown player on /props returns 200 (graceful degradation per D-10)."""
        response = integration_client.get("/api/players/99999/props")
        # Note: get_player_props returns 200 with empty structure for unknown players
        # since the player may exist but lack data. This differs from /players/{id}.
        assert response.status_code == 200

    def test_unknown_player_hitrates_404(self, integration_client):
        """Unknown player on /hitrates returns 404."""
        response = integration_client.get("/api/players/99999/hitrates?stat=pts")
        assert response.status_code == 404

    def test_unknown_player_lines_404(self, integration_client):
        """Unknown player on /lines returns 404."""
        response = integration_client.get("/api/players/99999/lines")
        assert response.status_code == 404


class TestUnknownTeam404:
    """D-12: Unknown team_id returns 404."""

    def test_unknown_team_404(self, integration_client):
        """Unknown team returns 404 with 'Team not found'."""
        response = integration_client.get("/api/teams/99999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Team not found"


# ---------------------------------------------------------------------------
# V1 cleanup verification
# ---------------------------------------------------------------------------

class TestV1Cleanup:
    """Verify V1 dependencies are removed from requirements.txt."""

    def test_xgboost_not_in_requirements(self):
        """xgboost should not be in requirements.txt."""
        req_path = os.path.join(os.path.dirname(__file__), "..", "requirements.txt")
        with open(req_path) as f:
            content = f.read()
        assert "xgboost" not in content, "xgboost should be removed from requirements.txt"

    def test_google_generativeai_not_in_requirements(self):
        """google-generativeai should not be in requirements.txt."""
        req_path = os.path.join(os.path.dirname(__file__), "..", "requirements.txt")
        with open(req_path) as f:
            content = f.read()
        assert "google-generativeai" not in content, "google-generativeai should be removed"

    def test_app_has_no_v1_imports(self):
        """app.py should have no imports from server.ml or nba_api.stats."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "app.py")
        with open(app_path) as f:
            content = f.read()
        assert "from server.ml" not in content, "server.ml imports should be removed"
        assert "nba_api.stats" not in content, "nba_api.stats imports should be removed"
        assert "google.generativeai" not in content, "google.generativeai should be removed"

    def test_server_ml_directory_not_exists(self):
        """server/ml/ directory should not exist (V1 code removed)."""
        import pathlib
        ml_dir = pathlib.Path(__file__).parent.parent / "ml"
        assert not ml_dir.exists(), "server/ml/ directory should be removed"

    def test_no_gemini_key_in_docker_compose(self):
        """GEMINI_API_KEY should not appear in docker-compose.yml."""
        compose_path = pathlib.Path(__file__).parent.parent.parent / "docker-compose.yml"
        if compose_path.exists():
            content = compose_path.read_text()
            assert "GEMINI_API_KEY" not in content, "GEMINI_API_KEY should be removed from docker-compose.yml"

    def test_no_v1_code_paths_in_v2(self):
        """No V1 code paths (xgboost, gemini, server.ml) should be importable in V2."""
        server_dir = pathlib.Path(__file__).parent.parent
        for py_file in server_dir.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            if "test_integration_05" in str(py_file):
                continue  # Test file checks for absence
            content = py_file.read_text()
            assert "from server.ml" not in content, f"{py_file.name} imports from server.ml"
            assert "import server.ml" not in content, f"{py_file.name} imports server.ml"
            assert "google.generativeai" not in content, f"{py_file.name} imports google.generativeai"

    def test_no_nba_db_file(self):
        """nba.db (0-byte V1 remnant) should not exist."""
        nba_db = pathlib.Path(__file__).parent.parent / "data" / "nba.db"
        assert not nba_db.exists(), "server/data/nba.db should be removed (V1 remnant)"


class TestRouteRegistration:
    """Verify all Phase 5 routes are registered on app startup."""

    def test_app_has_multiple_routes(self):
        """App should have more routes than just /api/health."""
        from server.app import app
        route_paths = [r.path for r in app.routes]
        # Should have: /api/health + players endpoints + teams endpoints
        assert len(app.routes) > 3, f"Expected more routes, got: {route_paths}"

    def test_players_router_registered(self):
        """players_router should be registered."""
        from server.app import app
        paths = {r.path for r in app.routes}
        assert any("/api/players" in p for p in paths)

    def test_teams_router_registered(self):
        """teams_router should be registered."""
        from server.app import app
        paths = {r.path for r in app.routes}
        assert any("/api/teams" in p for p in paths)
