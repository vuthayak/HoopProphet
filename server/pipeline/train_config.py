import os
from server.pipeline import DATA_DIR
from server.pipeline.feature_config import (
    STAT_COLS, COMBO_STATS, ALL_TARGET_STATS, STAT_TYPE_MAP,
    PARQUET_PATH, MIN_GAMES_PER_SEASON,
)

# === Paths ===
MODEL_DIR = os.path.join(DATA_DIR, "models")
MODEL_ARTIFACT_PATH = os.path.join(MODEL_DIR, "model.joblib")

# === Feature Exclusion ===
# Columns from the Parquet that are NOT features for model training.
# These leak the target, are identifiers, or are metadata.
ID_COLUMNS = ["player_id", "game_id", "season", "game_date"]
TARGET_COLUMNS = ["hit"]
META_COLUMNS = ["matchup", "wl", "is_dnp", "opp_abbr", "opp_team_id",
                 "player_team_id", "game_date_dt"]
# Raw stat columns that would leak the target (the model predicts over/under on these)
LEAKAGE_COLUMNS = set(STAT_COLS) | set(COMBO_STATS.keys())

# === Model Hyperparameters ===
LGBM_PARAMS = {
    "objective": "binary",
    "metric": "binary_logloss",
    "n_estimators": 500,
    "learning_rate": 0.05,
    "max_depth": 6,
    "num_leaves": 31,
    "min_child_samples": 50,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 5,
    "reg_alpha": 0.1,
    "reg_lambda": 0.1,
    "verbose": -1,
    "n_jobs": -1,
    "random_state": 42,
}

# Categorical features in the long-format dataset (LightGBM handles these natively)
CATEGORICAL_FEATURES = ["stat_type"]

# Early stopping
EARLY_STOPPING_ROUNDS = 50

# === Walk-Forward Split Configuration ===
# Seasons available: 2020-21 through 2024-25 (5 seasons)
# Walk-forward expanding window: each fold trains on seasons up to N,
# validates on season N+1. The embargo gap prevents temporal leakage.
EMBARGO_GAMES = 0  # No embargo needed — season boundaries are natural separators

# === Calibration Configuration (per D-01, D-02) ===
CALIBRATION_METHOD_PREFERRED = "isotonic"
CALIBRATION_METHOD_FALLBACK = "sigmoid"  # Platt scaling
CALIBRATION_MIN_SAMPLES = 1000  # Below this, isotonic is unreliable; use Platt
CALIBRATION_MIN_PER_BIN = 10    # Isotonic bin stability check

# === Metrics Logging ===
METRICS_LOG_DIR = os.path.join(DATA_DIR, "training_logs")
METRICS_COLUMNS = ["fold", "train_seasons", "val_season", "n_train", "n_val",
                    "log_loss", "brier_score", "accuracy", "calibration_method",
                    "n_calibration_samples"]