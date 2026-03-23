import logging

import pandas as pd

from server.pipeline.feature_config import (
    ALL_TARGET_STATS,
    COMBO_STATS,
    N_THRESHOLD_LINES,
    PRIMARY_STATS,
    STAT_COLS,
    STAT_TYPE_MAP,
)

logger = logging.getLogger(__name__)


def generate_targets(wide_df: pd.DataFrame) -> pd.DataFrame:
    """Convert wide feature rows into long-format target rows."""
    df = wide_df.sort_values(["player_id", "game_date"]).copy()

    id_cols = ["player_id", "game_id", "season", "game_date"]
    exclude_cols = set(STAT_COLS) | set(COMBO_STATS.keys()) | {
        "matchup",
        "wl",
        "is_dnp",
        "opp_abbr",
        "opp_team_id",
        "player_team_id",
        "game_date_dt",
    }
    feature_cols = [c for c in df.columns if c not in id_cols and c not in exclude_cols]

    for stat in ALL_TARGET_STATS:
        median_col = f"_line_median_{stat}"
        df[median_col] = (
            df.groupby("player_id")[stat]
            .rolling(20, min_periods=5)
            .median()
            .reset_index(level=0, drop=True)
        )
        df[median_col] = df.groupby("player_id")[median_col].shift(1)

    half_span = N_THRESHOLD_LINES // 2
    long_frames = []
    for stat in ALL_TARGET_STATS:
        median_col = f"_line_median_{stat}"
        stat_df = df.dropna(subset=[median_col]).copy()
        if stat_df.empty:
            continue
        base_line = (stat_df[median_col] * 2).round() / 2

        for offset in range(-half_span, half_span + 1):
            line_val = (base_line + offset).clip(lower=0.5)
            row_df = stat_df[id_cols + feature_cols].copy()
            row_df["stat_type"] = STAT_TYPE_MAP[stat]
            row_df["line_value"] = line_val
            row_df["hit"] = (stat_df[stat] > line_val).astype(int)
            long_frames.append(row_df)

    if not long_frames:
        empty_cols = id_cols + feature_cols + ["stat_type", "line_value", "hit"]
        return pd.DataFrame(columns=empty_cols)

    long_df = pd.concat(long_frames, ignore_index=True)
    long_df["stat_type"] = long_df["stat_type"].astype(int)
    long_df["hit"] = long_df["hit"].astype(int)

    logger.info("Generated %d long-format target rows", len(long_df))
    logger.info("Target rows by stat_type: %s", long_df["stat_type"].value_counts().to_dict())
    logger.info("Primary stats configured: %s", ",".join(PRIMARY_STATS))

    return long_df
