import logging
from typing import List, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


def get_seasons_sorted(df: pd.DataFrame) -> List[str]:
    """Return unique seasons in chronological order.

    Expects season column in 'YYYY-YY' format (e.g. '2023-24').
    Sorts by the start year so seasons are in temporal order.
    """
    seasons = sorted(df["season"].unique(), key=lambda s: int(s.split("-")[0]))
    logger.info("Found %d seasons: %s", len(seasons), seasons)
    return seasons


def walk_forward_split(
    df: pd.DataFrame,
    min_train_seasons: int = 2,
) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
    """Generate walk-forward train/validation splits.

    Each fold trains on the first N seasons and validates on season N+1.
    Expanding window: each subsequent fold adds one more training season.

    Args:
        df: Long-format DataFrame with 'season' column.
        min_train_seasons: Minimum number of seasons for the training set.
            Default 2 means the first fold trains on seasons 1+2 and
            validates on season 3.

    Returns:
        List of (train_df, val_df) tuples, one per fold.

    Example with seasons [2020-21, 2021-22, 2022-23, 2023-24, 2024-25]:
        Fold 1: train=[2020-21, 2021-22], val=[2022-23]
        Fold 2: train=[2020-21, 2021-22, 2022-23], val=[2023-24]
        Fold 3: train=[2020-21,..., 2023-24], val=[2024-25]
    """
    seasons = get_seasons_sorted(df)
    if len(seasons) < min_train_seasons + 1:
        raise ValueError(
            f"Need at least {min_train_seasons + 1} seasons for walk-forward "
            f"split, got {len(seasons)}"
        )

    folds = []
    for i in range(min_train_seasons, len(seasons)):
        train_seasons = seasons[:i]
        val_season = seasons[i]
        train_df = df[df["season"].isin(train_seasons)].copy()
        val_df = df[df["season"] == val_season].copy()

        logger.info(
            "Fold %d: train_seasons=%s, val_season=%s, train_rows=%d, val_rows=%d",
            len(folds) + 1, train_seasons, val_season, len(train_df), len(val_df),
        )
        folds.append((train_df, val_df))

    logger.info("Generated %d walk-forward folds", len(folds))
    return folds