"""
CLI orchestrator for the HoopProphet back-test pipeline.

Wires the back-test engine (Plan 01) and metrics modules (Plan 02) together,
producing structured JSON output (fold metrics, calibration, season
breakdown, ROI, confidence intervals) and Parquet per-prediction output for
ad-hoc analysis.

Usage:
    python -m server.pipeline.backtest_cli --backtest
    python -m server.pipeline.backtest_cli --backtest --parquet-path /path/to/features.parquet
    python -m server.pipeline.backtest_cli --backtest --output-path /path/to/output.parquet
    python -m server.pipeline.backtest_cli --backtest -v
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict

from server.pipeline.backtest import run_backtest
from server.pipeline.backtest_config import (
    BACKTEST_METRICS_DIR,
    BREAKEVEN_THRESHOLD,
)
from server.pipeline.backtest_metrics import (
    compute_confidence_intervals,
    compute_overall_calibration,
    compute_per_stat_calibration,
    compute_roi_metrics,
    compute_season_breakdown,
)

logger = logging.getLogger("server.pipeline.backtest_cli")


def run_backtest_pipeline(
    parquet_path: str = None,
    output_path: str = None,
    min_train_seasons: int = 2,
    metrics_dir: str = None,
    output_dir: str = None,
) -> Dict[str, Any]:
    """Execute the full back-test pipeline: load → backtest → compute metrics → save outputs.

    Args:
        parquet_path: Override default Parquet path.
        output_path: Override Parquet predictions output path (default auto-generated).
        min_train_seasons: Minimum seasons for walk-forward training window.
        metrics_dir: Override metrics log directory (legacy, use output_dir).
        output_dir: Override both output directories (metrics + predictions).

    Returns:
        Dict with artifact_path (None for backtest), metrics_log_path, predictions_path,
        n_folds, seasons.
    """
    start_time = time.time()

    # Resolve output directories
    if output_dir is not None:
        metrics_out = output_dir
    elif metrics_dir is not None:
        metrics_out = metrics_dir
    else:
        metrics_out = BACKTEST_METRICS_DIR

    os.makedirs(metrics_out, exist_ok=True)

    # Step 1: Run back-test
    logger.info("Running back-test...")
    result = run_backtest(parquet_path=parquet_path, min_train_seasons=min_train_seasons)
    predictions_df = result.predictions_df

    # Step 2: Compute all metrics
    logger.info("Computing metrics...")
    overall_cal = compute_overall_calibration(predictions_df)
    per_stat_cal = compute_per_stat_calibration(predictions_df)
    season_breakdown = compute_season_breakdown(predictions_df)
    roi = compute_roi_metrics(predictions_df)
    ci = compute_confidence_intervals(predictions_df)

    # Step 3: Build JSON output structure per D-01
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    # n_predictions_per_stat
    stat_counts: Dict[str, int] = {}
    for stat_val in predictions_df["stat_type"].unique():
        stat_name = str(stat_val)  # Will be resolved to string in future
        count = int((predictions_df["stat_type"] == stat_val).sum())
        stat_counts[stat_name] = count

    output_data = {
        "backtest_metadata": {
            "n_folds": result.n_folds,
            "seasons": result.seasons,
            "min_train_seasons": min_train_seasons,
            "breakeven_threshold": BREAKEVEN_THRESHOLD,
            "vig_description": "Standard -110 vig (52.4% breakeven)",
            "n_total_predictions": len(predictions_df),
            "n_predictions_per_stat": stat_counts,
            "timestamp": timestamp,
        },
        "fold_metrics": result.fold_summaries,
        "season_breakdown": season_breakdown,
        "overall_calibration": overall_cal,
        "per_stat_calibration": per_stat_cal,
        "roi": roi,
        "confidence_intervals": ci,
    }

    # Step 4: Save JSON metrics file
    json_path = os.path.join(metrics_out, f"backtest_metrics_{timestamp}.json")
    with open(json_path, "w") as f:
        json.dump(output_data, f, indent=2)
    logger.info("Saved metrics log to %s", json_path)

    # Step 5: Save Parquet per-prediction output
    if output_path is not None:
        parquet_out_path = output_path
    else:
        parquet_out_path = os.path.join(metrics_out, f"backtest_predictions_{timestamp}.parquet")

    predictions_df.to_parquet(
        parquet_out_path,
        engine="pyarrow",
        compression="snappy",
        index=False,
    )
    logger.info("Saved predictions to %s", parquet_out_path)

    # Step 6: Log summary
    elapsed = time.time() - start_time
    overall_acc = overall_cal.get("accuracy", 0)
    overall_roi_val = roi.get("overall_roi", 0)
    overall_brier = overall_cal.get("brier_score", 0)

    summary = {
        "artifact_path": None,
        "metrics_log_path": json_path,
        "predictions_path": parquet_out_path,
        "n_folds": result.n_folds,
        "seasons": result.seasons,
    }

    logger.info(
        "Back-test complete in %.1fs: %d folds, %d predictions, "
        "accuracy=%.3f, ROI=%+.3f, Brier=%.4f",
        elapsed, result.n_folds, len(predictions_df),
        overall_acc, overall_roi_val, overall_brier,
    )
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="HoopProphet back-test pipeline",
    )
    parser.add_argument(
        "--backtest", action="store_true",
        help="Run the full back-test pipeline (load → backtest → metrics → save)",
    )
    parser.add_argument(
        "--parquet-path", type=str, default=None,
        help="Override path to feature Parquet file",
    )
    parser.add_argument(
        "--output-path", type=str, default=None,
        help="Override path for Parquet predictions output",
    )
    parser.add_argument(
        "--min-train-seasons", type=int, default=2,
        help="Minimum seasons for walk-forward training window (default: 2)",
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="Override output directory for metrics and predictions",
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

    if not args.backtest:
        parser.print_help()
        sys.exit(1)

    try:
        summary = run_backtest_pipeline(
            parquet_path=args.parquet_path,
            output_path=args.output_path,
            min_train_seasons=args.min_train_seasons,
            output_dir=args.output_dir,
        )
        logger.info("Pipeline summary: %s", summary)
        sys.exit(0)
    except FileNotFoundError as e:
        logger.error("Feature Parquet not found: %s", e)
        logger.error("Run feature pipeline first: python -m server.pipeline.ingest --features-only")
        sys.exit(1)
    except Exception:
        logger.exception("Fatal error during back-test")
        sys.exit(1)


if __name__ == "__main__":
    main()
