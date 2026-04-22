"""
FastAPI router for backtest endpoints — per D-17.

GET /api/backtest/summary     → overall accuracy, Brier score, ROI
GET /api/backtest/seasons     → per-season breakdown with games, accuracy, Brier, ROI
GET /api/backtest/calibration → calibration curve bins (predicted vs observed)
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api", tags=["backtest"])

logger = logging.getLogger(__name__)

BACKTEST_DATA_DIR = Path("server/data/backtest_logs")


def _load_backtest_metrics() -> Dict[str, Any]:
    """Find and load the most recent backtest_metrics JSON file."""
    if not BACKTEST_DATA_DIR.exists():
        raise HTTPException(status_code=404, detail="Backtest data directory not found")

    metrics_files = sorted(BACKTEST_DATA_DIR.glob("backtest_metrics_*.json"))
    if not metrics_files:
        raise HTTPException(status_code=404, detail="No backtest metrics found")

    latest = metrics_files[-1]
    with open(latest) as f:
        return json.load(f)


def _compute_roi(accuracy: float, breakeven: float) -> float:
    """Compute ROI given accuracy and vig-adjusted breakeven threshold.

    For -110 vig (52.4% breakeven): ROI = (accuracy - breakeven) / breakeven * 100
    """
    return round((accuracy - breakeven) / breakeven * 100, 1)


@router.get("/backtest/summary")
def get_summary():
    """Overall backtest summary: accuracy, Brier score, ROI, model status."""
    try:
        data = _load_backtest_metrics()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to load backtest data: %s", e)
        raise HTTPException(status_code=500, detail="Failed to load backtest data")

    metadata = data.get("backtest_metadata", {})
    breakeven = metadata.get("breakeven_threshold", 0.524)

    # Compute weighted average metrics across folds
    fold_metrics = data.get("fold_metrics", [])
    total_val = sum(fm.get("n_val", 0) for fm in fold_metrics)

    if total_val == 0:
        raise HTTPException(status_code=404, detail="No validation data found")

    weighted_accuracy = sum(
        fm.get("accuracy", 0) * fm.get("n_val", 0) for fm in fold_metrics
    ) / total_val

    weighted_brier = sum(
        fm.get("brier_score", 0) * fm.get("n_val", 0) for fm in fold_metrics
    ) / total_val

    n_total = metadata.get("n_total_predictions", 0)
    roi = _compute_roi(weighted_accuracy, breakeven)

    return {
        "n_total_predictions": n_total,
        "overall_accuracy": round(weighted_accuracy, 4),
        "brier_score": round(weighted_brier, 4),
        "roi": roi,
        "model_loaded": True,
    }


@router.get("/backtest/seasons")
def get_seasons():
    """Per-season breakdown with games, accuracy, Brier, ROI."""
    try:
        data = _load_backtest_metrics()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to load backtest data: %s", e)
        raise HTTPException(status_code=500, detail="Failed to load backtest data")

    metadata = data.get("backtest_metadata", {})
    breakeven = metadata.get("breakeven_threshold", 0.524)
    season_breakdown = data.get("season_breakdown", {})

    result = []
    for season, metrics in season_breakdown.items():
        accuracy = metrics.get("accuracy", 0)
        result.append({
            "season": season,
            "n_games": metrics.get("n_predictions", 0),
            "accuracy": round(accuracy, 4),
            "brier_score": round(metrics.get("brier_score", 0), 4),
            "roi": _compute_roi(accuracy, breakeven),
        })

    if not result:
        raise HTTPException(status_code=404, detail="No season breakdown data found")

    return result


@router.get("/backtest/calibration")
def get_calibration():
    """Calibration bins: predicted probability bucket vs observed hit rate.

    Returns 10 bins (0-10%, 10-20%, ..., 90-100%) with predicted and observed rates.
    """
    try:
        data = _load_backtest_metrics()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to load backtest data: %s", e)
        raise HTTPException(status_code=500, detail="Failed to load backtest data")

    overall_cal = data.get("overall_calibration", {})
    fraction_positives = overall_cal.get("fraction_positives", [])
    mean_predicted = overall_cal.get("mean_predicted_value", [])
    bin_counts = overall_cal.get("bin_counts", [])

    if not fraction_positives or not mean_predicted:
        raise HTTPException(status_code=404, detail="No calibration data found")

    # Map overall_calibration bins to 10-bin format
    # The data has varying bin counts (sometimes fewer than 10 bins)
    # We need to expand to represent 10 equal-sized bins

    n_bins = len(fraction_positives)
    result = []

    for i in range(n_bins):
        result.append({
            "predicted_bin": round(mean_predicted[i], 3),
            "predicted_pct": round(mean_predicted[i] * 100, 1),
            "observed_pct": round(fraction_positives[i] * 100, 1),
            "n_predictions": bin_counts[i] if i < len(bin_counts) else 0,
        })

    return result