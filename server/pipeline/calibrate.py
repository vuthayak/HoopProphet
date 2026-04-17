import logging
from typing import Tuple

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import brier_score_loss

from server.pipeline.train_config import (
    CALIBRATION_METHOD_PREFERRED,
    CALIBRATION_METHOD_FALLBACK,
    CALIBRATION_MIN_SAMPLES,
    CALIBRATION_MIN_PER_BIN,
)

logger = logging.getLogger(__name__)


def _check_isotonic_reliability(
    y_cal: np.ndarray, n_samples: int
) -> Tuple[bool, str]:
    """Check if isotonic regression is reliable on the given calibration data.

    Per D-01/D-02: Isotonic regression requires sufficient samples for stable
    fitting. Below CALIBRATION_MIN_SAMPLES, use Platt sigmoid instead.
    Also checks for severe class imbalance that would make isotonic bins
    unreliable even with sufficient total samples.

    Args:
        y_cal: Binary labels for the calibration set.
        n_samples: Number of calibration samples.

    Returns:
        Tuple of (is_reliable, reason). If not reliable, reason explains why.
    """
    if n_samples < CALIBRATION_MIN_SAMPLES:
        reason = (
            f"Calibration set has {n_samples} samples, below threshold "
            f"{CALIBRATION_MIN_SAMPLES}. Using {CALIBRATION_METHOD_FALLBACK} "
            f"fallback instead of {CALIBRATION_METHOD_PREFERRED}."
        )
        logger.warning(reason)
        return False, reason

    # Check bin stability: even with enough total samples, isotonic can
    # produce erratic curves if class imbalance creates empty quantile bins
    n_positive = int(y_cal.sum())
    n_negative = len(y_cal) - n_positive
    min_class_samples = min(n_positive, n_negative)
    if min_class_samples <= CALIBRATION_MIN_PER_BIN:
        reason = (
            f"Calibration set has severe class imbalance: {n_positive} positive, "
            f"{n_negative} negative (min={min_class_samples}, threshold="
            f"{CALIBRATION_MIN_PER_BIN}). Using {CALIBRATION_METHOD_FALLBACK} "
            f"fallback instead of {CALIBRATION_METHOD_PREFERRED}."
        )
        logger.warning(reason)
        return False, reason

    return True, "Sufficient samples and class balance for isotonic calibration."


def calibrate_model(
    model,
    X_cal: np.ndarray,
    y_cal: np.ndarray,
) -> Tuple[CalibratedClassifierCV, dict]:
    """Calibrate a fitted LightGBM model's probability outputs.

    Per MODL-03: Applies probability calibration to ensure predicted
    probabilities match observed hit rates. Per D-01: prefers isotonic
    regression. Per D-02: falls back to Platt scaling when isotonic
    is unreliable.

    Uses sklearn's CalibratedClassifierCV with cv='prefit' to calibrate
    an already-trained model on held-out calibration data. This is NOT
    cross-validation — it's a post-hoc calibration step on a separate
    calibration set.

    Args:
        model: A fitted LGBMClassifier.
        X_cal: Calibration feature matrix (held-out, not used in training).
        y_cal: Calibration target labels (binary 0/1).

    Returns:
        Tuple of (calibrated_model, calibration_info).
        calibration_info contains:
            method: 'isotonic' or 'sigmoid' (which was actually used)
            reason: why this method was chosen
            n_calibration_samples: size of calibration set
            brier_score_before: Brier score of uncalibrated model
            brier_score_after: Brier score of calibrated model
    """
    n_samples = len(y_cal)

    # Compute pre-calibration Brier score
    y_pred_before = model.predict_proba(X_cal)[:, 1]
    brier_before = brier_score_loss(y_cal, y_pred_before)

    # Determine calibration method
    is_reliable, reason = _check_isotonic_reliability(y_cal, n_samples)
    method = CALIBRATION_METHOD_PREFERRED if is_reliable else CALIBRATION_METHOD_FALLBACK

    logger.info(
        "Calibrating model: method=%s, n_calibration_samples=%d, reason=%s",
        method, n_samples, reason,
    )

    # Fit CalibratedClassifierCV with cv='prefit' on the held-out calibration set
    calibrated = CalibratedClassifierCV(
        estimator=model,
        method=method,
        cv="prefit",
    )
    calibrated.fit(X_cal, y_cal)

    # Compute post-calibration Brier score
    y_pred_after = calibrated.predict_proba(X_cal)[:, 1]
    brier_after = brier_score_loss(y_cal, y_pred_after)

    calibration_info = {
        "calibration_method": method,
        "calibration_reason": reason,
        "n_calibration_samples": n_samples,
        "brier_score_before": round(brier_before, 6),
        "brier_score_after": round(brier_after, 6),
    }

    logger.info(
        "Calibration complete: method=%s, brier_before=%.4f, brier_after=%.4f",
        method, brier_before, brier_after,
    )

    return calibrated, calibration_info