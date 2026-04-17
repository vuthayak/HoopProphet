import logging
from typing import Tuple

import pandas as pd
from server.pipeline.feature_config import PARQUET_PATH
from server.pipeline.train_config import (
    ID_COLUMNS, TARGET_COLUMNS, META_COLUMNS, LEAKAGE_COLUMNS, CATEGORICAL_FEATURES,
)

logger = logging.getLogger(__name__)


def load_training_data(parquet_path: str = None) -> pd.DataFrame:
    """Load the long-format feature Parquet from Phase 2.

    Returns the full DataFrame with all columns. Does NOT filter or split —
    callers (get_feature_columns, walk_forward_split) handle that.

    Raises:
        FileNotFoundError: If Parquet file does not exist.
    """
    path = parquet_path or PARQUET_PATH
    df = pd.read_parquet(path, engine="pyarrow")
    logger.info("Loaded training data: %d rows, %d columns from %s", len(df), len(df.columns), path)
    return df


def get_feature_columns(df: pd.DataFrame) -> list[str]:
    """Identify which columns are model features.

    Features = all columns NOT in ID_COLUMNS, TARGET_COLUMNS, META_COLUMNS,
    or LEAKAGE_COLUMNS. Includes stat_type and line_value (they are input
    signals, not targets).
    """
    exclude = set(ID_COLUMNS) | set(TARGET_COLUMNS) | set(META_COLUMNS) | LEAKAGE_COLUMNS
    feature_cols = [c for c in df.columns if c not in exclude]
    logger.info("Identified %d feature columns (excluded %d)", len(feature_cols), len(exclude))
    return feature_cols


def get_target_column() -> str:
    """Return the target column name."""
    return "hit"


def prepare_datasets(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """Split DataFrame into feature matrix X and target vector y.

    Applies dtype conversion for LightGBM:
    - stat_type → categorical
    - line_value → float32
    - All numeric features → float32

    Returns:
        X: DataFrame with feature columns only
        y: Series with 'hit' column (0/1 binary)
    """
    feature_cols = get_feature_columns(df)
    X = df[feature_cols].copy()
    y = df[get_target_column()].copy()

    # Convert categorical feature for LightGBM
    if "stat_type" in X.columns:
        X["stat_type"] = X["stat_type"].astype("category")

    # Convert numeric columns to float32 for LightGBM efficiency
    numeric_cols = X.select_dtypes(include=["int64", "int32", "float64"]).columns
    X[numeric_cols] = X[numeric_cols].astype("float32")

    logger.info("Prepared datasets: X=%s, y distribution=%s", X.shape, y.value_counts().to_dict())
    return X, y