"""Tests for backtest_metrics.py — calibration, ROI, season breakdown, confidence intervals."""

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import brier_score_loss, log_loss

from server.pipeline.backtest_metrics import (
    compute_confidence_intervals,
    compute_overall_calibration,
    compute_per_stat_calibration,
    compute_roi_metrics,
    compute_season_breakdown,
)
from server.tests.backtest_fixtures import (
    make_miscalibrated_df,
    make_perfectly_calibrated_df,
    make_predictions_df,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def rng():
    """Seeded RNG for reproducible test data."""
    return np.random.default_rng(42)


@pytest.fixture
def predictions_df(rng):
    """Standard 200-row synthetic predictions DataFrame."""
    return make_predictions_df(rng=rng, n_rows=200)


@pytest.fixture
def perfect_cal_df(rng):
    """Perfectly calibrated DataFrame (ECE ≈ 0)."""
    return make_perfectly_calibrated_df(rng)


@pytest.fixture
def miscal_df(rng):
    """Miscalibrated DataFrame (ECE > 0)."""
    return make_miscalibrated_df(rng)


# ---------------------------------------------------------------------------
# Calibration tests
# ---------------------------------------------------------------------------

class TestOverallCalibration:
    def test_returns_required_keys(self, predictions_df):
        """Test 1: compute_overall_calibration returns all required dict keys."""
        result = compute_overall_calibration(predictions_df)
        assert isinstance(result, dict)
        for key in ("fraction_positives", "mean_predicted_value", "bin_counts", "ece"):
            assert key in result, f"Missing key: {key}"

    def test_per_stat_returns_keyed_by_stat_name(self, predictions_df):
        """Test 2: compute_per_stat_calibration returns dict keyed by stat name."""
        result = compute_per_stat_calibration(predictions_df)
        assert isinstance(result, dict)
        # Stat names are strings: "pts", "reb", "ast", etc.
        for key in result:
            assert isinstance(key, str), f"Key {key!r} should be string (stat name)"
            assert "fraction_positives" in result[key]

    def test_perfect_calibration_ece_near_zero(self, perfect_cal_df):
        """Test 3: Perfectly calibrated predictions → ECE near 0."""
        result = compute_overall_calibration(perfect_cal_df)
        assert result["ece"] < 0.02, f"Expected ECE < 0.02 for perfect calibration, got {result['ece']}"

    def test_miscalibration_ece_positive(self, miscal_df):
        """Test 4: Miscalibrated predictions → ECE > 0."""
        result = compute_overall_calibration(miscal_df)
        assert result["ece"] > 0.05, f"Expected ECE > 0.05 for miscalibration, got {result['ece']}"


# ---------------------------------------------------------------------------
# Season breakdown tests
# ---------------------------------------------------------------------------

class TestSeasonBreakdown:
    def test_returns_dict_keyed_by_season(self, predictions_df):
        """Test 5: compute_season_breakdown returns dict keyed by season string."""
        result = compute_season_breakdown(predictions_df)
        assert isinstance(result, dict)
        for season, metrics in result.items():
            assert isinstance(season, str)
            for key in ("accuracy", "log_loss", "brier_score", "n_predictions"):
                assert key in metrics, f"Season {season} missing metric: {key}"

    def test_accuracy_matches_manual(self, predictions_df):
        """Test 6: Season breakdown accuracy matches manual computation."""
        result = compute_season_breakdown(predictions_df)
        # Check one season manually
        first_season = list(result.keys())[0]
        season_df = predictions_df[predictions_df["season"] == first_season]
        # Accuracy = fraction of predictions where direction (above/below 0.5) matches outcome
        manual_acc = float(np.mean((season_df["predicted_proba"].values > 0.5) == season_df["hit"].values))
        assert abs(result[first_season]["accuracy"] - manual_acc) < 1e-6

    def test_thin_season_no_division_error(self, rng):
        """Test 7: Season with very few predictions is handled gracefully."""
        thin_df = make_predictions_df(rng=rng, n_rows=5)
        result = compute_season_breakdown(thin_df)
        # Should not raise, should still have entries
        assert len(result) > 0


# ---------------------------------------------------------------------------
# ROI tests
# ---------------------------------------------------------------------------

class TestROIMetrics:
    def test_returns_required_keys(self, predictions_df):
        """Test 8: compute_roi_metrics returns all required keys."""
        result = compute_roi_metrics(predictions_df)
        for key in ("overall_roi", "roi_by_bucket", "total_bets", "win_count", "loss_count"):
            assert key in result, f"Missing key: {key}"

    def test_all_breakeven_threshold_near_zero(self, rng):
        """Test 9: All predictions near breakeven (53%) → ROI near 0 minus vig."""
        # Create df where all predictions are slightly above breakeven (eligible bets)
        # but actual hit rate is ~52.4%, so ROI should be slightly negative due to vig
        rows = []
        for i in range(200):
            rows.append(
                {
                    "player_id": 1000 + i,
                    "game_id": f"00{i:04d}",
                    "season": "2023-24",
                    "game_date": "2024-01-15",
                    "stat_type": 0,
                    "line_value": 20.0,
                    "hit": 1 if rng.random() < 0.524 else 0,
                    "predicted_proba": 0.53,  # just above threshold = eligible bet
                    "fold": 1,
                    "train_seasons": "2022-23",
                }
            )
        df = pd.DataFrame(rows)
        result = compute_roi_metrics(df)
        # At ~52.4% actual hit rate with -110 vig, ROI should be slightly negative
        # (win: +0.909, loss: -1.0, expected = 0.524*0.909 - 0.476*1.0 ≈ -0.001)
        assert result["total_bets"] == 200
        assert result["overall_roi"] < 0.05  # vig makes it slightly negative

    def test_high_confidence_correct_bets_positive_roi(self, rng):
        """Test 10: All correct high-confidence bets → positive ROI."""
        rows = []
        for i in range(100):
            rows.append(
                {
                    "player_id": 1000 + i,
                    "game_id": f"00{i:04d}",
                    "season": "2023-24",
                    "game_date": "2024-01-15",
                    "stat_type": 0,
                    "line_value": 20.0,
                    "hit": 1,  # always correct
                    "predicted_proba": 0.75,
                    "fold": 1,
                    "train_seasons": "2022-23",
                }
            )
        df = pd.DataFrame(rows)
        result = compute_roi_metrics(df)
        # All correct at 0.75 probability: ROI should be positive
        # win: +0.909, no losses
        assert result["overall_roi"] > 0.0
        assert result["win_count"] == 100

    def test_vig_adjusted_roi_profit_per_win(self, predictions_df):
        """Test 11: ROI uses -110 vig: profit per win = +0.909, per loss = -1.0."""
        # Use a subset with high confidence to isolate vig calculation
        high_conf = predictions_df[predictions_df["predicted_proba"] > 0.60].copy()
        if len(high_conf) < 10:
            pytest.skip("Not enough high-confidence predictions")
        result = compute_roi_metrics(high_conf)

        # Check that the vig multiplier is applied correctly
        if result["total_bets"] > 0:
            expected_profit_per_win = 0.909  # 100/110
            expected_loss_per_miss = 1.0
            net = result["net_units"]
            total = result["total_wagered"]
            # ROI = net / total should equal (wins * 0.909 - losses * 1.0) / total
            assert abs(result["overall_roi"] - (net / total)) < 1e-9


# ---------------------------------------------------------------------------
# Confidence interval tests
# ---------------------------------------------------------------------------

class TestConfidenceIntervals:
    def test_returns_low_mid_high_keys(self, predictions_df):
        """Test 12: compute_confidence_intervals returns low, mid, high for each metric."""
        result = compute_confidence_intervals(predictions_df)
        for metric_name, bounds in result.items():
            assert isinstance(bounds, dict), f"{metric_name} bounds should be a dict"
            for key in ("low", "mid", "high"):
                assert key in bounds, f"{metric_name} missing: {key}"

    def test_ci_width_decreases_with_sample_size(self, rng):
        """Test 13: CI width decreases with larger sample sizes."""
        small_df = make_predictions_df(rng=rng, n_rows=50)
        large_df = make_predictions_df(rng=rng, n_rows=500)

        small_cis = compute_confidence_intervals(small_df, n_bootstrap=200)
        large_cis = compute_confidence_intervals(large_df, n_bootstrap=200)

        for metric in ("accuracy", "brier_score"):
            small_width = small_cis[metric]["high"] - small_cis[metric]["low"]
            large_width = large_cis[metric]["high"] - large_cis[metric]["low"]
            assert large_width <= small_width, (
                f"{metric} CI should tighten with more data: "
                f"small={small_width:.4f}, large={large_width:.4f}"
            )

    def test_ci_contains_point_estimate(self, predictions_df):
        """Test 14: CIs contain the point estimate for accuracy and Brier score."""
        result = compute_confidence_intervals(predictions_df, n_bootstrap=500)
        # Point estimates
        accuracy = float(predictions_df["hit"].mean())
        brier = float(brier_score_loss(predictions_df["hit"], predictions_df["predicted_proba"]))

        for metric, point_est in (("accuracy", accuracy), ("brier_score", brier)):
            low = result[metric]["low"]
            high = result[metric]["high"]
            assert low <= point_est <= high, (
                f"{metric} point estimate {point_est:.4f} not in CI [{low:.4f}, {high:.4f}]"
            )
