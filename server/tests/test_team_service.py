"""
Tests for team_service — get_teams, get_team_by_id.

Uses a clean temp SQLite DB with schema and seed team data per test.
"""

import os
import shutil
import sqlite3
import tempfile

import pytest

from server.pipeline.db.queries import upsert_team
from server.pipeline.db.schema import init_db


@pytest.fixture
def team_db():
    """Provide a temp SQLite DB with schema and seeded teams."""
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "test.db")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    init_db(conn)

    upsert_team(conn, 1610612747, "LAL", "Los Angeles Lakers")
    upsert_team(conn, 1610612743, "DEN", "Denver Nuggets")
    upsert_team(conn, 1610612751, "BKN", "Brooklyn Nets")
    conn.commit()
    conn.close()

    yield db_path
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture
def svc(team_db, monkeypatch):
    """Patch team_service DB_PATH and return the service module."""
    from server.services import team_service

    monkeypatch.setattr(team_service, "DB_PATH", team_db)
    return team_service


class TestGetTeams:
    def test_returns_list_of_dicts(self, svc):
        teams = svc.get_teams()
        assert isinstance(teams, list)
        assert len(teams) == 3

    def test_teams_have_required_fields(self, svc):
        teams = svc.get_teams()
        for team in teams:
            assert "team_id" in team
            assert "abbreviation" in team
            assert "full_name" in team


class TestGetTeamById:
    def test_returns_correct_team_dict(self, svc):
        team = svc.get_team_by_id(1610612747)
        assert team["team_id"] == 1610612747
        assert team["abbreviation"] == "LAL"
        assert team["full_name"] == "Los Angeles Lakers"

    def test_raises_for_unknown_id(self, svc):
        with pytest.raises(ValueError, match="Team not found"):
            svc.get_team_by_id(99999999)
