"""
Prediction serving service — core prop prediction engine per D-13, D-14.

- get_default_lines: median of last 20 non-DNP games, rounded to 0.5
- get_predictions: ML predictions from pre-computed features.parquet
- get_top_props: top 5 props ranked by probability
- get_player_props: combined output with hit rates
"""

import logging
import math
from typing import Any, Dict, List, Optional

import pandas as pd

from server.pipeline.artifact import predict_proba
from server.pipeline.feature_config import (
    ALL_TARGET_STATS,
    PRIMARY_STATS,
    STAT_TYPE_MAP,
    COMBO_STATS,
    PARQUET_PATH,
)
from server.services.player_service import get_player_game_logs
from server.services.hitrate_service import get_hit_rates

logger = logging.getLogger(__name__)


def _round_half(value: float) -> float:
    """Round to nearest 0.5 increment (sportsbook-style).

    Examples: 24.3→24.5, 24.7→24.5, 25.0→25.0, 24.25→24.5, 24.75→24.5
    """
    return int(value * 2 + 0.5) / 2


def _round_percent(value: float) -> float:
    """Round probability to nearest 1% (0.01) per D-08.

    Prevents model reconstruction attack and avoids over-precision.
    """
    return round(value, 2)


def get_default_lines(
    player_id: int,
    seasons: Optional[list[str]] = None,
) -> dict[str, float]:
    """Compute default stat lines for a player per D-01, D-02, D-03, D-04.

    Uses median of last 20 non-DNP games, rounded to 0.5.
    Excludes stats where player averages <1.0 per game (D-04).
    Requires minimum 5 non-DNP games (D-02).
    Combo stats (PRA, PA, PR) computed from component stat sums (D-03).

    Args:
        player_id: NBA player ID.
        seasons: Optional list of season strings to filter.

    Returns:
        Dict of stat -> line_value for stats that meet minimum thresholds.
        Only PRIMARY_STATS and COMBO_STATS are returned.

    Raises:
        ValueError: If player has no game logs.
    """
    game_logs = get_player_game_logs(player_id, seasons=seasons)

    if not game_logs:
        raise ValueError(f"Player not found: {player_id}")

    # Filter to non-DNP games
    non_dnp = [g for g in game_logs if g.get("is_dnp", 1) == 0]

    if len(non_dnp) < 5:
        raise ValueError(f"Player not found: {player_id}")

    # Sort by game_date DESC
    non_dnp = sorted(non_dnp, key=lambda g: g.get("game_date", ""), reverse=True)

    # Use last 20 non-DNP games for median calculation
    last_20 = non_dnp[:20]

    lines = {}

    # Process primary stats
    for stat in PRIMARY_STATS:
        if stat == "plus_minus":
            # plus_minus can be negative, handle specially
            values = [g.get(stat, 0) or 0 for g in last_20]
        else:
            values = [g.get(stat, 0) or 0 for g in last_20]

        # Check minimum games (at least 5)
        if len(values) < 5:
            continue

        # Check minimum volume: average >= 1.0 per D-04
        avg = sum(values) / len(values)
        if avg < 1.0:
            continue

        median_val = sorted(values)[len(values) // 2]
        lines[stat] = _round_half(median_val)

    # Process combo stats (PRA, PA, PR) per D-03
    for combo_stat, component_stats in COMBO_STATS.items():
        # Compute combo sums for each game
        combo_sums = []
        for g in last_20:
            combo_val = sum(g.get(s, 0) or 0 for s in component_stats)
            combo_sums.append(combo_val)

        if len(combo_sums) < 5:
            continue

        # Check minimum volume
        avg = sum(combo_sums) / len(combo_sums)
        if avg < 1.0:
            continue

        median_val = sorted(combo_sums)[len(combo_sums) // 2]
        lines[combo_stat] = _round_half(median_val)

    return lines


def get_predictions(
    player_id: int,
    model_artifact: Optional[Dict[str, Any]],
) -> List[dict]:
    """Get ML predictions for a player's props per D-13, D-14, D-08.

    Reads pre-computed features from features.parquet filtered by player_id.
    Returns empty list if artifact is None (D-10) or player not in features (D-14).

    Args:
        player_id: NBA player ID.
        model_artifact: Loaded model artifact dict, or None for graceful degradation.

    Returns:
        List of prop dicts: [{stat, line, probability, direction}, ...]
        Empty list if no artifact or player not in features.parquet.
    """
    if model_artifact is None:
        # Graceful degradation per D-10
        return []

    try:
        df = pd.read_parquet(PARQUET_PATH)
    except Exception:
        # features.parquet doesn't exist or can't be read — D-14 graceful skip
        logger.warning("Could not read features.parquet at %s", PARQUET_PATH)
        return []

    # Filter to player
    player_df = df[df["player_id"] == player_id]

    if player_df.empty:
        # Player not in features.parquet per D-14
        return []

    # Sort by game_date descending and get most recent row per stat_type
    player_df = player_df.sort_values("game_date", ascending=False)

    # Get default lines for this player to know which stats to predict
    try:
        default_lines = get_default_lines(player_id)
    except ValueError:
        return []

    predictions = []

    for stat, line in default_lines.items():
        stat_type = STAT_TYPE_MAP.get(stat)
        if stat_type is None:
            continue

        # Get feature row for this stat_type (most recent)
        stat_rows = player_df[player_df["stat_type"] == stat_type]
        if stat_rows.empty:
            continue

        feature_row = stat_rows.iloc[0:1]  # Single row DataFrame

        try:
            proba = predict_proba(model_artifact, feature_row)
            # proba is numpy array, get first element
            if hasattr(proba, "__iter__"):
                proba = float(proba[0])
            else:
                proba = float(proba)
        except Exception as e:
            logger.warning("predict_proba failed for player %d stat %s: %s", player_id, stat, e)
            continue

        predictions.append({
            "stat": stat,
            "line": line,
            "probability": _round_percent(proba),
            "direction": "over",
        })

    return predictions


def get_top_props(
    player_id: int,
    model_artifact: Optional[Dict[str, Any]],
    n: int = 5,
) -> List[dict]:
    """Get top N props ranked by model probability per D-05, D-06.

    Args:
        player_id: NBA player ID.
        model_artifact: Loaded model artifact, or None.
        n: Maximum number of props to return (default 5, per D-06).

    Returns:
        List of top prop dicts sorted by probability descending.
    """
    predictions = get_predictions(player_id, model_artifact)

    # Sort by probability descending per D-05
    predictions = sorted(predictions, key=lambda p: p["probability"], reverse=True)

    return predictions[:n]


def get_player_props(
    player_id: int,
    model_artifact: Optional[Dict[str, Any]],
    seasons: Optional[list[str]] = None,
) -> dict:
    """Get combined player props data per D-07.

    Returns default lines, top props with ML probabilities, and hit rates.

    Args:
        player_id: NBA player ID.
        model_artifact: Loaded model artifact, or None for graceful degradation.
        seasons: Optional list of season strings.

    Returns:
        Dict with player_id, default_lines, and top_props (each with hit_rates).
        Returns empty top_props when model_artifact is None (D-10).
    """
    try:
        default_lines = get_default_lines(player_id, seasons=seasons)
    except ValueError:
        default_lines = {}

    predictions = get_predictions(player_id, model_artifact)
    top_props = sorted(predictions, key=lambda p: p["probability"], reverse=True)[:5]

    # Add hit rates to each top prop
    enriched_props = []
    for prop in top_props:
        stat = prop["stat"]
        line = prop["line"]

        try:
            hit_rates = get_hit_rates(player_id, stat, line, seasons=seasons)
        except ValueError:
            hit_rates = {"L5": None, "L10": None, "L20": None, "season": None}

        enriched_props.append({
            "stat": stat,
            "line": line,
            "probability": prop["probability"],
            "direction": prop["direction"],
            "hit_rates": hit_rates,
        })

    return {
        "player_id": player_id,
        "default_lines": default_lines,
        "top_props": enriched_props,
    }
