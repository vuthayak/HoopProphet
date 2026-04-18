"""
Hit rate computation service — per D-09.

Hit rate = percentage of games in a window where stat > default line.
Each window returns {rate: float, count: int}.
Windows with <5 games return None per D-11.
"""

import logging
from typing import Optional

from server.services.player_service import get_player_game_logs
from server.pipeline.feature_config import WINDOWS_PRIMARY

logger = logging.getLogger(__name__)


def get_hit_rates(
    player_id: int,
    stat: str,
    line_value: float,
    seasons: Optional[list[str]] = None,
) -> dict:
    """Compute hit rates across L5, L10, L20, and full-season windows.

    Hit rate = percentage of games in the window where the player's stat
    exceeds the given line_value.

    Args:
        player_id: NBA player ID.
        stat: Stat name (e.g., "pts", "reb", "ast").
        line_value: The threshold to beat for a "hit".
        seasons: Optional list of season strings to filter.

    Returns:
        Dict with L5, L10, L20, season keys. Each value is either:
        - None if <5 games in that window (per D-11)
        - {"rate": float, "count": int} with the hit rate and sample size

    Raises:
        ValueError: If player has no game logs in the database.
    """
    # Get all game logs for the player
    game_logs = get_player_game_logs(player_id, seasons=seasons)

    if not game_logs:
        raise ValueError(f"Player not found: {player_id}")

    # Filter to non-DNP games where stat is not null/0
    non_dnp = [g for g in game_logs if g.get("is_dnp", 1) == 0 and g.get(stat, 0) is not None]

    if not non_dnp:
        raise ValueError(f"Player not found: {player_id}")

    # Sort by game_date DESC (most recent first)
    non_dnp = sorted(non_dnp, key=lambda g: g.get("game_date", ""), reverse=True)

    result = {}

    # Define windows: L5=5, L10=10, L20=20, season=all
    windows = {
        "L5": 5,
        "L10": 10,
        "L20": 20,
    }

    for window_name, window_size in windows.items():
        if len(non_dnp) < window_size:
            # Insufficient data for this window per D-11
            result[window_name] = None
        else:
            window_games = non_dnp[:window_size]
            hits = sum(1 for g in window_games if g.get(stat, 0) is not None and g.get(stat, 0) > line_value)
            result[window_name] = {
                "rate": round(hits / len(window_games), 2),
                "count": len(window_games),
            }

    # Season window (all non-DNP games)
    if len(non_dnp) < 5:
        result["season"] = None
    else:
        hits = sum(1 for g in non_dnp if g.get(stat, 0) is not None and g.get(stat, 0) > line_value)
        result["season"] = {
            "rate": round(hits / len(non_dnp), 2),
            "count": len(non_dnp),
        }

    return result
