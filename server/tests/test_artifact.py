import os
import numpy as np
import pandas as pd
import pytest
from lightgbm import LGBMClassifier
from sklearn.calibration import CalibratedClassifierCV

from server.pipeline.artifact import save_artifact, load_artifact, predict_proba


@pytest.fixture
def fitted_model_and_calibrator():
    """Create a small fitted model and calibrator for testing."""
    rng = np.random.RandomState(42)
    n = 300
    X = pd.DataFrame({
        "feat_a": rng.randn(n),
        "feat_b": rng.randn(n),
        "stat_type": pd.Categorical(rng.choice([0, 1, 2], n)),
        "line_value": rng.uniform(0.5, 30, n),
    })
    y = rng.choice([0, 1], n, p=[0.45, 0.55])

    model = LGBMClassifier(
        n_estimators=30, learning_rate=0.1, max_depth=3,
        verbose=-1, random_state=42,
    )
    model.fit(X, y)

    # Calibrate on same data (not ideal for real use, but sufficient for testing)
    calibrator = CalibratedClassifierCV(
        estimator=LGBMClassifier(
            n_estimators=30, learning_rate=0.1, max_depth=3,
            verbose=-1, random_state=42,
        ),
        method="isotonic",
        cv=3,
    )
    calibrator.fit(X, y)

    feature_columns = list(X.columns)
    return model, calibrator, feature_columns, X


def test_save_and_load_artifact_roundtrip(fitted_model_and_calibrator, tmp_path):
    model, calibrator, feature_columns, X = fitted_model_and_calibrator
    path = str(tmp_path / "test_model.joblib")

    metrics = {
        "fold": 1,
        "log_loss": 0.65,
        "brier_score": 0.22,
        "calibration_method": "isotonic",
    }

    save_artifact(
        model, calibrator, feature_columns, metrics, output_path=path,
    )

    assert os.path.exists(path), "Artifact file should exist"

    loaded = load_artifact(path=path)
    assert "model" in loaded
    assert "calibrator" in loaded
    assert "feature_columns" in loaded
    assert loaded["feature_columns"] == feature_columns
    assert loaded["metadata"]["calibration_method"] == "isotonic"
    assert loaded["metadata"]["version"] == "2.0"
    assert isinstance(loaded["metadata"]["saved_at"], str)


def test_predict_proba_with_artifact(fitted_model_and_calibrator, tmp_path):
    model, calibrator, feature_columns, X = fitted_model_and_calibrator
    path = str(tmp_path / "test_model.joblib")

    save_artifact(
        model, calibrator, feature_columns,
        {"calibration_method": "isotonic"},
        output_path=path,
    )

    loaded = load_artifact(path=path)

    # Create test data with matching columns
    X_test = X.head(10).copy()
    probs = predict_proba(loaded, X_test)

    assert len(probs) == 10
    assert probs.min() >= 0.0
    assert probs.max() <= 1.0


def test_artifact_metadata_structure(fitted_model_and_calibrator, tmp_path):
    model, calibrator, feature_columns, X = fitted_model_and_calibrator
    path = str(tmp_path / "test_model.joblib")

    metrics = {"fold": 1, "log_loss": 0.65, "calibration_method": "sigmoid"}
    save_artifact(model, calibrator, feature_columns, metrics, output_path=path)

    loaded = load_artifact(path=path)
    metadata = loaded["metadata"]

    assert "saved_at" in metadata
    assert "version" in metadata
    assert "n_features" in metadata
    assert "objective" in metadata
    assert "calibration_method" in metadata
    assert metadata["n_features"] == len(feature_columns)
    assert metadata["objective"] == "binary"