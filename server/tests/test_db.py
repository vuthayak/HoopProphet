from server.pipeline.db.queries import (
    get_remaining_work,
    insert_game_logs,
    mark_progress,
    upsert_player,
)


def _seed_player(conn, player_id=203999):
    """Insert a player so FK constraints are satisfied for game log inserts."""
    upsert_player(conn, player_id, "Nikola Jokic", True, "C", 1610612743)


def test_schema_creates_all_tables(tmp_db):
    cursor = tmp_db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = {row[0] for row in cursor.fetchall()}
    expected = {
        "players", "teams", "player_game_logs", "team_stats",
        "team_rosters", "team_schedules", "collection_progress",
    }
    assert expected.issubset(tables), f"Missing tables: {expected - tables}"


def test_upsert_player(tmp_db):
    upsert_player(tmp_db, 203999, "Nikola Jokic", True, "C", 1610612743)
    row = tmp_db.execute("SELECT * FROM players WHERE player_id = 203999").fetchone()
    assert row is not None
    assert row["full_name"] == "Nikola Jokic"
    assert row["team_id"] == 1610612743

    upsert_player(tmp_db, 203999, "Nikola Jokic", True, "C", 1610612744)
    rows = tmp_db.execute("SELECT * FROM players WHERE player_id = 203999").fetchall()
    assert len(rows) == 1
    assert rows[0]["team_id"] == 1610612744


def test_progress_tracking(tmp_db):
    mark_progress(tmp_db, "player_gamelog", 203999, "2023-24", "completed")
    remaining = get_remaining_work(tmp_db, "player_gamelog")
    assert (203999, "2023-24") not in remaining

    mark_progress(tmp_db, "player_gamelog", 201566, "2023-24", "pending")
    remaining = get_remaining_work(tmp_db, "player_gamelog")
    assert (201566, "2023-24") in remaining


def test_insert_game_log_dedup(tmp_db, sample_game_log_df):
    _seed_player(tmp_db)
    insert_game_logs(tmp_db, sample_game_log_df)
    count_first = tmp_db.execute("SELECT COUNT(*) FROM player_game_logs").fetchone()[0]
    assert count_first == 5

    insert_game_logs(tmp_db, sample_game_log_df)
    count_second = tmp_db.execute("SELECT COUNT(*) FROM player_game_logs").fetchone()[0]
    assert count_second == 5, "INSERT OR IGNORE should prevent duplicates"


def test_wal_mode_enabled(tmp_db):
    result = tmp_db.execute("PRAGMA journal_mode").fetchone()
    assert result[0] == "wal"
