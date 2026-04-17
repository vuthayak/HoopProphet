import json
import os
import numpy as np
import pytest

from server.pipeline.metrics import (
    compute_fold_metrics, compute_calibration_curve, save_metrics_log,
)


def test_compute_fold_metrics():
    rng = np.random.RandomState(42)
    y_true = rng.choice([0, 1], 1000, p=[0.45, 0.55])
    y_pred = np.clip(y_true + rng.randn(1000) * 0.3, 0, 1)

    metrics = compute_fold_metrics(
        y_true=y_true, y_pred=y_pred,
        fold=1, train_seasons=["2020-21", "2021-22"], val_season="2022-23",
        n_train=50000, n_val=12000,
        calibration_method="isotonic", n_calibration_samples=12000,
    )

    assert metrics["fold"] == 1
    assert metrics["train_seasons"] == ["2020-21", "2021-22"]
    assert metrics["val_season"] == "2022-23"
    assert 0 < metrics["log_loss"] < 1.0
    assert 0 < metrics["brier_score"] < 1.0
    assert 0 < metrics["accuracy"] < 1.0
    assert metrics["calibration_method"] == "isotonic"
    assert metrics["n_calibration_samples"] == 12000


def test_compute_calibration_curve():
    rng = np.random.RandomState(42)
    n = 2000
    y_true = rng.choice([0, 1], n, p=[0.45, 0.55])
    # Well-calibrated predictions: add noise but keep correlated
    y_pred = np.clip(y_true * 0.7 + np.random.random(n) * 0.3, 0, 1)

    curve = compute_calibration_curve(y_true, y_pred, n_bins=10)

    assert "fraction_positives" in curve
    assert "mean_predicted_value" in curve
    assert "n_bins" in curve
    assert "bin_counts" in curve
    assert "ece" in curve
    # calibration_curve may drop empty bins, so lengths can be <= n_bins
    assert len(curve["fraction_positives"]) <= 10
    assert len(curve["mean_predicted_value"]) <= 10
    assert curve["n_bins"] == 10
    # ECE should be a reasonable number
    assert 0 <= curve["ece"] <= 1.0


def test_save_metrics_log(tmp_path):
    fold_metrics = [
        {
            "fold": 1, "train_seasons": ["2020-21", "2021-22"],
            "val_season": "2022-23", "n_train": 50000, "n_val": 12000,
            "log_loss": 0.654, "brier_score": 0.223, "accuracy": 0.589,
            "calibration_method": "isotonic", "n_calibration_samples": 12000,
        },
        {
            "fold": 2, "train_seasons": ["2020-21", "2021-22", "2022-23"],
            "val_season": "2023-24", "n_train": 62000, "n_val": 13000,
            "log_loss": 0.661, "brier_score": 0.231, "accuracy": 0.582,
            "calibration_method": "isotonic", "n_calibration_samples": 13000,
        },
    ]

    path = save_metrics_log(
        fold_metrics,
        calibration_curve_data={"fraction_positives": [0.1, 0.3], "mean_predicted_value": [0.12, 0.29]},
        output_dir=str(tmp_path),
    )

    assert os.path.exists(path)
    with open(path) as f:
        data = json.load(f)

    assert "fold_metrics" in data
    assert "summary" in data
    assert data["summary"]["n_folds"] == 2
    assert "calibration_curve" in data
    assert isinstance(data["summary"]["mean_log_loss"], float)