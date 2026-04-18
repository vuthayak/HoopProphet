"""Integration tests for backtest_cli.py.

Tests the end-to-end back-test CLI pipeline following the train_cli.py pattern.
"""

import json
import os

import numpy as np
import pandas as pd
import pytest

from server.pipeline.backtest_cli import run_backtest_pipeline


class TestRunBacktestPipeline:
    """Test 1: run_backtest_pipeline with training_parquet fixture returns dict."""

    def test_returns_dict_with_required_keys(self, training_parquet, tmp_path):
        """run_backtest_pipeline returns dict with artifact_path (None), metrics_log_path,
        predictions_path, n_folds, seasons."""
        metrics_dir = str(tmp_path / "metrics")
        result = run_backtest_pipeline(
            parquet_path=training_parquet,
            output_dir=metrics_dir,
            min_train_seasons=2,
        )

        assert isinstance(result, dict)
        assert "artifact_path" in result
        assert result["artifact_path"] is None  # backtest has no artifact
        assert "metrics_log_path" in result
        assert "predictions_path" in result
        assert "n_folds" in result
        assert "seasons" in result
        assert result["n_folds"] >= 1
        assert len(result["seasons"]) >= 3  # training_parquet has 3 seasons

    def test_pipeline_with_default_arguments(self, training_parquet, tmp_path):
        """run_backtest_pipeline works with all default arguments."""
        metrics_dir = str(tmp_path / "metrics")
        result = run_backtest_pipeline(
            parquet_path=training_parquet,
            output_dir=metrics_dir,
        )

        assert result["n_folds"] >= 1
        assert os.path.exists(result["metrics_log_path"])
        assert os.path.exists(result["predictions_path"])


class TestCLIHelp:
    """Test 2: backtest --help flag shows expected arguments."""

    def test_help_shows_backtest_flag(self):
        """--help includes --backtest flag."""
        import subprocess
        result = subprocess.run(
            ["python", "-m", "server.pipeline.backtest_cli", "--help"],
            capture_output=True,
            text=True,
        )
        output = result.stdout + result.stderr
        assert "--backtest" in output

    def test_help_shows_parquet_path(self):
        """--help includes --parquet-path."""
        import subprocess
        result = subprocess.run(
            ["python", "-m", "server.pipeline.backtest_cli", "--help"],
            capture_output=True,
            text=True,
        )
        output = result.stdout + result.stderr
        assert "--parquet-path" in output

    def test_help_shows_verbose_flag(self):
        """--help includes -v/--verbose flag."""
        import subprocess
        result = subprocess.run(
            ["python", "-m", "server.pipeline.backtest_cli", "--help"],
            capture_output=True,
            text=True,
        )
        output = result.stdout + result.stderr
        assert "-v" in output or "--verbose" in output


class TestJSONOutput:
    """Test 3 & 5: JSON output has all required sections."""

    def test_json_has_all_required_sections(self, training_parquet, tmp_path):
        """JSON output contains fold_metrics, season_breakdown, calibration,
        roi, confidence_intervals sections."""
        metrics_dir = str(tmp_path / "metrics")
        result = run_backtest_pipeline(
            parquet_path=training_parquet,
            output_dir=metrics_dir,
            min_train_seasons=2,
        )

        with open(result["metrics_log_path"], "r") as f:
            data = json.load(f)

        # Top-level sections per D-01 contract
        assert "backtest_metadata" in data
        assert "fold_metrics" in data
        assert "season_breakdown" in data
        assert "overall_calibration" in data
        assert "per_stat_calibration" in data
        assert "roi" in data
        assert "confidence_intervals" in data

    def test_json_metadata_has_required_fields(self, training_parquet, tmp_path):
        """backtest_metadata contains n_folds, seasons, min_train_seasons,
        breakeven_threshold, vig_description, n_total_predictions."""
        metrics_dir = str(tmp_path / "metrics")
        result = run_backtest_pipeline(
            parquet_path=training_parquet,
            output_dir=metrics_dir,
            min_train_seasons=2,
        )

        with open(result["metrics_log_path"], "r") as f:
            data = json.load(f)

        meta = data["backtest_metadata"]
        assert "n_folds" in meta
        assert "seasons" in meta
        assert "min_train_seasons" in meta
        assert "breakeven_threshold" in meta
        assert "vig_description" in meta
        assert "n_total_predictions" in meta
        assert "n_predictions_per_stat" in meta
        assert "timestamp" in meta


class TestParquetOutput:
    """Test 4 & 6: Parquet output has per-prediction rows."""

    def test_parquet_has_required_columns(self, training_parquet, tmp_path):
        """Parquet file has player_id, game_id, season, stat_type, line_value,
        hit, predicted_proba, fold columns."""
        metrics_dir = str(tmp_path / "metrics")
        result = run_backtest_pipeline(
            parquet_path=training_parquet,
            output_dir=metrics_dir,
            min_train_seasons=2,
        )

        df = pd.read_parquet(result["predictions_path"])
        required_cols = [
            "player_id", "game_id", "season", "stat_type",
            "line_value", "hit", "predicted_proba", "fold",
        ]
        for col in required_cols:
            assert col in df.columns, f"Missing column: {col}"

    def test_parquet_round_trip(self, training_parquet, tmp_path):
        """Parquet round-trips correctly: save, read back, columns and row count match."""
        metrics_dir = str(tmp_path / "metrics")
        result = run_backtest_pipeline(
            parquet_path=training_parquet,
            output_dir=metrics_dir,
            min_train_seasons=2,
        )

        df = pd.read_parquet(result["predictions_path"])

        # Columns present
        assert len(df.columns) >= 8

        # Row count > 0
        assert len(df) > 0

        # Values in expected ranges
        assert df["predicted_proba"].between(0, 1).all()
        assert df["hit"].isin([0, 1]).all()
        assert df["fold"].between(1, 4).all()
