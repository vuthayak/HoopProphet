"""
Player data service — queries from SQLite cache per CLNP-03.

All functions read from the cached SQLite DB, NOT live NBA API calls.
"""

import sqlite3
from typing import Optional

import pandas as pd

from server.core.config import DB_PATH
from server.pipeline.db.queries import get_game_logs_df, get_players_df
from server.pipeline.feature_config import STAT_COLS


def get_connection() -> sqlite3.Connection:
    """Open a connection to DB_PATH with foreign keys enabled.

    Caller is responsible for closing (use in `with` or try/finally).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_players(active_only: bool = True) -> list[dict]:
    """Return all players as list of dicts with player_id, full_name, position, team_id.

    Args:
        active_only: If True (default), only return is_active==1 players.
    """
    with get_connection() as conn:
        df = get_players_df(conn)
    if active_only:
        df = df[df["is_active"] == 1] if "is_active" in df.columns else df
    return df[["player_id", "full_name", "position", "team_id"]].to_dict(orient="records")


def search_players(query: str, active_only: bool = True) -> list[dict]:
    """Case-insensitive partial match on full_name.

    Args:
        query: Search string to match against player full names.
        active_only: If True (default), only return is_active==1 players.
    """
    if not query:
        return get_players(active_only=active_only)
    with get_connection() as conn:
        df = get_players_df(conn)
    if active_only:
        df = df[df["is_active"] == 1] if "is_active" in df.columns else df
    mask = df["full_name"].str.contains(query, case=False, na=False)
    return df[mask][["player_id", "full_name", "position", "team_id"]].to_dict(orient="records")


def get_player_by_id(player_id: int) -> dict:
    """Return single player dict.

    Raises:
        ValueError: If player_id doesn't exist in the database.
    """
    with get_connection() as conn:
        df = get_players_df(conn)
    row = df[df["player_id"] == player_id]
    if row.empty:
        raise ValueError(f"Player not found: {player_id}")
    return row.iloc[0][["player_id", "full_name", "position", "team_id"]].to_dict()


def get_player_game_logs(
    player_id: int,
    seasons: Optional[list[str]] = None,
    limit: Optional[int] = None,
) -> list[dict]:
    """Return game log rows for a player from SQLite.

    Args:
        player_id: The NBA player ID.
        seasons: Optional list of season strings (e.g. ["2023-24"]) to filter.
        limit: If provided, return last N rows sorted by game_date DESC.

    Returns:
        List of dicts with game_id, season, game_date, matchup, wl, is_dnp,
        plus all STAT_COLS. NaN/None values replaced with 0 for numeric,
        empty string for strings. Returns empty list if player has no game logs.
    """
    with get_connection() as conn:
        df = get_game_logs_df(conn, seasons=seasons)
    df = df[df["player_id"] == player_id]
    if df.empty:
        return []

    # Sort by game_date DESC, apply limit
    df = df.sort_values("game_date", ascending=False)
    if limit is not None:
        df = df.head(limit)

    # Build output dict with all relevant columns
    stat_cols_present = [c for c in STAT_COLS if c in df.columns]
    out_cols = ["player_id", "game_id", "season", "game_date", "matchup", "wl", "is_dnp"] + stat_cols_present
    result = df[out_cols].copy()

    # Replace NaN with appropriate defaults
    for col in stat_cols_present:
        result[col] = result[col].fillna(0)
    result["wl"] = result["wl"].fillna("")
    result["matchup"] = result["matchup"].fillna("")

    return result.to_dict(orient="records")
