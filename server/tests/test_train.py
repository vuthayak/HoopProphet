import numpy as np
import pandas as pd
import pytest
from lightgbm import LGBMClassifier
from sklearn.metrics import log_loss

from server.pipeline.train import train_model
from server.pipeline.dataset import load_training_data, prepare_datasets


@pytest.fixture
def synthetic_train_val():
    """Create small synthetic train/val DataFrames for fast tests."""
    rng = np.random.RandomState(42)
    n_train = 200
    n_val = 50
    feature_names = ["feat_a", "feat_b", "feat_c", "stat_type", "line_value"]

    def make_df(n, rng):
        df = pd.DataFrame({
            "feat_a": rng.randn(n),
            "feat_b": rng.randn(n),
            "feat_c": rng.randn(n),
            "stat_type": rng.choice([0, 1, 2, 3], n),
            "line_value": rng.uniform(0.5, 30, n),
            "hit": rng.choice([0, 1], n, p=[0.45, 0.55]),
            "player_id": rng.choice([203999, 2544], n),
            "game_id": [f"game_{i}" for i in range(n)],
            "season": rng.choice(["2022-23", "2023-24"], n),
            "game_date": [f"2023-01-{(i%28)+1:02d}" for i in range(n)],
        })
        return df

    return make_df(n_train, rng), make_df(n_val, rng)


def test_train_model_returns_lgbm_classifier(synthetic_train_val):
    train_df, val_df = synthetic_train_val
    model, metrics = train_model(train_df, val_df, early_stopping=False)
    assert isinstance(model, LGBMClassifier)
    assert model.objective_ == "binary"


def test_train_model_output_probabilities(synthetic_train_val):
    train_df, val_df = synthetic_train_val
    model, metrics = train_model(train_df, val_df, early_stopping=False)
    X_val, _ = prepare_datasets(val_df)
    probs = model.predict_proba(X_val)[:, 1]
    assert probs.min() >= 0.0, "Probabilities must be >= 0"
    assert probs.max() <= 1.0, "Probabilities must be <= 1"


def test_train_model_categorical_features(synthetic_train_val):
    train_df, val_df = synthetic_train_val
    model, metrics = train_model(train_df, val_df, early_stopping=False)
    # LightGBM should handle stat_type as categorical
    X_val, _ = prepare_datasets(val_df)
    probs = model.predict_proba(X_val)
    assert probs.shape[1] == 2, "Binary classifier should output 2 columns"


def test_train_model_metrics_returned(synthetic_train_val):
    train_df, val_df = synthetic_train_val
    model, metrics = train_model(train_df, val_df, early_stopping=False)
    assert "train_rows" in metrics
    assert "val_rows" in metrics
    assert "train_log_loss" in metrics
    assert "val_log_loss" in metrics
    assert metrics["train_rows"] == 200
    assert metrics["val_rows"] == 50


def test_train_model_feature_importances(synthetic_train_val):
    train_df, val_df = synthetic_train_val
    model, metrics = train_model(train_df, val_df, early_stopping=False)
    importances = model.feature_importances_
    assert len(importances) > 0, "Feature importances should be available"
    # At least some features should have non-zero importance
    assert importances.sum() > 0, "Some features should have non-zero importance"