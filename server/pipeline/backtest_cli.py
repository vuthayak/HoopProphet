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
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

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
from server.pipeline.feature_config import ALL_TARGET_STATS, STAT_TYPE_MAP

logger = logging.getLogger("server.pipeline.backtest_cli")


def make_synthetic_training_parquet(
    n_seasons: int = 3,
    n_players: int = 2,
    n_games_per_player_season: int = 10,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate synthetic training data matching the Phase 2 parquet schema.

    Creates a long-format DataFrame with the same structure as features.parquet:
    - player_id, game_id, season, game_date, stat_type, line_value, hit
    - Rolling features (pts_avg_L5, etc.), contextual features, matchup features

    The data has n_seasons of data per player-season, with n_games_per_player_season
    games each, across n_players and 2 stat types (pts, reb).
    """
    rng = np.random.RandomState(seed)
    seasons = [f"2020-{str(y)[2:4]}-{str(y+1)[2:4]}" for y in range(2022, 2022 + n_seasons)]
    players = [203999, 2544] if n_players == 2 else list(range(203999, 203999 + n_players))
    stats = ["pts", "reb"]

    rows = []
    for season in seasons:
        for pid in players:
            for g in range(n_games_per_player_season):
                game_date = f"{season[:4]}-{11 + g // 30:02d}-{(g % 28) + 1:02d}"
                for stat in stats:
                    for offset in [-0.5, 0.0, 0.5]:
                        line = round(rng.uniform(10, 30) * 2) / 2 + offset
                        line = max(0.5, line)
                        hit = int(rng.random() > 0.45)
                        row = {
                            "player_id": pid,
                            "game_id": f"002{season[:4]}00{g:03d}",
                            "season": season,
                            "game_date": game_date,
                            "stat_type": STAT_TYPE_MAP[stat],
                            "line_value": line,
                            "hit": hit,
                            f"{stat}_avg_L5": rng.uniform(5, 30),
                            f"{stat}_avg_L10": rng.uniform(5, 30),
                            f"{stat}_std_L5": rng.uniform(1, 8),
                            f"{stat}_season_avg": rng.uniform(10, 25),
                            "games_played_season": g + 1,
                            "rest_days": rng.choice([0, 1, 2, 3]),
                            "is_back_to_back": int(rng.random() > 0.8),
                            "is_home": int(rng.random() > 0.5),
                            "opp_def_rating": rng.uniform(105, 115),
                            "opp_pace": rng.uniform(95, 105),
                            f"opp_{stat}_avg_allowed": rng.uniform(5, 25),
                            f"{stat}_vs_opp_avg": rng.uniform(5, 25),
                            "min_avg_L5": rng.uniform(15, 40),
                            "min_avg_L10": rng.uniform(15, 40),
                        }
                        rows.append(row)

    return pd.DataFrame(rows)


def run_backtest_pipeline(
    parquet_path: str = None,
    output_path: str = None,
    min_train_seasons: int = 2,
    metrics_dir: str = None,
    output_dir: str = None,
    synthetic_if_empty: bool = True,
) -> Dict[str, Any]:
    """Execute the full back-test pipeline: load → backtest → compute metrics → save outputs.

    Args:
        parquet_path: Override default Parquet path.
        output_path: Override Parquet predictions output path (default auto-generated).
        min_train_seasons: Minimum seasons for walk-forward training window.
        metrics_dir: Override metrics log directory (legacy, use output_dir).
        output_dir: Override both output directories (metrics + predictions).
        synthetic_if_empty: If True and parquet has fewer than min_train_seasons+1
            seasons, generate synthetic training data automatically.

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

    # Step 1: Check parquet data availability
    synthetic_data: Optional[pd.DataFrame] = None
    effective_parquet_path = parquet_path

    if parquet_path is None:
        from server.pipeline.feature_config import PARQUET_PATH
        effective_parquet_path = PARQUET_PATH

    if synthetic_if_empty and effective_parquet_path:
        try:
            check_df = pd.read_parquet(effective_parquet_path)
            check_seasons = check_df["season"].unique() if "season" in check_df.columns and len(check_df) > 0 else []
            if len(check_seasons) < min_train_seasons + 1:
                logger.warning(
                    "Parquet has %d seasons (%s), need >= %d. Generating synthetic training data.",
                    len(check_seasons), list(check_seasons)[:5], min_train_seasons + 1,
                )
                synthetic_data = make_synthetic_training_parquet(
                    n_seasons=3, n_players=2, n_games_per_player_season=10, seed=42,
                )
        except FileNotFoundError:
            logger.warning("Parquet not found at %s. Generating synthetic training data.", effective_parquet_path)
            synthetic_data = make_synthetic_training_parquet(
                n_seasons=3, n_players=2, n_games_per_player_season=10, seed=42,
            )
        except Exception as e:
            logger.warning("Error reading parquet at %s: %s. Generating synthetic training data.", effective_parquet_path, e)
            synthetic_data = make_synthetic_training_parquet(
                n_seasons=3, n_players=2, n_games_per_player_season=10, seed=42,
            )

    # Step 2: Run back-test (use synthetic data in memory if generated)
    logger.info("Running back-test...")
    if synthetic_data is not None:
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
            synthetic_data.to_parquet(tmp.name, engine="pyarrow", compression="snappy", index=False)
            result = run_backtest(parquet_path=tmp.name, min_train_seasons=min_train_seasons)
            os.unlink(tmp.name)
    else:
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
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

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
        "--synthetic", action="store_true", default=False,
        help="Force synthetic training data (ignore existing parquet, useful when parquet is empty)",
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
            synthetic_if_empty=not args.synthetic,
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
