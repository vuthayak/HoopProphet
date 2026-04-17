"""
CLI orchestrator for the HoopProphet model training pipeline.

Loads Phase 2 feature Parquet, trains a unified LightGBM classifier
across walk-forward temporal splits, calibrates probabilities, logs
metrics, and saves the model artifact.

Usage:
    python -m server.pipeline.train_cli --train
    python -m server.pipeline.train_cli --train --parquet-path /path/to/features.parquet
    python -m server.pipeline.train_cli --train --output-path /path/to/model.joblib
"""

import argparse
import logging
import os
import sys
import time

import numpy as np

from server.pipeline.train_config import MODEL_ARTIFACT_PATH, METRICS_LOG_DIR
from server.pipeline.dataset import load_training_data, get_feature_columns, prepare_datasets
from server.pipeline.splits import walk_forward_split, get_seasons_sorted
from server.pipeline.train import train_model
from server.pipeline.calibrate import calibrate_model
from server.pipeline.artifact import save_artifact
from server.pipeline.metrics import (
    compute_fold_metrics, compute_calibration_curve, save_metrics_log,
)

logger = logging.getLogger("server.pipeline.train_cli")


def run_training_pipeline(
    parquet_path: str = None,
    output_path: str = None,
    min_train_seasons: int = 2,
) -> dict:
    """Execute the full training pipeline: load → split → train → calibrate → save.

    Args:
        parquet_path: Override default Parquet path.
        output_path: Override default model artifact path.
        min_train_seasons: Minimum seasons for walk-forward training window.

    Returns:
        Dict with training summary: best_fold, final_metrics, artifact_path.
    """
    start_time = time.time()

    # Step 1: Load data
    logger.info("Loading feature data...")
    df = load_training_data(parquet_path)
    seasons = get_seasons_sorted(df)
    logger.info("Data: %d rows, %d seasons: %s", len(df), len(seasons), seasons)

    # Step 2: Walk-forward splits
    folds = walk_forward_split(df, min_train_seasons=min_train_seasons)
    logger.info("Walk-forward: %d folds", len(folds))

    # Step 3: Train and calibrate on each fold
    all_fold_metrics = []
    best_fold_idx = 0
    best_brier = float("inf")
    best_artifact_data = None

    for fold_idx, (train_df, val_df) in enumerate(folds):
        fold_num = fold_idx + 1
        train_seasons = sorted(train_df["season"].unique())
        val_season = sorted(val_df["season"].unique())
        logger.info(
            "Fold %d: train=%s (%d rows), val=%s (%d rows)",
            fold_num, train_seasons, len(train_df), val_season, len(val_df),
        )

        # Train LightGBM
        model, train_metrics = train_model(train_df, val_df)

        # Prepare calibration data from validation set
        X_val, y_val = prepare_datasets(val_df)

        # Calibrate
        calibrator, cal_info = calibrate_model(model, X_val, y_val.values)
        logger.info(
            "Fold %d: calibrated with %s (%s)",
            fold_num, cal_info["calibration_method"], cal_info["calibration_reason"],
        )

        # Compute validated predictions
        y_pred = calibrator.predict_proba(X_val)[:, 1]

        # Log fold metrics (MODL-07)
        fold_metrics = compute_fold_metrics(
            y_true=y_val.values,
            y_pred=y_pred,
            fold=fold_num,
            train_seasons=train_seasons,
            val_season=val_season[0] if len(val_season) == 1 else str(val_season),
            n_train=len(train_df),
            n_val=len(val_df),
            calibration_method=cal_info["calibration_method"],
            n_calibration_samples=cal_info["n_calibration_samples"],
        )
        all_fold_metrics.append(fold_metrics)

        # Track best fold by Brier score
        if fold_metrics["brier_score"] < best_brier:
            best_brier = fold_metrics["brier_score"]
            best_fold_idx = fold_idx
            best_artifact_data = {
                "model": model,
                "calibrator": calibrator,
                "feature_columns": get_feature_columns(df),
                "metrics": {"fold_metrics": all_fold_metrics, "best_fold": fold_num},
            }

    # Step 4: Train final model on ALL data for production serving
    logger.info("Training final production model on all data...")
    # Use last fold's validation set for final calibration reference
    # The production model trains on all available data
    final_model, final_metrics = train_model(df, early_stopping=False)

    # For calibration: use the last season as calibration set
    last_season = seasons[-1]
    cal_df = df[df["season"] == last_season]
    X_cal, y_cal = prepare_datasets(cal_df)

    final_calibrator, final_cal_info = calibrate_model(final_model, X_cal, y_cal.values)

    # Compute calibration curve on the calibration set (MODL-07)
    y_pred_cal = final_calibrator.predict_proba(X_cal)[:, 1]
    cal_curve = compute_calibration_curve(y_cal.values, y_pred_cal)

    feature_columns = get_feature_columns(df)

    # Step 5: Save artifact (MODL-05)
    final_all_metrics = all_fold_metrics + [{
        "fold": "final",
        "train_seasons": seasons,
        "n_train": len(df),
        "n_calibration_samples": len(cal_df),
        "calibration_method": final_cal_info["calibration_method"],
        "log_loss": final_metrics.get("train_log_loss", 0),
        "brier_score": final_cal_info.get("brier_score_after", 0),
    }]

    artifact_path = save_artifact(
        model=final_model,
        calibrator=final_calibrator,
        feature_columns=feature_columns,
        metrics={"fold_metrics": final_all_metrics, "best_fold": best_fold_idx + 1},
        output_path=output_path,
    )

    # Step 6: Save metrics log (MODL-07)
    log_path = save_metrics_log(
        all_fold_metrics=final_all_metrics,
        calibration_curve_data=cal_curve,
        output_dir=METRICS_LOG_DIR,
    )

    elapsed = time.time() - start_time
    summary = {
        "artifact_path": artifact_path,
        "metrics_log_path": log_path,
        "n_folds": len(folds),
        "best_fold": best_fold_idx + 1,
        "best_brier": round(best_brier, 6),
        "final_calibration_method": final_cal_info["calibration_method"],
        "elapsed_seconds": round(elapsed, 1),
    }

    logger.info("Training complete in %.1fs: %s", elapsed, summary)
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="HoopProphet model training pipeline",
    )
    parser.add_argument(
        "--train", action="store_true",
        help="Run the full training pipeline (load → split → train → calibrate → save)",
    )
    parser.add_argument(
        "--parquet-path", type=str, default=None,
        help="Override path to feature Parquet file",
    )
    parser.add_argument(
        "--output-path", type=str, default=None,
        help="Override path for model artifact output",
    )
    parser.add_argument(
        "--min-train-seasons", type=int, default=2,
        help="Minimum seasons for walk-forward training window (default: 2)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable DEBUG logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        level=logging.DEBUG if args.verbose else logging.INFO,
    )

    if not args.train:
        parser.print_help()
        sys.exit(1)

    try:
        summary = run_training_pipeline(
            parquet_path=args.parquet_path,
            output_path=args.output_path,
            min_train_seasons=args.min_train_seasons,
        )
        logger.info("Pipeline summary: %s", summary)
        sys.exit(0)
    except FileNotFoundError as e:
        logger.error("Feature Parquet not found: %s", e)
        logger.error("Run feature pipeline first: python -m server.pipeline.ingest --features-only")
        sys.exit(1)
    except Exception:
        logger.exception("Fatal error during training")
        sys.exit(1)


if __name__ == "__main__":
    main()