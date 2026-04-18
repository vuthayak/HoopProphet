"""Synthetic predictions DataFrame factory for backtest metrics tests."""

import numpy as np
import pandas as pd


def make_predictions_df(
    *,
    rng: np.random.Generator,
    seasons: list[str] | None = None,
    stat_types: list[int] | None = None,
    n_rows: int = 200,
) -> pd.DataFrame:
    """Build a synthetic per-prediction DataFrame for testing.

    Args:
        rng: numpy random generator (seeded by caller for reproducibility)
        seasons: list of season strings to include (default ["2022-23", "2023-24", "2024-25"])
        stat_types: list of stat_type integers to include (default [0, 1, 2])
        n_rows: total number of prediction rows

    Returns:
        DataFrame with all required columns matching the backtest.py contract
    """
    if seasons is None:
        seasons = ["2022-23", "2023-24", "2024-25"]
    if stat_types is None:
        stat_types = [0, 1, 2]  # pts, reb, ast

    n_seasons = len(seasons)
    n_stats = len(stat_types)

    rows = []
    for i in range(n_rows):
        season = seasons[i % n_seasons]
        stat_type = stat_types[i % n_stats]

        # Generate predicted_proba with spread across the range [0.35, 0.85]
        # to test both below and above breakeven (0.524)
        base = 0.35 + (i % 50) * 0.01
        predicted_proba = float(np.clip(base + rng.uniform(-0.05, 0.05), 0.30, 0.90))

        # Generate hit: higher proba → higher hit rate
        hit_prob = predicted_proba
        hit = 1 if rng.random() < hit_prob else 0

        rows.append(
            {
                "player_id": 1000 + i,
                "game_id": f"00{i:04d}",
                "season": season,
                "game_date": f"2024-01-{(i % 28) + 1:02d}",
                "stat_type": stat_type,
                "line_value": rng.uniform(10.0, 30.0),
                "hit": hit,
                "predicted_proba": round(predicted_proba, 4),
                "fold": (i % 3) + 1,
                "train_seasons": "2021-22,2022-23" if season != "2021-22" else "2020-21,2021-22",
            }
        )

    return pd.DataFrame(rows)


def make_perfectly_calibrated_df(rng: np.random.Generator) -> pd.DataFrame:
    """DataFrame where predicted_proba exactly matches observed hit rate.

    Each bin of predicted probability has observed hit rate equal to the prediction,
    giving ECE ≈ 0. Uses 100 rows per bin with deterministic hit assignment so
    observed hit rate is EXACTLY equal to predicted probability.
    """
    rows = []
    n_per_bin = 100
    # Create 6 bins from 0.40 to 0.90
    for prob in np.linspace(0.40, 0.90, 6):
        n_hits = int(round(prob * n_per_bin))  # exact hit count for this bin
        hit_array = ([1] * n_hits) + ([0] * (n_per_bin - n_hits))
        rng.shuffle(hit_array)  # shuffle so order doesn't give it away
        prob_rounded = round(float(prob), 4)
        for hit in hit_array:
            rows.append(
                {
                    "player_id": int(rng.integers(1000, 9999)),
                    "game_id": f"00{int(rng.integers(1000, 9999)):04d}",
                    "season": "2023-24",
                    "game_date": "2024-01-15",
                    "stat_type": 0,
                    "line_value": 20.0,
                    "hit": hit,
                    "predicted_proba": prob_rounded,
                    "fold": 1,
                    "train_seasons": "2022-23",
                }
            )
    return pd.DataFrame(rows)


def make_miscalibrated_df(rng: np.random.Generator) -> pd.DataFrame:
    """DataFrame where high predictions underperform and low predictions overperform.

    Creates systematic miscalibration with ECE > 0.
    """
    rows = []
    for i in range(300):
        # Invert: high proba → low hit rate
        prob = 0.40 + (i % 60) * 0.01
        prob = min(prob, 0.95)
        hit_prob = 1.0 - prob  # inverted
        hit = 1 if rng.random() < hit_prob else 0
        rows.append(
            {
                "player_id": 1000 + i,
                "game_id": f"00{i:04d}",
                "season": "2023-24",
                "game_date": "2024-01-15",
                "stat_type": 0,
                "line_value": 20.0,
                "hit": hit,
                "predicted_proba": round(float(prob), 4),
                "fold": 1,
                "train_seasons": "2022-23",
            }
        )
    return pd.DataFrame(rows)
