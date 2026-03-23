import sqlite3
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from server.pipeline.db import queries
from server.pipeline.db.schema import init_db
from server.pipeline.collectors.game_logs import collect_player_gamelogs
from server.pipeline.collectors.team_stats import collect_team_stats
from server.pipeline.ingest import validate_completeness, main


def _create_mock_client():
    """Build a MagicMock NBAClient with realistic return values."""
    client = MagicMock()

    client.get_all_teams.return_value = [
        {"id": 1, "full_name": "Boston Celtics", "abbreviation": "BOS"},
        {"id": 2, "full_name": "Los Angeles Lakers", "abbreviation": "LAL"},
    ]

    client.get_all_active_players.return_value = [
        {"id": 101, "full_name": "Player A", "is_active": True},
        {"id": 102, "full_name": "Player B", "is_active": True},
        {"id": 103, "full_name": "Player C", "is_active": True},
    ]

    client.fetch_team_roster.return_value = pd.DataFrame([
        {"PLAYER_ID": 101, "PLAYER": "Player A", "POSITION": "G", "NUM": "0"},
        {"PLAYER_ID": 102, "PLAYER": "Player B", "POSITION": "F", "NUM": "7"},
        {"PLAYER_ID": 103, "PLAYER": "Player C", "POSITION": "C", "NUM": "13"},
    ])

    client.fetch_team_schedule.return_value = pd.DataFrame([
        {"TEAM_ID": 1, "GAME_ID": "0022300001", "GAME_DATE": "2023-10-25",
         "MATCHUP": "BOS vs. NYK", "WL": "W"},
        {"TEAM_ID": 1, "GAME_ID": "0022300002", "GAME_DATE": "2023-10-27",
         "MATCHUP": "BOS @ PHI", "WL": "L"},
        {"TEAM_ID": 1, "GAME_ID": "0022300003", "GAME_DATE": "2023-10-30",
         "MATCHUP": "BOS vs. MIA", "WL": "W"},
        {"TEAM_ID": 1, "GAME_ID": "0022300004", "GAME_DATE": "2023-11-01",
         "MATCHUP": "BOS @ CLE", "WL": "W"},
        {"TEAM_ID": 1, "GAME_ID": "0022300005", "GAME_DATE": "2023-11-03",
         "MATCHUP": "BOS vs. TOR", "WL": "L"},
    ])

    client.fetch_team_advanced_stats.return_value = pd.DataFrame([
        {"TEAM_ID": 1, "TEAM_NAME": "Boston Celtics",
         "DEF_RATING": 108.5, "OFF_RATING": 115.2, "NET_RATING": 6.7, "PACE": 99.3},
        {"TEAM_ID": 2, "TEAM_NAME": "Los Angeles Lakers",
         "DEF_RATING": 112.1, "OFF_RATING": 113.8, "NET_RATING": 1.7, "PACE": 100.1},
    ])

    def _mock_gamelog(player_id, season):
        return pd.DataFrame([
            {"Player_ID": player_id, "Game_ID": f"00223000{i:02d}",
             "GAME_DATE": f"2023-10-{25 + i * 2}", "SEASON_ID": "22023",
             "MATCHUP": "BOS vs. NYK", "WL": "W",
             "MIN": "30:00", "PTS": 20, "REB": 5, "AST": 5,
             "STL": 1, "BLK": 1, "FG3M": 2, "FGM": 8, "FGA": 15,
             "FTM": 2, "FTA": 3, "OREB": 1, "DREB": 4,
             "TOV": 2, "PF": 2, "PLUS_MINUS": 5}
            for i in range(3)
        ])

    client.fetch_player_gamelog.side_effect = _mock_gamelog
    return client


def _seed_teams_and_players(conn):
    """Insert minimal teams and players for tests."""
    for t in [
        (1, "BOS", "Boston Celtics"),
        (2, "LAL", "Los Angeles Lakers"),
    ]:
        queries.upsert_team(conn, *t)
    for p in [
        (101, "Player A"),
        (102, "Player B"),
        (103, "Player C"),
    ]:
        queries.upsert_player(conn, p[0], p[1], True)


class TestGameLogsStored:

    def test_gamelogs_stored(self, tmp_db):
        mock_client = _create_mock_client()
        _seed_teams_and_players(tmp_db)

        for pid in [101, 102, 103]:
            queries.mark_progress(tmp_db, "player_gamelog", pid, "2023-24", "pending")

        collect_player_gamelogs(mock_client, tmp_db, seasons=["2023-24"])

        count = tmp_db.execute(
            "SELECT COUNT(*) FROM player_game_logs WHERE is_dnp = 0"
        ).fetchone()[0]
        assert count > 0

        player_ids = {
            row[0] for row in
            tmp_db.execute("SELECT DISTINCT player_id FROM player_game_logs").fetchall()
        }
        assert {101, 102, 103} == player_ids

        row = tmp_db.execute(
            "SELECT pts, reb, ast FROM player_game_logs WHERE player_id = 101 LIMIT 1"
        ).fetchone()
        assert row[0] == 20
        assert row[1] == 5
        assert row[2] == 5


class TestTeamStatsStored:

    def test_team_stats_stored(self, tmp_db):
        mock_client = _create_mock_client()
        _seed_teams_and_players(tmp_db)

        collect_team_stats(mock_client, tmp_db, seasons=["2023-24"])

        rows = tmp_db.execute(
            "SELECT * FROM team_stats WHERE season = '2023-24'"
        ).fetchall()
        assert len(rows) == 2

        bos = tmp_db.execute(
            "SELECT def_rating, pace FROM team_stats "
            "WHERE team_id = 1 AND season = '2023-24'"
        ).fetchone()
        assert bos[0] == pytest.approx(108.5)
        assert bos[1] == pytest.approx(99.3)


class TestResumeAfterInterrupt:

    def test_resume_after_interrupt(self, tmp_db):
        mock_client = _create_mock_client()
        _seed_teams_and_players(tmp_db)

        for pid in [101, 102, 103]:
            queries.mark_progress(tmp_db, "player_gamelog", pid, "2023-24", "pending")

        for pid in [101, 102, 103]:
            queries.mark_progress(tmp_db, "player_gamelog", pid, "2023-24",
                                  "completed" if pid <= 103 else "pending")
        queries.mark_progress(tmp_db, "player_gamelog", 101, "2023-24", "completed")
        queries.mark_progress(tmp_db, "player_gamelog", 102, "2023-24", "completed")
        queries.mark_progress(tmp_db, "player_gamelog", 103, "2023-24", "completed")

        for pid in [104, 105]:
            queries.upsert_player(tmp_db, pid, f"Player {pid}", True)
            queries.mark_progress(tmp_db, "player_gamelog", pid, "2023-24", "pending")

        collect_player_gamelogs(mock_client, tmp_db, seasons=["2023-24"])

        called_player_ids = {
            call.args[0] for call in mock_client.fetch_player_gamelog.call_args_list
        }
        assert 101 not in called_player_ids
        assert 102 not in called_player_ids
        assert 103 not in called_player_ids
        assert 104 in called_player_ids
        assert 105 in called_player_ids

        all_statuses = tmp_db.execute(
            "SELECT entity_id, status FROM collection_progress "
            "WHERE entity_type = 'player_gamelog' AND season = '2023-24'"
        ).fetchall()
        status_map = {row[0]: row[1] for row in all_statuses}
        for pid in [101, 102, 103, 104, 105]:
            assert status_map[pid] == "completed"


class TestValidateCompleteness:

    def test_validates_insufficient_data(self, tmp_db):
        for i in range(10):
            queries.upsert_team(tmp_db, i, f"T{i:02d}", f"Team {i}")

        result = validate_completeness(tmp_db)
        assert result is False

    def test_validates_sufficient_data(self, tmp_db):
        for i in range(30):
            queries.upsert_team(tmp_db, i + 1, f"T{i:02d}", f"Team {i}")

        for i in range(450):
            queries.upsert_player(tmp_db, i + 1, f"Player {i}", True)

        cols = [
            "player_id", "game_id", "season", "game_date", "matchup", "wl",
            "min", "pts", "reb", "ast", "stl", "blk", "fg3m",
            "fgm", "fga", "ftm", "fta", "oreb", "dreb", "tov", "pf",
            "plus_minus", "is_dnp",
        ]
        placeholders = ", ".join(["?"] * len(cols))
        sql = f"INSERT OR IGNORE INTO player_game_logs ({', '.join(cols)}) VALUES ({placeholders})"
        rows = []
        for pid in range(1, 451):
            for g in range(120):
                rows.append((
                    pid, f"G{pid:04d}{g:03d}", "2023-24",
                    f"2023-{10 + g // 30:02d}-{1 + g % 28:02d}",
                    "BOS vs. NYK", "W",
                    30.0, 20.0, 5.0, 5.0, 1.0, 1.0, 2.0, 8.0, 15.0,
                    2.0, 3.0, 1.0, 4.0, 2.0, 2.0, 5.0, 0,
                ))
        tmp_db.executemany(sql, rows)
        tmp_db.commit()

        for i in range(30):
            for s in ["2023-24", "2022-23", "2021-22", "2020-21"]:
                queries.insert_team_stats(tmp_db, i + 1, s, 110.0, 112.0, 2.0, 99.0)

        result = validate_completeness(tmp_db)
        assert result is True


class TestFullPipelineMock:

    @patch("server.pipeline.ingest.get_connection")
    @patch("server.pipeline.ingest.NBAClient")
    def test_full_pipeline_mock(self, mock_client_cls, mock_get_conn, tmp_db):
        mock_client = _create_mock_client()
        mock_client_cls.return_value = mock_client

        wrapper = MagicMock(wraps=tmp_db)
        wrapper.close = MagicMock()
        mock_get_conn.return_value = wrapper

        with patch("sys.argv", ["ingest", "--full"]):
            with pytest.raises(SystemExit):
                main()

        assert tmp_db.execute("SELECT COUNT(*) FROM teams").fetchone()[0] > 0
        assert tmp_db.execute("SELECT COUNT(*) FROM players").fetchone()[0] > 0
        assert tmp_db.execute("SELECT COUNT(*) FROM player_game_logs").fetchone()[0] > 0
        assert tmp_db.execute("SELECT COUNT(*) FROM team_stats").fetchone()[0] > 0
        assert tmp_db.execute("SELECT COUNT(*) FROM team_rosters").fetchone()[0] > 0
        assert tmp_db.execute("SELECT COUNT(*) FROM team_schedules").fetchone()[0] > 0
