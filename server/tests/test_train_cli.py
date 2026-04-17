import os
import tempfile

import numpy as np
import pytest

from server.pipeline.train_cli import run_training_pipeline
from server.pipeline.artifact import load_artifact, predict_proba
from server.pipeline.dataset import load_training_data, prepare_datasets


def test_full_training_pipeline_on_synthetic_data(training_parquet, tmp_path):
    """End-to-end: load → walk-forward → train → calibrate → save → load → predict."""
    output_path = str(tmp_path / "test_model.joblib")
    metrics_dir = str(tmp_path / "metrics")

    summary = run_training_pipeline(
        parquet_path=training_parquet,
        output_path=output_path,
        min_train_seasons=2,
        metrics_dir=metrics_dir,
    )

    # Verify pipeline summary
    assert "artifact_path" in summary
    assert "n_folds" in summary
    assert "final_calibration_method" in summary
    assert summary["artifact_path"] == output_path

    # Verify artifact file exists
    assert os.path.exists(output_path)

    # Load and verify artifact
    artifact = load_artifact(path=output_path)
    assert "model" in artifact
    assert "calibrator" in artifact
    assert "feature_columns" in artifact
    assert "metrics" in artifact
    assert "metadata" in artifact
    assert artifact["metadata"]["objective"] == "binary"
    assert artifact["metadata"]["calibration_method"] in ["isotonic", "sigmoid"]

    # Verify predict_proba works
    df = load_training_data(training_parquet)
    X, _ = prepare_datasets(df.head(20))
    probs = predict_proba(artifact, X)
    assert len(probs) == 20
    assert probs.min() >= 0.0
    assert probs.max() <= 1.0
    assert not np.any(np.isnan(probs))

    # Verify metrics log was written (or would be — check summary)
    assert "n_folds" in summary
    assert summary["n_folds"] >= 1


def test_calibration_method_recorded_in_artifact(training_parquet, tmp_path):
    """Verify that the calibration method (isotonic or sigmoid) is recorded."""
    output_path = str(tmp_path / "test_model.joblib")
    metrics_dir = str(tmp_path / "metrics")

    run_training_pipeline(
        parquet_path=training_parquet,
        output_path=output_path,
        min_train_seasons=2,
        metrics_dir=metrics_dir,
    )

    artifact = load_artifact(path=output_path)
    cal_method = artifact["metadata"]["calibration_method"]
    assert cal_method in ["isotonic", "sigmoid"], f"Expected isotonic or sigmoid, got {cal_method}"

    # Verify metrics contain calibration method per fold
    fold_metrics = artifact["metrics"]["fold_metrics"]
    for fm in fold_metrics:
        if isinstance(fm.get("fold"), int):  # Skip the "final" entry
            assert "calibration_method" in fm
            assert fm["calibration_method"] in ["isotonic", "sigmoid"]


def test_walk_forward_fold_metrics_present(training_parquet, tmp_path):
    """Verify that walk-forward fold metrics include all required fields per MODL-07."""
    output_path = str(tmp_path / "test_model.joblib")
    metrics_dir = str(tmp_path / "metrics")

    summary = run_training_pipeline(
        parquet_path=training_parquet,
        output_path=output_path,
        min_train_seasons=2,
        metrics_dir=metrics_dir,
    )

    artifact = load_artifact(path=output_path)
    fold_metrics = artifact["metrics"]["fold_metrics"]

    # Should have at least 1 fold + 1 "final" entry
    assert len(fold_metrics) >= 2

    # Each fold metric should have required fields (MODL-07)
    required_fields = ["fold", "train_seasons", "n_train", "log_loss", "brier_score",
                       "accuracy", "calibration_method", "n_calibration_samples"]
    for fm in fold_metrics:
        if isinstance(fm.get("fold"), int):
            for field in required_fields:
                assert field in fm, f"Fold metric missing field: {field}"