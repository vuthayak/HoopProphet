import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss, log_loss

from server.pipeline.train_config import METRICS_LOG_DIR, METRICS_COLUMNS

logger = logging.getLogger(__name__)


def compute_fold_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    fold: int,
    train_seasons: list,
    val_season: str,
    n_train: int,
    n_val: int,
    calibration_method: str,
    n_calibration_samples: int,
) -> Dict[str, Any]:
    """Compute evaluation metrics for a single walk-forward fold.

    Per MODL-07: logs log loss, Brier score, accuracy, and fold metadata.

    Args:
        y_true: True binary labels.
        y_pred: Predicted probabilities for the positive class.
        fold: Fold number (1-indexed).
        train_seasons: Seasons used for training in this fold.
        val_season: Season used for validation.
        n_train: Number of training rows.
        n_val: Number of validation rows.
        calibration_method: 'isotonic' or 'sigmoid'.
        n_calibration_samples: Number of calibration set rows.

    Returns:
        Dict with all fold metrics.
    """
    ll = log_loss(y_true, y_pred)
    brier = brier_score_loss(y_true, y_pred)
    accuracy = np.mean((y_pred > 0.5) == y_true)

    metrics = {
        "fold": fold,
        "train_seasons": train_seasons,
        "val_season": val_season,
        "n_train": n_train,
        "n_val": n_val,
        "log_loss": round(float(ll), 6),
        "brier_score": round(float(brier), 6),
        "accuracy": round(float(accuracy), 6),
        "calibration_method": calibration_method,
        "n_calibration_samples": n_calibration_samples,
    }

    logger.info(
        "Fold %d metrics: log_loss=%.4f, brier=%.4f, accuracy=%.4f, method=%s",
        fold, ll, brier, accuracy, calibration_method,
    )

    return metrics


def compute_calibration_curve(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    n_bins: int = 10,
    strategy: str = "uniform",
) -> Dict[str, Any]:
    """Compute calibration curve data for reliability diagrams.

    Per MODL-07: provides calibration curve (predicted vs observed hit rates)
    for assessing whether "70% predicted" means ~70% observed.

    Args:
        y_true: True binary labels.
        y_pred: Predicted probabilities for the positive class.
        n_bins: Number of bins for the calibration curve (default 10).
        strategy: Binning strategy ('uniform' or 'quantile').

    Returns:
        Dict with:
            - fraction_positives: observed hit rate per bin
            - mean_predicted_value: mean predicted probability per bin
            - n_bins: number of bins
            - bin_counts: number of samples per bin
    """
    fraction_positives, mean_predicted = calibration_curve(
        y_true, y_pred, n_bins=n_bins, strategy=strategy,
    )

    # Compute bin counts for transparency
    # Use the same binning strategy as calibration_curve to ensure alignment
    if strategy == "quantile":
        bins = np.percentile(y_pred, np.linspace(0, 100, n_bins + 1))
        bins[0] = 0.0
        bins[-1] = 1.0
    else:
        bins = np.linspace(0.0, 1.0, n_bins + 1)

    all_bin_counts = np.histogram(y_pred, bins=bins)[0]

    # calibration_curve may drop empty bins, so we need to align
    # bin_counts with the returned fraction_positives array
    non_empty_mask = all_bin_counts > 0
    aligned_bin_counts = all_bin_counts[non_empty_mask]

    # Safety: if lengths still mismatch, truncate to match
    min_len = min(len(fraction_positives), len(aligned_bin_counts))
    fraction_positives = fraction_positives[:min_len]
    mean_predicted = mean_predicted[:min_len]
    aligned_bin_counts = aligned_bin_counts[:min_len]

    curve_data = {
        "fraction_positives": fraction_positives.tolist(),
        "mean_predicted_value": mean_predicted.tolist(),
        "n_bins": n_bins,
        "bin_counts": aligned_bin_counts.tolist(),
    }

    # Compute Expected Calibration Error (ECE)
    total = np.sum(aligned_bin_counts)
    if total > 0:
        ece = np.sum(aligned_bin_counts * np.abs(fraction_positives - mean_predicted)) / total
    else:
        ece = 0.0
    curve_data["ece"] = round(float(ece), 6)

    logger.info(
        "Calibration curve: %d bins, ECE=%.4f", n_bins, ece,
    )

    return curve_data


def save_metrics_log(
    all_fold_metrics: List[Dict],
    calibration_curve_data: Optional[Dict] = None,
    output_dir: Optional[str] = None,
) -> str:
    """Save all training metrics to a JSON log file.

    Args:
        all_fold_metrics: List of per-fold metrics dicts.
        calibration_curve_data: Optional calibration curve data.
        output_dir: Override default METRICS_LOG_DIR.

    Returns:
        Path to saved metrics file.
    """
    output_dir = output_dir or METRICS_LOG_DIR
    os.makedirs(output_dir, exist_ok=True)

    log_data = {
        "fold_metrics": all_fold_metrics,
        "summary": {
            "mean_log_loss": round(float(np.mean([m["log_loss"] for m in all_fold_metrics])), 6),
            "mean_brier_score": round(float(np.mean([m["brier_score"] for m in all_fold_metrics])), 6),
            "mean_accuracy": round(float(np.mean([m["accuracy"] for m in all_fold_metrics])), 6),
            "n_folds": len(all_fold_metrics),
            "calibration_method": all_fold_metrics[-1]["calibration_method"] if all_fold_metrics else "unknown",
        },
    }

    if calibration_curve_data:
        log_data["calibration_curve"] = calibration_curve_data

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(output_dir, f"training_metrics_{timestamp}.json")
    with open(log_path, "w") as f:
        json.dump(log_data, f, indent=2)

    logger.info("Saved metrics log to %s", log_path)
    return log_path