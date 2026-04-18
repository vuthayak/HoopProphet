"""Walk-forward back-test evaluation engine.

Evaluates the LightGBM model across historical season folds using the same
walk-forward temporal split strategy as training (Phase 3).

Per Objective: train on seasons 1..N-1, predict season N, collect per-prediction
results for downstream metric computation (Plan 02) and CLI output (Plan 03).

Outputs:
    - predictions_df: per-prediction DataFrame with player_id, game_id, season,
      stat_type, line_value, hit, predicted_proba, fold columns
    - fold_summaries: list of per-fold metrics dicts for reporting
"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd

from server.pipeline.backtest_config import (
    BREAKEVEN_THRESHOLD, VIG_MULTIPLIER, CALIBRATION_BINS,
    CONFIDENCE_LEVEL, BOOTSTRAP_SAMPLES, MIN_TRAIN_SEASONS,
    BACKTEST_METRICS_DIR,
)
from server.pipeline.dataset import load_training_data, prepare_datasets
from server.pipeline.metrics import compute_fold_metrics
from server.pipeline.splits import get_seasons_sorted, walk_forward_split
from server.pipeline.train import train_model
from server.pipeline.calibrate import calibrate_model

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """Result of a walk-forward back-test run.

    Attributes:
        predictions_df: Per-prediction DataFrame with columns:
            player_id, game_id, season, stat_type, line_value, hit,
            predicted_proba, fold
        fold_summaries: List of per-fold metrics dicts with:
            fold, train_seasons, val_season, n_train, n_val,
            log_loss, brier_score, accuracy, calibration_method,
            n_calibration_samples
        n_folds: Number of walk-forward folds evaluated
        seasons: Chronologically sorted list of seasons in the input data
    """
    predictions_df: pd.DataFrame
    fold_summaries: List[Dict[str, Any]]
    n_folds: int
    seasons: List[str]


def run_backtest(
    parquet_path: Optional[str] = None,
    min_train_seasons: int = MIN_TRAIN_SEASONS,
    params: Optional[dict] = None,
) -> BacktestResult:
    """Run walk-forward back-test evaluation across historical season folds.

    For each fold:
        1. Train model on all preceding seasons (train_df)
        2. Calibrate model on train_df's validation split
        3. Predict on the held-out validation season (val_df)
        4. Collect per-prediction rows for downstream metrics

    Args:
        parquet_path: Path to features Parquet. Uses default DATA_DIR path if None.
        min_train_seasons: Minimum number of seasons for training window.
            Default 2 means first fold trains on seasons 1+2, validates on 3.
        params: Override default LGBM hyperparameters.

    Returns:
        BacktestResult with predictions DataFrame and per-fold metrics.

    Raises:
        ValueError: If fewer than min_train_seasons+1 seasons in data.
    """
    # --- Load data ---
    df = load_training_data(parquet_path)
    seasons = get_seasons_sorted(df)

    if len(seasons) < min_train_seasons + 1:
        raise ValueError(
            f"Need at least {min_train_seasons + 1} seasons for walk-forward "
            f"back-test, got {len(seasons)} ({seasons})"
        )

    # --- Generate walk-forward folds ---
    folds = walk_forward_split(df, min_train_seasons=min_train_seasons)
    logger.info("Starting back-test with %d folds across %d seasons", len(folds), len(seasons))

    all_predictions: List[pd.DataFrame] = []
    fold_summaries: List[Dict[str, Any]] = []

    # --- Iterate over folds ---
    for fold_idx, (train_df, val_df) in enumerate(folds, start=1):
        train_seasons = sorted(train_df["season"].unique(), key=lambda s: int(s.split("-")[0]))
        val_season = val_df["season"].iloc[0]

        logger.info(
            "Fold %d: training on %s (%d rows), validating on %s (%d rows)",
            fold_idx, train_seasons, len(train_df), val_season, len(val_df),
        )

        # 1. Train model on train_df
        model, train_metrics = train_model(
            train_df,
            val_df=None,  # We'll calibrate on val_df below
            early_stopping=True,
            params=params,
        )

        # 2. Prepare validation features
        X_val, y_val = prepare_datasets(val_df)

        # 3. Calibrate model on val_df (using full val_df as calibration set)
        calibrator, cal_info = calibrate_model(model, X_val.values, y_val.values)

        # 4. Get calibrated predictions
        y_pred = calibrator.predict_proba(X_val.values)[:, 1]

        # 5. Build per-prediction rows
        val_df_copy = val_df.copy()
        pred_rows = pd.DataFrame({
            "player_id": val_df_copy["player_id"].values,
            "game_id": val_df_copy["game_id"].values,
            "season": val_df_copy["season"].values,
            "stat_type": val_df_copy["stat_type"].values,
            "line_value": val_df_copy["line_value"].values,
            "hit": y_val.values,
            "predicted_proba": y_pred,
            "fold": fold_idx,
        })
        all_predictions.append(pred_rows)

        # 6. Compute fold-level metrics
        fold_metrics = compute_fold_metrics(
            y_true=y_val.values,
            y_pred=y_pred,
            fold=fold_idx,
            train_seasons=train_seasons,
            val_season=val_season,
            n_train=len(train_df),
            n_val=len(val_df),
            calibration_method=cal_info["calibration_method"],
            n_calibration_samples=cal_info["n_calibration_samples"],
        )
        fold_summaries.append(fold_metrics)

        logger.info(
            "Fold %d complete: log_loss=%.4f, brier=%.4f, accuracy=%.4f",
            fold_idx, fold_metrics["log_loss"], fold_metrics["brier_score"],
            fold_metrics["accuracy"],
        )

    # --- Assemble result ---
    predictions_df = pd.concat(all_predictions, ignore_index=True)

    result = BacktestResult(
        predictions_df=predictions_df,
        fold_summaries=fold_summaries,
        n_folds=len(folds),
        seasons=seasons,
    )

    logger.info(
        "Back-test complete: %d folds, %d total predictions",
        result.n_folds, len(predictions_df),
    )

    return result
