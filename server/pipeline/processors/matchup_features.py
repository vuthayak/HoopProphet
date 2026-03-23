import logging

import pandas as pd

from server.pipeline.feature_config import PRIMARY_STATS
from server.pipeline.processors.contextual_features import _extract_opponent

logger = logging.getLogger(__name__)

PREV_SEASON = {
    "2020-21": None,
    "2021-22": "2020-21",
    "2022-23": "2021-22",
    "2023-24": "2022-23",
    "2024-25": "2023-24",
}


def compute_matchup_features(df: pd.DataFrame, all_game_logs: pd.DataFrame) -> pd.DataFrame:
    """Compute per-game historical matchup averages within a 2-season window."""
    logger.info("Computing matchup features for %d rows", len(df))

    out = df.copy()
    all_logs = all_game_logs.copy()

    for stat in PRIMARY_STATS:
        out[f"matchup_avg_{stat}"] = pd.NA

    all_logs["game_date"] = pd.to_datetime(all_logs["game_date"])
    all_logs["opp_abbr"] = all_logs["matchup"].apply(_extract_opponent)
    all_logs["opp_team_id"] = all_logs["opp_abbr"].map(
        dict(zip(out["opp_abbr"].dropna(), out["opp_team_id"].dropna()))
    )
    all_logs = all_logs[all_logs["is_dnp"] == 0].copy()

    current = out[["game_id", "player_id", "opp_team_id", "season", "game_date"]].copy()
    current["game_date"] = pd.to_datetime(current["game_date"])
    current["prev_season"] = current["season"].map(PREV_SEASON)

    hist_cols = ["player_id", "opp_team_id", "season", "game_date", *PRIMARY_STATS]
    history = all_logs[hist_cols].copy()

    merged = current.merge(
        history,
        on=["player_id", "opp_team_id"],
        how="left",
        suffixes=("_curr", "_hist"),
    )
    merged = merged[
        (merged["game_date_hist"] < merged["game_date_curr"])
        & (
            (merged["season_hist"] == merged["season_curr"])
            | (merged["season_hist"] == merged["prev_season"])
        )
    ]

    matchup_avg = merged.groupby("game_id")[PRIMARY_STATS].mean().add_prefix("matchup_avg_")
    out = out.merge(matchup_avg, on="game_id", how="left", suffixes=("", "_computed"))

    for stat in PRIMARY_STATS:
        col = f"matchup_avg_{stat}"
        computed_col = f"{col}_computed"
        if computed_col in out.columns:
            out[col] = out[computed_col]
            out.drop(columns=[computed_col], inplace=True)

    logger.info("Completed matchup features: added %d columns", len(PRIMARY_STATS))
    return out
