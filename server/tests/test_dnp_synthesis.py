import sqlite3

import pytest

from server.pipeline.db import queries
from server.pipeline.db.schema import init_db
from server.pipeline.processors.dnp_synthesis import (
    synthesize_dnp_rows,
    synthesize_all_dnp_rows,
)


def _seed_teams(conn, teams):
    """Insert team rows: teams = [(team_id, abbreviation, full_name), ...]"""
    for tid, abbr, name in teams:
        queries.upsert_team(conn, tid, abbr, name)


def _seed_players(conn, players):
    """Insert player rows: players = [(player_id, full_name), ...]"""
    for pid, name in players:
        queries.upsert_player(conn, pid, name, True)


def _seed_rosters(conn, entries):
    """Insert roster entries: entries = [(team_id, player_id, season), ...]"""
    for tid, pid, season in entries:
        queries.insert_team_roster(conn, tid, pid, season)


def _seed_schedules(conn, games):
    """Insert schedule games: games = [(team_id, game_id, season, date, matchup, wl), ...]"""
    for tid, gid, season, gdate, matchup, wl in games:
        queries.insert_team_schedule(conn, tid, gid, season, gdate, matchup, wl)


def _seed_game_logs(conn, logs):
    """Insert game logs: logs = list of dicts with all player_game_logs columns."""
    import pandas as pd
    if logs:
        queries.insert_game_logs(conn, pd.DataFrame(logs))


def _make_log(player_id, game_id, season, game_date, matchup, **overrides):
    """Build a single game log dict with sensible defaults."""
    row = {
        "player_id": player_id, "game_id": game_id,
        "season": season, "game_date": game_date,
        "matchup": matchup, "wl": "W",
        "min": 30.0, "pts": 20.0, "reb": 5.0, "ast": 5.0,
        "stl": 1.0, "blk": 1.0, "fg3m": 2.0, "fgm": 8.0, "fga": 15.0,
        "ftm": 2.0, "fta": 3.0, "oreb": 1.0, "dreb": 4.0,
        "tov": 2.0, "pf": 2.0, "plus_minus": 5.0,
        "is_dnp": 0,
    }
    row.update(overrides)
    return row


class TestDNPSynthesis:

    def test_dnp_rows_created(self, tmp_db):
        _seed_teams(tmp_db, [(1, "BOS", "Boston Celtics")])
        _seed_players(tmp_db, [(101, "Player A"), (102, "Player B")])
        _seed_rosters(tmp_db, [(1, 101, "2023-24"), (1, 102, "2023-24")])
        _seed_schedules(tmp_db, [
            (1, "001", "2023-24", "2023-10-25", "BOS vs. NYK", "W"),
            (1, "002", "2023-24", "2023-10-27", "BOS @ PHI", "W"),
            (1, "003", "2023-24", "2023-10-30", "BOS vs. MIA", "L"),
            (1, "004", "2023-24", "2023-11-01", "BOS @ CLE", "W"),
            (1, "005", "2023-24", "2023-11-03", "BOS vs. TOR", "W"),
        ])

        _seed_game_logs(tmp_db, [
            _make_log(101, "001", "2023-24", "2023-10-25", "BOS vs. NYK"),
            _make_log(101, "002", "2023-24", "2023-10-27", "BOS @ PHI"),
            _make_log(101, "003", "2023-24", "2023-10-30", "BOS vs. MIA"),
            _make_log(101, "004", "2023-24", "2023-11-01", "BOS @ CLE"),
            _make_log(102, "001", "2023-24", "2023-10-25", "BOS vs. NYK"),
            _make_log(102, "002", "2023-24", "2023-10-27", "BOS @ PHI"),
            _make_log(102, "003", "2023-24", "2023-10-30", "BOS vs. MIA"),
        ])

        count = synthesize_dnp_rows(tmp_db, "2023-24")

        cursor = tmp_db.execute(
            "SELECT player_id, game_id FROM player_game_logs WHERE is_dnp = 1 "
            "ORDER BY player_id, game_id"
        )
        dnp_rows = cursor.fetchall()

        assert count == 3
        assert len(dnp_rows) == 3

        player_a_dnps = [r for r in dnp_rows if r[0] == 101]
        player_b_dnps = [r for r in dnp_rows if r[0] == 102]
        assert len(player_a_dnps) == 1
        assert player_a_dnps[0][1] == "005"
        assert len(player_b_dnps) == 2
        assert {r[1] for r in player_b_dnps} == {"004", "005"}

        for row in dnp_rows:
            full = tmp_db.execute(
                "SELECT is_dnp, min, pts FROM player_game_logs "
                "WHERE player_id = ? AND game_id = ?",
                (row[0], row[1]),
            ).fetchone()
            assert full[0] == 1
            assert full[1] == 0
            assert full[2] == 0

    def test_no_false_dnp_for_traded_player(self, tmp_db):
        _seed_teams(tmp_db, [
            (1, "BOS", "Boston Celtics"),
            (2, "LAL", "Los Angeles Lakers"),
        ])
        _seed_players(tmp_db, [(201, "Traded Player")])
        _seed_rosters(tmp_db, [(2, 201, "2023-24")])
        _seed_schedules(tmp_db, [
            (2, "G01", "2023-24", "2023-10-25", "LAL vs. GSW", "W"),
            (2, "G02", "2023-24", "2023-11-01", "LAL @ PHX", "L"),
            (2, "G03", "2023-24", "2023-11-15", "LAL vs. DEN", "W"),
            (2, "G04", "2023-24", "2023-12-01", "LAL @ SAC", "L"),
            (2, "G05", "2023-24", "2024-01-10", "LAL vs. MIN", "W"),
            (2, "G06", "2023-24", "2024-01-20", "LAL @ OKC", "W"),
            (2, "G07", "2023-24", "2024-02-05", "LAL vs. DAL", "L"),
            (2, "G08", "2023-24", "2024-02-15", "LAL @ POR", "W"),
            (2, "G09", "2023-24", "2024-03-01", "LAL vs. SAS", "W"),
            (2, "G10", "2023-24", "2024-03-15", "LAL @ LAC", "L"),
        ])

        _seed_game_logs(tmp_db, [
            _make_log(201, "G05", "2023-24", "2024-01-10", "LAL vs. MIN"),
            _make_log(201, "G06", "2023-24", "2024-01-20", "LAL @ OKC"),
            _make_log(201, "G07", "2023-24", "2024-02-05", "LAL vs. DAL"),
            _make_log(201, "G09", "2023-24", "2024-03-01", "LAL vs. SAS"),
            _make_log(201, "G10", "2023-24", "2024-03-15", "LAL @ LAC"),
        ])

        count = synthesize_dnp_rows(tmp_db, "2023-24")

        cursor = tmp_db.execute(
            "SELECT game_id, game_date FROM player_game_logs "
            "WHERE player_id = 201 AND is_dnp = 1 ORDER BY game_date"
        )
        dnp_rows = cursor.fetchall()

        assert count == 1
        assert len(dnp_rows) == 1
        assert dnp_rows[0][0] == "G08"

        early_dnps = [r for r in dnp_rows if r[1] < "2024-01-10"]
        assert len(early_dnps) == 0

    def test_dnp_idempotent(self, tmp_db):
        _seed_teams(tmp_db, [(1, "BOS", "Boston Celtics")])
        _seed_players(tmp_db, [(101, "Player A"), (102, "Player B")])
        _seed_rosters(tmp_db, [(1, 101, "2023-24"), (1, 102, "2023-24")])
        _seed_schedules(tmp_db, [
            (1, "001", "2023-24", "2023-10-25", "BOS vs. NYK", "W"),
            (1, "002", "2023-24", "2023-10-27", "BOS @ PHI", "W"),
            (1, "003", "2023-24", "2023-10-30", "BOS vs. MIA", "L"),
        ])
        _seed_game_logs(tmp_db, [
            _make_log(101, "001", "2023-24", "2023-10-25", "BOS vs. NYK"),
            _make_log(101, "002", "2023-24", "2023-10-27", "BOS @ PHI"),
            _make_log(102, "001", "2023-24", "2023-10-25", "BOS vs. NYK"),
        ])

        synthesize_dnp_rows(tmp_db, "2023-24")
        count_after_first = tmp_db.execute(
            "SELECT COUNT(*) FROM player_game_logs"
        ).fetchone()[0]

        synthesize_dnp_rows(tmp_db, "2023-24")
        count_after_second = tmp_db.execute(
            "SELECT COUNT(*) FROM player_game_logs"
        ).fetchone()[0]

        assert count_after_first == count_after_second

    def test_no_dnp_for_player_with_no_gamelogs(self, tmp_db):
        _seed_teams(tmp_db, [(1, "BOS", "Boston Celtics")])
        _seed_players(tmp_db, [(301, "Preseason Cut")])
        _seed_rosters(tmp_db, [(1, 301, "2023-24")])
        _seed_schedules(tmp_db, [
            (1, "001", "2023-24", "2023-10-25", "BOS vs. NYK", "W"),
            (1, "002", "2023-24", "2023-10-27", "BOS @ PHI", "W"),
        ])

        count = synthesize_dnp_rows(tmp_db, "2023-24")

        cursor = tmp_db.execute(
            "SELECT COUNT(*) FROM player_game_logs WHERE player_id = 301"
        )
        assert cursor.fetchone()[0] == 0
        assert count == 0
