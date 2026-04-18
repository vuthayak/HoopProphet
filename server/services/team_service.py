"""
Team data service — queries from SQLite cache per CLNP-03.

All functions read from the cached SQLite DB, NOT live NBA API calls.
"""

import sqlite3

import pandas as pd

from server.core.config import DB_PATH
from server.pipeline.db.queries import get_teams_df


def get_connection() -> sqlite3.Connection:
    """Open a connection to DB_PATH with foreign keys enabled.

    Caller is responsible for closing (use in `with` or try/finally).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_teams() -> list[dict]:
    """Return all teams as list of dicts with team_id, abbreviation, full_name."""
    with get_connection() as conn:
        df = get_teams_df(conn)
    return df[["team_id", "abbreviation", "full_name"]].to_dict(orient="records")


def get_team_by_id(team_id: int) -> dict:
    """Return single team dict.

    Raises:
        ValueError: If team_id doesn't exist in the database.
    """
    with get_connection() as conn:
        df = get_teams_df(conn)
    row = df[df["team_id"] == team_id]
    if row.empty:
        raise ValueError(f"Team not found: {team_id}")
    return row.iloc[0][["team_id", "abbreviation", "full_name"]].to_dict()
