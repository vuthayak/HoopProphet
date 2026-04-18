"""Unit tests for walk-forward back-test evaluation engine.

RED phase: Tests define expected behavior before implementation.
Tests use training_parquet fixture (3 seasons, 2 players, 2 stats).
"""
import numpy as np
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch


class TestBacktestConfig:
    """Tests for backtest configuration constants."""

    def test_breakeven_threshold_value(self):
        """BREAKEVEN_THRESHOLD must be 0.524 (52.4% at -110 vig)."""
        from server.pipeline.backtest_config import BREAKEVEN_THRESHOLD
        assert BREAKEVEN_THRESHOLD == 0.524

    def test_vig_multiplier_value(self):
        """VIG_MULTIPLIER must be 0.909 (profit at -110: 100/110)."""
        from server.pipeline.backtest_config import VIG_MULTIPLIER
        assert VIG_MULTIPLIER == pytest.approx(0.909, rel=1e-3)

    def test_calibration_bins(self):
        """CALIBRATION_BINS must be 10."""
        from server.pipeline.backtest_config import CALIBRATION_BINS
        assert CALIBRATION_BINS == 10

    def test_bootstrap_samples(self):
        """BOOTSTRAP_SAMPLES must be 1000."""
        from server.pipeline.backtest_config import BOOTSTRAP_SAMPLES
        assert BOOTSTRAP_SAMPLES == 1000

    def test_min_train_seasons(self):
        """MIN_TRAIN_SEASONS must be 2."""
        from server.pipeline.backtest_config import MIN_TRAIN_SEASONS
        assert MIN_TRAIN_SEASONS == 2

    def test_all_target_stats(self):
        """ALL_TARGET_STATS must contain all 10 prop stats."""
        from server.pipeline.backtest_config import ALL_TARGET_STATS
        expected = ["pts", "reb", "ast", "stl", "blk", "fg3m", "pra", "pa", "pr", "min"]
        assert ALL_TARGET_STATS == expected


class TestBacktestResultDataclass:
    """Tests for BacktestResult dataclass structure."""

    def test_backtest_result_has_required_fields(self):
        """BacktestResult must have predictions_df, fold_summaries, n_folds, seasons."""
        from server.pipeline.backtest import BacktestResult
        # Create with empty data
        result = BacktestResult(
            predictions_df=pd.DataFrame(),
            fold_summaries=[],
            n_folds=0,
            seasons=[],
        )
        assert hasattr(result, "predictions_df")
        assert hasattr(result, "fold_summaries")
        assert hasattr(result, "n_folds")
        assert hasattr(result, "seasons")
        assert isinstance(result.predictions_df, pd.DataFrame)
        assert isinstance(result.fold_summaries, list)
        assert result.n_folds == 0
        assert result.seasons == []

    def test_backtest_result_predictions_df_columns(self):
        """predictions_df must have required columns after a run."""
        from server.pipeline.backtest import BacktestResult
        df = pd.DataFrame({
            "player_id": [1],
            "game_id": ["foo"],
            "season": ["2023-24"],
            "stat_type": [0],
            "line_value": [20.0],
            "hit": [1],
            "predicted_proba": [0.6],
            "fold": [1],
        })
        result = BacktestResult(
            predictions_df=df,
            fold_summaries=[],
            n_folds=1,
            seasons=["2021-22"],
        )
        required_cols = ["player_id", "game_id", "season", "stat_type",
                         "line_value", "hit", "predicted_proba", "fold"]
        for col in required_cols:
            assert col in result.predictions_df.columns, f"Missing column: {col}"


class TestRunBacktest:
    """Tests for run_backtest function using training_parquet fixture."""

    def test_run_backtest_single_fold_with_3_seasons(self, training_parquet):
        """run_backtest with 3-season data produces 1 fold (min_train_seasons=2)."""
        from server.pipeline.backtest import run_backtest
        result = run_backtest(parquet_path=training_parquet, min_train_seasons=2)
        assert result.n_folds == 1, f"Expected 1 fold, got {result.n_folds}"

    def test_fold_train_val_split_correct(self, training_parquet):
        """Each fold's train_df covers exactly [0:N] seasons and val_df is [N+1]."""
        from server.pipeline.backtest import run_backtest
        result = run_backtest(parquet_path=training_parquet, min_train_seasons=2)
        assert len(result.fold_summaries) == 1
        fold0 = result.fold_summaries[0]
        # First fold trains on first 2 seasons, validates on 3rd
        assert fold0["train_seasons"] == ["2021-22", "2022-23"]
        assert fold0["val_season"] == "2023-24"

    def test_predictions_df_required_columns(self, training_parquet):
        """Per-prediction DataFrame has all required columns."""
        from server.pipeline.backtest import run_backtest
        result = run_backtest(parquet_path=training_parquet, min_train_seasons=2)
        required_cols = ["player_id", "game_id", "season", "stat_type",
                         "line_value", "hit", "predicted_proba", "fold"]
        for col in required_cols:
            assert col in result.predictions_df.columns, f"Missing column: {col}"

    def test_predicted_proba_in_valid_range(self, training_parquet):
        """predicted_proba values are between 0 and 1 (calibrated probabilities)."""
        from server.pipeline.backtest import run_backtest
        result = run_backtest(parquet_path=training_parquet, min_train_seasons=2)
        probs = result.predictions_df["predicted_proba"]
        assert probs.min() >= 0.0, f"Min prob < 0: {probs.min()}"
        assert probs.max() <= 1.0, f"Max prob > 1: {probs.max()}"

    def test_no_temporal_leakage(self, training_parquet):
        """No temporal leakage: each fold's train data precedes its val season."""
        from server.pipeline.backtest import run_backtest
        result = run_backtest(parquet_path=training_parquet, min_train_seasons=2)
        for fold_summary in result.fold_summaries:
            train_seasons = fold_summary["train_seasons"]
            val_season = fold_summary["val_season"]
            # All train seasons must start before val season
            val_start_year = int(val_season.split("-")[0])
            for ts in train_seasons:
                assert int(ts.split("-")[0]) < val_start_year, \
                    f"Train season {ts} not before val {val_season} — temporal leakage!"

    def test_raises_value_error_with_insufficient_seasons(self, training_parquet):
        """run_backtest with min_train_seasons=2 on 2-season data raises ValueError."""
        from server.pipeline.backtest import run_backtest
        # Create 2-season data
        df = pd.read_parquet(training_parquet)
        df_2season = df[df["season"].isin(["2021-22", "2022-23"])]
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
            tmp_path = f.name
        df_2season.to_parquet(tmp_path, index=False)
        try:
            with pytest.raises(ValueError, match="walk-forward"):
                run_backtest(parquet_path=tmp_path, min_train_seasons=2)
        finally:
            os.unlink(tmp_path)

    def test_result_seasons_matches_input(self, training_parquet):
        """result.seasons matches the input data seasons."""
        from server.pipeline.backtest import run_backtest
        result = run_backtest(parquet_path=training_parquet, min_train_seasons=2)
        expected = ["2021-22", "2022-23", "2023-24"]
        assert result.seasons == expected, f"Expected {expected}, got {result.seasons}"

    def test_predictions_have_fold_numbers(self, training_parquet):
        """Each prediction row has a fold number matching its validation fold."""
        from server.pipeline.backtest import run_backtest
        result = run_backtest(parquet_path=training_parquet, min_train_seasons=2)
        assert "fold" in result.predictions_df.columns
        # With 3 seasons and min_train=2, we get fold 1
        assert result.predictions_df["fold"].nunique() == 1
        assert result.predictions_df["fold"].iloc[0] == 1
