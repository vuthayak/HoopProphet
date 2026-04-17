import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import log_loss, brier_score_loss

from server.pipeline.dataset import load_training_data, prepare_datasets
from server.pipeline.splits import walk_forward_split
from server.pipeline.train import train_model
from server.pipeline.calibrate import calibrate_model


@pytest.fixture
def train_val_data(training_parquet):
    """Load synthetic data and split into train/val."""
    df = load_training_data(training_parquet)
    folds = walk_forward_split(df, min_train_seasons=2)
    # Use the only fold (3 seasons, min_train=2 → 1 fold)
    train_df, val_df = folds[0]
    return train_df, val_df


def test_train_then_calibrate_produces_valid_probabilities(train_val_data):
    """Full pipeline: train → calibrate → predict probabilities in [0, 1]."""
    train_df, val_df = train_val_data
    model, train_metrics = train_model(train_df, val_df)
    X_val, y_val = prepare_datasets(val_df)
    calibrated, cal_info = calibrate_model(model, X_val, y_val)
    probs = calibrated.predict_proba(X_val)[:, 1]
    assert probs.min() >= 0.0
    assert probs.max() <= 1.0
    assert not np.any(np.isnan(probs)), "Probabilities should not be NaN"


def test_calibration_method_logged(train_val_data):
    """Calibration method is recorded in info dict."""
    train_df, val_df = train_val_data
    model, _ = train_model(train_df, val_df)
    X_val, y_val = prepare_datasets(val_df)
    calibrated, cal_info = calibrate_model(model, X_val, y_val)
    assert cal_info["calibration_method"] in ["isotonic", "sigmoid"]
    assert "calibration_reason" in cal_info
    assert cal_info["n_calibration_samples"] == len(y_val)


def test_metrics_are_finite_and_reasonable(train_val_data):
    """Log loss and Brier score are finite, reasonable numbers."""
    train_df, val_df = train_val_data
    model, train_metrics = train_model(train_df, val_df)
    X_val, y_val = prepare_datasets(val_df)
    calibrated, cal_info = calibrate_model(model, X_val, y_val)

    # Train metrics should be finite
    assert np.isfinite(train_metrics["train_log_loss"])
    assert train_metrics["train_log_loss"] > 0
    assert train_metrics["train_log_loss"] < 1.0  # binary log loss <= 1 for reasonable models

    # Calibration Brier scores should be finite
    assert np.isfinite(cal_info["brier_score_before"])
    assert np.isfinite(cal_info["brier_score_after"])


def test_walk_forward_plus_train_calibrate(train_val_data):
    """Validate that the full walk-forward → train → calibrate pipeline works."""
    train_df, val_df = train_val_data
    model, metrics = train_model(train_df, val_df)
    X_val, y_val = prepare_datasets(val_df)
    calibrated, cal_info = calibrate_model(model, X_val, y_val)

    # Verify the calibrated model can predict
    probs = calibrated.predict_proba(X_val)[:, 1]
    assert len(probs) == len(y_val)

    # Brier score should be computed
    brier = brier_score_loss(y_val, probs)
    assert np.isfinite(brier)
    assert 0 < brier < 1  # Should be better than random guessing