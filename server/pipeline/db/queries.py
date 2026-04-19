import sqlite3

import pandas as pd


def upsert_player(conn: sqlite3.Connection, player_id: int, full_name: str,
                  is_active: bool, position: str = None, team_id: int = None):
    conn.execute(
        "INSERT OR REPLACE INTO players (player_id, full_name, is_active, position, team_id) "
        "VALUES (?, ?, ?, ?, ?)",
        (player_id, full_name, int(is_active), position, team_id),
    )
    conn.commit()


def upsert_team(conn: sqlite3.Connection, team_id: int, abbreviation: str, full_name: str):
    conn.execute(
        "INSERT OR REPLACE INTO teams (team_id, abbreviation, full_name) VALUES (?, ?, ?)",
        (team_id, abbreviation, full_name),
    )
    conn.commit()


def insert_game_logs(conn: sqlite3.Connection, df: pd.DataFrame):
    cols = [
        "player_id", "game_id", "season", "game_date", "matchup", "wl",
        "min", "pts", "reb", "ast", "stl", "blk", "fg3m",
        "fgm", "fga", "ftm", "fta", "oreb", "dreb", "tov", "pf",
        "plus_minus", "is_dnp",
    ]
    placeholders = ", ".join(["?"] * len(cols))
    sql = f"INSERT OR IGNORE INTO player_game_logs ({', '.join(cols)}) VALUES ({placeholders})"
    rows = [tuple(row[c] for c in cols) for _, row in df.iterrows()]
    conn.executemany(sql, rows)
    conn.commit()


def insert_team_stats(conn: sqlite3.Connection, team_id: int, season: str,
                      def_rating: float, off_rating: float, net_rating: float, pace: float):
    conn.execute(
        "INSERT OR REPLACE INTO team_stats (team_id, season, def_rating, off_rating, net_rating, pace) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (team_id, season, def_rating, off_rating, net_rating, pace),
    )
    conn.commit()


def insert_team_roster(conn: sqlite3.Connection, team_id: int, player_id: int, season: str):
    conn.execute(
        "INSERT OR IGNORE INTO team_rosters (team_id, player_id, season) VALUES (?, ?, ?)",
        (team_id, player_id, season),
    )
    conn.commit()


def insert_team_schedule(conn: sqlite3.Connection, team_id: int, game_id: str,
                         season: str, game_date: str, matchup: str, wl: str):
    conn.execute(
        "INSERT OR IGNORE INTO team_schedules (team_id, game_id, season, game_date, matchup, wl) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (team_id, game_id, season, game_date, matchup, wl),
    )
    conn.commit()


def mark_progress(conn: sqlite3.Connection, entity_type: str, entity_id: int,
                  season: str, status: str, error_message: str = None):
    conn.execute(
        "INSERT OR REPLACE INTO collection_progress "
        "(entity_type, entity_id, season, status, error_message) VALUES (?, ?, ?, ?, ?)",
        (entity_type, entity_id, season, status, error_message),
    )
    conn.commit()


def get_remaining_work(conn: sqlite3.Connection, entity_type: str) -> list[tuple[int, str]]:
    cursor = conn.execute(
        "SELECT entity_id, season FROM collection_progress "
        "WHERE entity_type = ? AND status != 'completed' ORDER BY season, entity_id",
        (entity_type,),
    )
    return [(row[0], row[1]) for row in cursor.fetchall()]


def get_completed_count(conn: sqlite3.Connection, entity_type: str) -> int:
    cursor = conn.execute(
        "SELECT COUNT(*) FROM collection_progress WHERE entity_type = ? AND status = 'completed'",
        (entity_type,),
    )
    return cursor.fetchone()[0]


def get_game_logs_df(conn: sqlite3.Connection, seasons: list[str] = None) -> pd.DataFrame:
    if seasons:
        placeholders = ",".join(["?"] * len(seasons))
        return pd.read_sql_query(
            f"SELECT * FROM player_game_logs WHERE season IN ({placeholders})",
            conn,
            params=seasons,
        )
    return pd.read_sql_query("SELECT * FROM player_game_logs", conn)


def get_team_stats_df(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query("SELECT * FROM team_stats", conn)


def get_players_df(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query(
        "SELECT player_id, full_name, is_active, position, team_id FROM players",
        conn,
    )


def get_teams_df(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query(
        "SELECT team_id, abbreviation, full_name FROM teams",
        conn,
    )


def insert_news_items(conn: sqlite3.Connection, items: list[dict]):
    """Insert news items, ignoring duplicates."""
    cols = ["source", "source_url", "headline", "raw_content", "published_at",
            "fetched_at", "player_id", "player_name", "alert_keywords"]
    placeholders = ", ".join(["?"] * len(cols))
    sql = f"INSERT OR IGNORE INTO news_items ({', '.join(cols)}) VALUES ({placeholders})"
    rows = [tuple(item.get(c) for c in cols) for item in items]
    conn.executemany(sql, rows)
    conn.commit()


def insert_player_alerts(conn: sqlite3.Connection, alerts: list[dict]):
    """Upsert player alerts — update last_updated_at and severity on re-match."""
    for alert in alerts:
        conn.execute(
            """INSERT INTO player_alerts (player_id, alert_type, subcategory, severity, source, source_url, headline, first_seen_at, last_updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
               ON CONFLICT(player_id, alert_type, source) DO UPDATE SET
                   subcategory=excluded.subcategory,
                   severity=excluded.severity,
                   headline=excluded.headline,
                   source_url=excluded.source_url,
                   last_updated_at=datetime('now')""",
            (alert["player_id"], alert["alert_type"], alert.get("subcategory"),
             alert["severity"], alert["source"], alert.get("source_url"),
             alert.get("headline"))
        )
    conn.commit()


def get_player_alerts(conn: sqlite3.Connection, player_id: int) -> list[dict]:
    """Get active alerts for a player, ordered by last_updated_at DESC."""
    cursor = conn.execute(
        "SELECT id, player_id, alert_type, subcategory, severity, source, source_url, headline, first_seen_at, last_updated_at "
        "FROM player_alerts WHERE player_id = ? ORDER BY last_updated_at DESC",
        (player_id,)
    )
    return [dict(row) for row in cursor.fetchall()]


def get_news_items(conn: sqlite3.Connection, player_id: int, limit: int = 50) -> list[dict]:
    """Get news items for a player, ordered by published_at DESC."""
    cursor = conn.execute(
        "SELECT id, source, source_url, headline, raw_content, published_at, fetched_at, player_id, player_name, alert_keywords "
        "FROM news_items WHERE player_id = ? ORDER BY published_at DESC LIMIT ?",
        (player_id, limit)
    )
    return [dict(row) for row in cursor.fetchall()]


def get_stale_alerts(conn: sqlite3.Connection, max_age_hours: int = 24) -> list[dict]:
    """Get alerts last updated more than max_age_hours ago (for stale data warning per D-08)."""
    cursor = conn.execute(
        "SELECT * FROM player_alerts WHERE datetime(last_updated_at) < datetime('now', ?)",
        (f"-{max_age_hours} hours",)
    )
    return [dict(row) for row in cursor.fetchall()]


def cleanup_stale_news(conn: sqlite3.Connection, max_age_days: int = 30):
    """Delete news items older than max_age_days to prevent unbounded growth."""
    conn.execute(
        "DELETE FROM news_items WHERE datetime(fetched_at) < datetime('now', ?)",
        (f"-{max_age_days} days",)
    )
    conn.commit()


def cleanup_expired_alerts(conn: sqlite3.Connection):
    """Remove alerts where the source news is no longer present (replaced/expired)."""
    conn.execute(
        "DELETE FROM player_alerts WHERE player_id NOT IN (SELECT DISTINCT player_id FROM news_items WHERE player_id IS NOT NULL) "
        "AND datetime(last_updated_at) < datetime('now', '-7 days')"
    )
    conn.commit()
