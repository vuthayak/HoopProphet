import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

import joblib

from server.pipeline.train_config import MODEL_ARTIFACT_PATH, MODEL_DIR

logger = logging.getLogger(__name__)


def save_artifact(
    model,
    calibrator,
    feature_columns: list,
    metrics: Dict[str, Any],
    output_path: Optional[str] = None,
) -> str:
    """Save trained model + calibrator + metadata as a single .joblib bundle.

    Per MODL-05: the artifact contains everything needed for serving —
    the calibrated model, feature column order, training metadata, and
    calibration method.

    Args:
        model: Fitted LGBMClassifier (before calibration).
        calibrator: Fitted CalibratedClassifierCV wrapping the model.
        feature_columns: Ordered list of feature column names.
        metrics: Walk-forward metrics dict with fold-level results.
        output_path: Override default MODEL_ARTIFACT_PATH.

    Returns:
        Path to saved artifact file.
    """
    path = output_path or MODEL_ARTIFACT_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)

    artifact = {
        "model": model,                       # Raw LGBMClassifier (for inspecting feature importances)
        "calibrator": calibrator,              # CalibratedClassifierCV (use this for predict_proba)
        "feature_columns": feature_columns,    # Feature column order for input validation
        "categorical_features": ["stat_type"], # LightGBM categorical features
        "metrics": metrics,                     # Training metrics per fold
        "metadata": {
            "saved_at": datetime.utcnow().isoformat(),
            "version": "2.0",
            "n_features": len(feature_columns),
            "objective": "binary",
            "calibration_method": metrics.get("calibration_method", "unknown"),
        },
    }

    joblib.dump(artifact, path, compress=3)
    logger.info("Artifact saved to %s (%.1f MB)", path, os.path.getsize(path) / 1024 / 1024)
    return path


def load_artifact(path: Optional[str] = None) -> Dict[str, Any]:
    """Load a saved model artifact bundle.

    Args:
        path: Override default MODEL_ARTIFACT_PATH.

    Returns:
        Dict with keys: model, calibrator, feature_columns,
        categorical_features, metrics, metadata.
    """
    path = path or MODEL_ARTIFACT_PATH
    artifact = joblib.load(path)
    logger.info("Loaded artifact from %s (saved at %s)", path, artifact.get("metadata", {}).get("saved_at", "unknown"))
    return artifact


def predict_proba(artifact: Dict[str, Any], X) -> Any:
    """Predict calibrated probabilities using a loaded artifact.

    This is the serving interface: load once at startup, call predict_proba
    per request. The calibrator applies isotonic/sigmoid correction to raw
    LightGBM probabilities.

    Args:
        artifact: Loaded artifact dict from load_artifact().
        X: Feature DataFrame with columns matching artifact['feature_columns'].

    Returns:
        numpy array of calibrated probabilities for the positive class.
    """
    calibrator = artifact["calibrator"]
    feature_columns = artifact["feature_columns"]
    X_ordered = X[feature_columns].copy()

    # Ensure categorical dtype for LightGBM features
    for col in artifact.get("categorical_features", []):
        if col in X_ordered.columns:
            X_ordered[col] = X_ordered[col].astype("category")

    return calibrator.predict_proba(X_ordered)[:, 1]