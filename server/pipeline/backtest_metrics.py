"""Back-test metrics: calibration curves, ROI, season breakdown, confidence intervals.

Consumes the per-prediction DataFrame from backtest.py (Plan 01).
"""

from typing import Any, Callable, Dict

import numpy as np
import pandas as pd

from server.pipeline.backtest_config import (
    BOOTSTRAP_SAMPLES,
    BREAKEVEN_THRESHOLD,
    CALIBRATION_BINS,
    CONFIDENCE_LEVEL,
    VIG_MULTIPLIER,
)
from server.pipeline.feature_config import STAT_TYPE_NAMES
from server.pipeline.metrics import compute_calibration_curve


def compute_overall_calibration(
    predictions_df: pd.DataFrame, n_bins: int = CALIBRATION_BINS
) -> Dict[str, Any]:
    """Compute overall calibration curve and summary metrics.

    Args:
        predictions_df: DataFrame with hit and predicted_proba columns.
        n_bins: Number of calibration bins.

    Returns:
        Dict with fraction_positives, mean_predicted_value, bin_counts, ece,
        brier_score, log_loss, accuracy, n_predictions.
    """
    y_true = predictions_df["hit"].values
    y_pred = predictions_df["predicted_proba"].values

    curve = compute_calibration_curve(y_true, y_pred, n_bins=n_bins)

    from sklearn.metrics import brier_score_loss, log_loss

    result = dict(curve)
    result["brier_score"] = float(brier_score_loss(y_true, y_pred))
    result["log_loss"] = float(log_loss(y_true, y_pred))
    result["accuracy"] = float(np.mean((y_pred > 0.5) == y_true))
    result["n_predictions"] = int(len(y_true))
    return result


def compute_per_stat_calibration(
    predictions_df: pd.DataFrame, n_bins: int = CALIBRATION_BINS
) -> Dict[str, Dict[str, Any]]:
    """Per-stat-type calibration curves.

    Args:
        predictions_df: DataFrame with stat_type, hit, predicted_proba columns.
        n_bins: Number of calibration bins.

    Returns:
        Dict keyed by stat name (e.g. "pts", "reb"), each containing calibration
        curve data. Skips stat types with fewer than 50 predictions.
    """
    result: Dict[str, Dict[str, Any]] = {}

    for stat_type_val in predictions_df["stat_type"].unique():
        stat_name = STAT_TYPE_NAMES.get(int(stat_type_val))
        if stat_name is None:
            continue

        subset = predictions_df[predictions_df["stat_type"] == stat_type_val]
        if len(subset) < 50:
            result[stat_name] = {"skipped": "insufficient_samples", "n": len(subset)}
            continue

        result[stat_name] = compute_overall_calibration(subset, n_bins=n_bins)

    return result


def compute_season_breakdown(
    predictions_df: pd.DataFrame,
) -> Dict[str, Dict[str, float]]:
    """Season-by-season accuracy breakdown.

    Args:
        predictions_df: DataFrame with season, hit, predicted_proba columns.

    Returns:
        Dict keyed by season string, each with accuracy, log_loss, brier_score,
        n_predictions, mean_predicted_proba, hit_rate.
    """
    from sklearn.metrics import brier_score_loss, log_loss

    result: Dict[str, Dict[str, float]] = {}

    for season, group in predictions_df.groupby("season"):
        y_true = group["hit"].values
        y_pred = group["predicted_proba"].values
        n = len(y_true)

        unique_labels = np.unique(y_true)
        if len(unique_labels) < 2:
            # Cannot compute log_loss or brier_score with only one class
            ll = float("nan")
            brier = float("nan")
        else:
            ll = float(log_loss(y_true, y_pred))
            brier = float(brier_score_loss(y_true, y_pred))

        result[season] = {
            "accuracy": float(np.mean((y_pred > 0.5) == y_true)),
            "log_loss": ll,
            "brier_score": brier,
            "n_predictions": n,
            "mean_predicted_proba": float(np.mean(y_pred)),
            "hit_rate": float(np.mean(y_true)),
        }

    return result


def compute_roi_metrics(
    predictions_df: pd.DataFrame,
    threshold: float = BREAKEVEN_THRESHOLD,
) -> Dict[str, Any]:
    """Vig-adjusted ROI metrics using -110 odds.

    Args:
        predictions_df: DataFrame with hit, predicted_proba columns.
        threshold: Minimum probability to place a bet (default 52.4%).

    Returns:
        Dict with overall_roi, roi_by_bucket, total_bets, win_count, loss_count,
        net_units, total_wagered.
    """
    eligible = predictions_df[predictions_df["predicted_proba"] > threshold].copy()

    if len(eligible) == 0:
        return {
            "overall_roi": 0.0,
            "roi_by_bucket": {},
            "total_bets": 0,
            "win_count": 0,
            "loss_count": 0,
            "net_units": 0.0,
            "total_wagered": 0.0,
        }

    # Compute profit per bet
    is_win = eligible["hit"] == 1
    profit = np.where(is_win, VIG_MULTIPLIER, -1.0)
    net_units = float(np.sum(profit))
    total_wagered = float(len(profit))
    overall_roi = net_units / total_wagered

    # ROI by confidence bucket
    buckets = [
        (0.50, 0.55, "50-55%"),
        (0.55, 0.60, "55-60%"),
        (0.60, 0.70, "60-70%"),
        (0.70, 0.80, "70-80%"),
        (0.80, 1.01, "80%+"),
    ]
    roi_by_bucket: Dict[str, Dict[str, Any]] = {}
    for low, high, label in buckets:
        bucket_df = eligible[(eligible["predicted_proba"] >= low) & (eligible["predicted_proba"] < high)]
        if len(bucket_df) == 0:
            continue
        bucket_profit = np.where(bucket_df["hit"].values == 1, VIG_MULTIPLIER, -1.0)
        roi_by_bucket[label] = {
            "roi": float(np.sum(bucket_profit) / len(bucket_profit)),
            "n_bets": len(bucket_df),
        }

    return {
        "overall_roi": overall_roi,
        "roi_by_bucket": roi_by_bucket,
        "total_bets": int(len(eligible)),
        "win_count": int(np.sum(is_win)),
        "loss_count": int(np.sum(~is_win)),
        "net_units": net_units,
        "total_wagered": total_wagered,
    }


def compute_confidence_intervals(
    predictions_df: pd.DataFrame,
    metric_funcs: Dict[str, Callable] | None = None,
    n_bootstrap: int = BOOTSTRAP_SAMPLES,
    ci_level: float = CONFIDENCE_LEVEL,
) -> Dict[str, Dict[str, float]]:
    """Bootstrap confidence intervals for back-test metrics.

    Args:
        predictions_df: DataFrame with hit, predicted_proba columns.
        metric_funcs: Dict of metric name → callable that takes (y_true, y_pred).
                      Defaults to accuracy, brier_score, log_loss, roi.
        n_bootstrap: Number of bootstrap resamples.
        ci_level: Confidence level (default 0.95 → 2.5th/97.5th percentiles).

    Returns:
        Dict like: {"accuracy": {"low": 0.54, "mid": 0.58, "high": 0.62}, ...}
    """
    from sklearn.metrics import accuracy_score, brier_score_loss, log_loss

    if metric_funcs is None:
        def _roi(y_true, y_pred):
            eligible_mask = y_pred > BREAKEVEN_THRESHOLD
            if not np.any(eligible_mask):
                return np.nan
            profit = np.where(y_true[eligible_mask] == 1, VIG_MULTIPLIER, -1.0)
            return float(np.sum(profit) / len(profit))

        metric_funcs = {
            "accuracy": lambda y_true, y_pred: accuracy_score(y_true, y_pred > 0.5),
            "brier_score": lambda y_true, y_pred: brier_score_loss(y_true, y_pred),
            "log_loss": lambda y_true, y_pred: log_loss(y_true, y_pred),
            "roi": _roi,
        }

    y_true = predictions_df["hit"].values
    y_pred = predictions_df["predicted_proba"].values
    n = len(y_true)

    lower_pct = (1 - ci_level) / 2 * 100  # 2.5
    upper_pct = (1 + ci_level) / 2 * 100  # 97.5

    result: Dict[str, Dict[str, float]] = {}

    for metric_name, metric_func in metric_funcs.items():
        point_val = metric_func(y_true, y_pred)
        bootstrap_vals = []
        for _ in range(n_bootstrap):
            idx = np.random.randint(0, n, size=n)
            boot_val = metric_func(y_true[idx], y_pred[idx])
            bootstrap_vals.append(boot_val)

        bootstrap_vals = np.array(bootstrap_vals)
        # Filter out nan values
        bootstrap_vals = bootstrap_vals[~np.isnan(bootstrap_vals)]

        if len(bootstrap_vals) > 0:
            result[metric_name] = {
                "low": float(np.percentile(bootstrap_vals, lower_pct)),
                "mid": float(point_val),
                "high": float(np.percentile(bootstrap_vals, upper_pct)),
            }
        else:
            result[metric_name] = {"low": np.nan, "mid": float(point_val), "high": np.nan}

    return result
