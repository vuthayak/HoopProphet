import logging
import sqlite3

import pandas as pd
from tqdm import tqdm

from server.pipeline import SEASONS
from server.pipeline.nba_client import NBAClient
from server.pipeline.db import queries

logger = logging.getLogger(__name__)

GAMELOG_COLUMN_MAP = {
    "Player_ID": "player_id",
    "Game_ID": "game_id",
    "GAME_DATE": "game_date",
    "MATCHUP": "matchup",
    "WL": "wl",
    "MIN": "min",
    "PTS": "pts",
    "REB": "reb",
    "AST": "ast",
    "STL": "stl",
    "BLK": "blk",
    "FG3M": "fg3m",
    "FGM": "fgm",
    "FGA": "fga",
    "FTM": "ftm",
    "FTA": "fta",
    "OREB": "oreb",
    "DREB": "dreb",
    "TOV": "tov",
    "PF": "pf",
    "PLUS_MINUS": "plus_minus",
}

SCHEMA_COLUMNS = [
    "player_id", "game_id", "season", "game_date", "matchup", "wl",
    "min", "pts", "reb", "ast", "stl", "blk", "fg3m",
    "fgm", "fga", "ftm", "fta", "oreb", "dreb", "tov", "pf",
    "plus_minus", "is_dnp",
]

NUMERIC_COLUMNS = [
    "min", "pts", "reb", "ast", "stl", "blk", "fg3m",
    "fgm", "fga", "ftm", "fta", "oreb", "dreb", "tov", "pf",
    "plus_minus",
]


def _parse_minutes(min_str) -> float:
    """Convert NBA API minutes to decimal float.

    Handles "MM:SS" strings, raw numeric values, and None/empty.
    """
    if min_str is None or (isinstance(min_str, str) and min_str.strip() == ""):
        return 0.0
    if isinstance(min_str, (int, float)):
        return float(min_str)
    if isinstance(min_str, str) and ":" in min_str:
        parts = min_str.split(":")
        try:
            return int(parts[0]) + int(parts[1]) / 60.0
        except (ValueError, IndexError):
            return 0.0
    try:
        return float(min_str)
    except (ValueError, TypeError):
        return 0.0


def collect_player_gamelogs(
    client: NBAClient, conn: sqlite3.Connection, seasons: list[str] = None
) -> dict:
    """Fetch per-player per-season game logs for all active players.

    Uses per-season calls (not SeasonAll.all) for smaller responses and
    granular progress tracking. Seeds collection_progress for resumability.
    """
    if seasons is None:
        seasons = SEASONS

    cursor = conn.execute(
        "SELECT DISTINCT player_id, full_name FROM players WHERE is_active = 1"
    )
    players = cursor.fetchall()

    if not players:
        logger.info("Players table empty — seeding from NBA API")
        raw_players = client.get_all_active_players()
        for p in raw_players:
            queries.upsert_player(conn, p["id"], p["full_name"], True)
        players = [(p["id"], p["full_name"]) for p in raw_players]

    for pid, _ in players:
        for season in seasons:
            conn.execute(
                "INSERT OR IGNORE INTO collection_progress "
                "(entity_type, entity_id, season, status) "
                "VALUES ('player_gamelog', ?, ?, 'pending')",
                (pid, season),
            )
    conn.commit()

    remaining_cursor = conn.execute(
        "SELECT entity_id, season FROM collection_progress "
        "WHERE entity_type = 'player_gamelog' AND status != 'completed' "
        "ORDER BY season, entity_id"
    )
    remaining = remaining_cursor.fetchall()

    games_inserted = 0
    players_completed = 0
    failed = 0
    skipped = 0

    for player_id, season in tqdm(remaining, desc="Collecting game logs"):
        try:
            df = client.fetch_player_gamelog(player_id, season)
        except ValueError:
            logger.info("No games for player %d in %s", player_id, season)
            queries.mark_progress(conn, "player_gamelog", player_id, season, "completed")
            skipped += 1
            continue
        except Exception as e:
            logger.error("Failed for player %d season %s: %s", player_id, season, e)
            queries.mark_progress(
                conn, "player_gamelog", player_id, season, "failed", str(e)
            )
            failed += 1
            continue

        if not df.empty:
            rename_map = {k: v for k, v in GAMELOG_COLUMN_MAP.items() if k in df.columns}
            df = df.rename(columns=rename_map)

            if "player_id" not in df.columns:
                df["player_id"] = player_id
            df["season"] = season
            df["min"] = df["min"].apply(_parse_minutes)
            df["is_dnp"] = 0

            for col in NUMERIC_COLUMNS:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

            present_cols = [c for c in SCHEMA_COLUMNS if c in df.columns]
            df = df[present_cols]

            queries.insert_game_logs(conn, df)
            games_inserted += len(df)

        queries.mark_progress(conn, "player_gamelog", player_id, season, "completed")
        players_completed += 1

    return {
        "players_completed": players_completed,
        "games_inserted": games_inserted,
        "failed": failed,
        "skipped": skipped,
        "remaining": len(remaining) - players_completed - failed - skipped,
    }
