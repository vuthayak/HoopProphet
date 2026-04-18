"""
Tests for player_service — get_players, search_players, get_player_by_id, get_player_game_logs.

Uses a clean temp SQLite DB with schema and seed data per test.
"""

import os
import shutil
import sqlite3
import tempfile

import pandas as pd
import pytest

from server.pipeline.db.queries import insert_game_logs, upsert_player, upsert_team
from server.pipeline.db.schema import init_db


@pytest.fixture
def player_db():
    """Provide a temp SQLite DB with schema and seed player/team/game_log data."""
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
    upsert_player(conn, 999999, "Retired Player", False, "G", None)

    game_logs = [
        {"player_id": lebron_id, "game_id": "0022301001", "season": "2023-24",
         "game_date": "2023-10-24", "matchup": "LAL @ DEN", "wl": "L",
         "min": 36.0, "pts": 27.0, "reb": 8.0, "ast": 9.0, "stl": 1.0,
         "blk": 1.0, "fg3m": 2.0, "fgm": 10.0, "fga": 20.0, "ftm": 5.0,
         "fta": 7.0, "oreb": 1.0, "dreb": 7.0, "tov": 3.0, "pf": 2.0,
         "plus_minus": -7.0, "is_dnp": 0},
        {"player_id": lebron_id, "game_id": "0022301002", "season": "2023-24",
         "game_date": "2023-10-26", "matchup": "LAL vs. PHX", "wl": "W",
         "min": 35.0, "pts": 31.0, "reb": 9.0, "ast": 8.0, "stl": 2.0,
         "blk": 0.0, "fg3m": 3.0, "fgm": 11.0, "fga": 21.0, "ftm": 6.0,
         "fta": 8.0, "oreb": 1.0, "dreb": 8.0, "tov": 4.0, "pf": 2.0,
         "plus_minus": 6.0, "is_dnp": 0},
        {"player_id": lebron_id, "game_id": "0022301003", "season": "2023-24",
         "game_date": "2023-10-29", "matchup": "LAL @ SAC", "wl": "L",
         "min": 34.0, "pts": 25.0, "reb": 7.0, "ast": 6.0, "stl": 1.0,
         "blk": 1.0, "fg3m": 2.0, "fgm": 9.0, "fga": 19.0, "ftm": 5.0,
         "fta": 6.0, "oreb": 1.0, "dreb": 6.0, "tov": 3.0, "pf": 3.0,
         "plus_minus": -5.0, "is_dnp": 0},
        {"player_id": jokic_id, "game_id": "0022300001", "season": "2023-24",
         "game_date": "2023-10-25", "matchup": "DEN vs. LAL", "wl": "W",
         "min": 35.0, "pts": 29.0, "reb": 12.0, "ast": 11.0, "stl": 1.0,
         "blk": 1.0, "fg3m": 2.0, "fgm": 11.0, "fga": 18.0, "ftm": 5.0,
         "fta": 6.0, "oreb": 2.0, "dreb": 10.0, "tov": 3.0, "pf": 2.0,
         "plus_minus": 15.0, "is_dnp": 0},
        {"player_id": jokic_id, "game_id": "0022300002", "season": "2023-24",
         "game_date": "2023-10-27", "matchup": "DEN @ MEM", "wl": "W",
         "min": 37.0, "pts": 27.0, "reb": 10.0, "ast": 9.0, "stl": 2.0,
         "blk": 0.0, "fg3m": 1.0, "fgm": 10.0, "fga": 19.0, "ftm": 6.0,
         "fta": 7.0, "oreb": 2.0, "dreb": 8.0, "tov": 4.0, "pf": 2.0,
         "plus_minus": 7.0, "is_dnp": 0},
    ]
    insert_game_logs(conn, pd.DataFrame(game_logs))
    conn.commit()
    conn.close()

    yield db_path
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture
def svc(player_db, monkeypatch):
    """Patch player_service DB_PATH and return the service module."""
    from server.services import player_service

    monkeypatch.setattr(player_service, "DB_PATH", player_db)
    return player_service


class TestGetPlayers:
    def test_returns_list_of_dicts(self, svc):
        result = svc.get_players(active_only=True)
        assert isinstance(result, list)
        assert len(result) >= 2

    def test_active_only_filter(self, svc):
        active = svc.get_players(active_only=True)
        all_players = svc.get_players(active_only=False)
        assert len(active) < len(all_players)


class TestSearchPlayers:
    def test_exact_name_match(self, svc):
        results = svc.search_players("LeBron")
        assert len(results) >= 1
        names = [r["full_name"] for r in results]
        assert "LeBron James" in names

    def test_case_insensitive(self, svc):
        results = svc.search_players("jokic")
        names = [r["full_name"] for r in results]
        assert "Nikola Jokic" in names

    def test_empty_query_returns_all_active(self, svc):
        results = svc.search_players("")
        active = svc.get_players(active_only=True)
        assert len(results) == len(active)


class TestGetPlayerById:
    def test_returns_player_dict(self, svc):
        player = svc.get_player_by_id(2544)
        assert player["player_id"] == 2544
        assert player["full_name"] == "LeBron James"

    def test_raises_for_unknown_id(self, svc):
        with pytest.raises(ValueError, match="Player not found"):
            svc.get_player_by_id(99999999)


class TestGetPlayerGameLogs:
    def test_returns_list_of_dicts(self, svc):
        logs = svc.get_player_game_logs(2544)
        assert isinstance(logs, list)
        assert len(logs) >= 2

    def test_returns_recent_games_first(self, svc):
        logs = svc.get_player_game_logs(2544)
        dates = [log["game_date"] for log in logs]
        assert dates == sorted(dates, reverse=True)

    def test_limit_returns_last_n_games(self, svc):
        logs = svc.get_player_game_logs(2544, limit=2)
        assert len(logs) == 2

    def test_season_filter(self, svc):
        logs = svc.get_player_game_logs(2544, seasons=["2023-24"])
        for log in logs:
            assert log["season"] == "2023-24"

    def test_unknown_player_returns_empty_list(self, svc):
        logs = svc.get_player_game_logs(99999999)
        assert logs == []
