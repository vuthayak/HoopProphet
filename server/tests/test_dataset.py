import pandas as pd
import pytest
from server.pipeline.dataset import (
    load_training_data, get_feature_columns, prepare_datasets, get_target_column,
)
from server.pipeline.train_config import (
    ID_COLUMNS, TARGET_COLUMNS, META_COLUMNS, LEAKAGE_COLUMNS, CATEGORICAL_FEATURES,
)


def test_load_training_data_returns_dataframe(training_parquet):
    df = load_training_data(training_parquet)
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    assert "hit" in df.columns
    assert "stat_type" in df.columns
    assert "line_value" in df.columns


def test_get_feature_columns_excludes_leakage(training_parquet):
    df = load_training_data(training_parquet)
    feature_cols = get_feature_columns(df)
    # Must NOT contain ID columns
    for col in ID_COLUMNS:
        assert col not in feature_cols, f"ID column {col} should be excluded"
    # Must NOT contain target column
    assert "hit" not in feature_cols
    # Must NOT contain raw stat columns that leak the target
    for stat in ["pts", "reb", "ast", "stl", "blk", "fg3m", "min"]:
        assert stat not in feature_cols, f"Raw stat {stat} should be excluded"
    # Must NOT contain combo stat columns
    for combo in ["pra", "pa", "pr"]:
        assert combo not in feature_cols, f"Combo stat {combo} should be excluded"
    # Must NOT contain meta columns
    for col in META_COLUMNS:
        assert col not in feature_cols, f"Meta column {col} should be excluded"


def test_get_feature_columns_includes_model_inputs(training_parquet):
    df = load_training_data(training_parquet)
    feature_cols = get_feature_columns(df)
    # stat_type and line_value ARE features (model inputs, not leakage)
    assert "stat_type" in feature_cols, "stat_type should be a feature (categorical input)"
    assert "line_value" in feature_cols, "line_value should be a feature (prop threshold)"
    # Rolling features should be included
    assert any("_avg_L5" in c for c in feature_cols), "Rolling average features should be included"
    # Contextual features should be included
    assert any("rest_days" in c for c in feature_cols), "Contextual features should be included"


def test_prepare_datasets_shapes_and_dtypes(training_parquet):
    df = load_training_data(training_parquet)
    X, y = prepare_datasets(df)
    assert X.shape[0] == y.shape[0], "X and y should have same number of rows"
    assert X.shape[1] == len(get_feature_columns(df)), "X should have exactly the feature columns"
    assert y.name == "hit"
    assert set(y.unique()).issubset({0, 1}), "Target should be binary"
    # stat_type should be categorical for LightGBM
    assert X["stat_type"].dtype.name == "category", "stat_type should be category dtype"


def test_get_target_column():
    assert get_target_column() == "hit"