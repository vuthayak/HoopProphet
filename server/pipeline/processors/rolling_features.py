import logging

import pandas as pd

from server.pipeline.feature_config import (
    COMBO_STATS,
    PRIMARY_STATS,
    SECONDARY_STATS,
    STAT_COLS,
    WINDOWS_PRIMARY,
    WINDOWS_SECONDARY,
)

logger = logging.getLogger(__name__)


def compute_rolling_features(played_df: pd.DataFrame) -> pd.DataFrame:
    """Compute rolling and season-to-date features with a temporal guard."""
    logger.info("Computing rolling features for %d rows", len(played_df))

    df = played_df.sort_values(["player_id", "game_date"]).copy()

    # Add raw combo stat columns before rolling calculations.
    for combo_name, component_stats in COMBO_STATS.items():
        df[combo_name] = df[component_stats].sum(axis=1)

    for stat in STAT_COLS:
        windows = WINDOWS_PRIMARY if stat in PRIMARY_STATS else WINDOWS_SECONDARY
        for window in windows:
            min_periods = 1 if window in [5, 10] else 10
            grouped = df.groupby("player_id")[stat]
            df[f"{stat}_avg_L{window}"] = (
                grouped.rolling(window, min_periods=min_periods)
                .mean()
                .reset_index(level=0, drop=True)
            )
            df[f"{stat}_std_L{window}"] = (
                grouped.rolling(window, min_periods=min_periods)
                .std()
                .reset_index(level=0, drop=True)
            )

    for combo_name in COMBO_STATS:
        for window in WINDOWS_PRIMARY:
            min_periods = 1 if window in [5, 10] else 10
            grouped = df.groupby("player_id")[combo_name]
            df[f"{combo_name}_avg_L{window}"] = (
                grouped.rolling(window, min_periods=min_periods)
                .mean()
                .reset_index(level=0, drop=True)
            )
            df[f"{combo_name}_std_L{window}"] = (
                grouped.rolling(window, min_periods=min_periods)
                .std()
                .reset_index(level=0, drop=True)
            )

    for stat in PRIMARY_STATS:
        df[f"{stat}_season_avg"] = (
            df.groupby(["player_id", "season"])[stat]
            .expanding(min_periods=1)
            .mean()
            .reset_index(level=[0, 1], drop=True)
        )

    df["games_played_season"] = df.groupby(["player_id", "season"]).cumcount() + 1

    rolling_cols = [
        c
        for c in df.columns
        if "_avg_L" in c or "_std_L" in c or "_season_avg" in c or c == "games_played_season"
    ]
    df[rolling_cols] = df.groupby("player_id")[rolling_cols].shift(1)

    logger.info(
        "Completed rolling feature computation: total columns=%d, rolling columns=%d",
        len(df.columns),
        len(rolling_cols),
    )
    return df
