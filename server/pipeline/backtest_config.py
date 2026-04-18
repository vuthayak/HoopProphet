"""Configuration constants for the back-test pipeline."""

import os
from server.pipeline import DATA_DIR
from server.pipeline.feature_config import ALL_TARGET_STATS

# Standard -110 sportsbook vig: win $100 on a $110 bet → 100/110 ≈ 0.909 profit per unit.
VIG_MULTIPLIER = 100 / 110  # ≈ 0.909

# Breakeven probability for -110 odds: need > 52.4% win rate to be profitable.
BREAKEVEN_THRESHOLD = 0.524

# Number of bins for calibration curves.
CALIBRATION_BINS = 10

# Confidence level for bootstrap intervals.
CONFIDENCE_LEVEL = 0.95

# Number of bootstrap resamples for confidence intervals.
BOOTSTRAP_SAMPLES = 1000

# Minimum seasons required for walk-forward training window.
MIN_TRAIN_SEASONS = 2

# Directory for back-test metrics output.
BACKTEST_METRICS_DIR = os.path.join(DATA_DIR, "backtest_logs")
