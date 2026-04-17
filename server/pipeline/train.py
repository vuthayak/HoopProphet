import logging
from typing import Optional, Tuple

import pandas as pd
from lightgbm import LGBMClassifier, early_stopping, log_evaluation
from sklearn.metrics import log_loss

from server.pipeline.train_config import (
    LGBM_PARAMS, CATEGORICAL_FEATURES, EARLY_STOPPING_ROUNDS,
)
from server.pipeline.dataset import prepare_datasets

logger = logging.getLogger(__name__)


def _log_callback(stopping_rounds: int):
    """Return list of LightGBM callbacks for early stopping and logging.

    Uses the modern callback API (LightGBM >= 4.0) instead of
    deprecated keyword arguments.
    """
    return [early_stopping(stopping_rounds=stopping_rounds, verbose=True),
            log_evaluation(period=50)]


def train_model(
    train_df: pd.DataFrame,
    val_df: Optional[pd.DataFrame] = None,
    params: Optional[dict] = None,
    early_stopping: bool = True,
) -> Tuple[LGBMClassifier, dict]:
    """Train a unified LightGBM binary classifier.

    Trains a single model across all players and all prop stat types.
    Per MODL-01: unified model. Per MODL-02: binary objective with probability output.

    Args:
        train_df: Training DataFrame with feature columns and 'hit' target.
        val_df: Validation DataFrame for early stopping. If None, uses 10% of train.
        params: Override default LGBM_PARAMS. Merged with defaults.
        early_stopping: Whether to use early stopping on validation set.

    Returns:
        Tuple of (fitted LGBMClassifier, metrics_dict).
        metrics_dict contains: train_rows, val_rows, best_iteration, train_log_loss.
    """
    # Merge user params with defaults
    lgbm_params = {**LGBM_PARAMS, **(params or {})}

    # Prepare X, y
    X_train, y_train = prepare_datasets(train_df)

    # Make categorical columns explicit for LightGBM
    for col in CATEGORICAL_FEATURES:
        if col in X_train.columns:
            X_train[col] = X_train[col].astype("category")

    # Prepare evaluation set
    metrics = {"train_rows": len(train_df)}
    eval_set = None
    eval_names = None

    if val_df is not None:
        X_val, y_val = prepare_datasets(val_df)
        for col in CATEGORICAL_FEATURES:
            if col in X_val.columns:
                X_val[col] = X_val[col].astype("category")
        eval_set = [(X_val, y_val)]
        eval_names = ["validation"]
        metrics["val_rows"] = len(val_df)

    # Train the model
    model = LGBMClassifier(**lgbm_params)

    fit_params = {}
    if early_stopping and eval_set is not None:
        fit_params["eval_set"] = eval_set
        fit_params["eval_names"] = eval_names
        fit_params["callbacks"] = _log_callback(EARLY_STOPPING_ROUNDS)

    model.fit(X_train, y_train, **fit_params)

    # Record metrics
    metrics["best_iteration"] = model.best_iteration_ if hasattr(model, "best_iteration_") else lgbm_params["n_estimators"]
    y_train_pred = model.predict_proba(X_train)[:, 1]
    metrics["train_log_loss"] = log_loss(y_train, y_train_pred)

    if val_df is not None:
        y_val_pred = model.predict_proba(X_val)[:, 1]
        metrics["val_log_loss"] = log_loss(y_val, y_val_pred)

    logger.info(
        "Trained LightGBM: %d rows, best_iteration=%s, train_log_loss=%.4f, val_log_loss=%.4f",
        metrics["train_rows"],
        metrics["best_iteration"],
        metrics["train_log_loss"],
        metrics.get("val_log_loss", float("nan")),
    )

    return model, metrics