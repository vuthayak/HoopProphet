import pandas as pd
import pytest

from server.pipeline.db.queries import get_game_logs_df
from server.pipeline.feature_config import (
    COMBO_STATS,
    PRIMARY_STATS,
    SECONDARY_STATS,
    WINDOWS_PRIMARY,
    WINDOWS_SECONDARY,
)
from server.pipeline.processors.rolling_features import compute_rolling_features


def _played_logs(feature_db):
    logs = get_game_logs_df(feature_db)
    return logs[logs["is_dnp"] == 0].copy()


def _rolling_columns(result: pd.DataFrame):
    return [
        col
        for col in result.columns
        if "_avg_L" in col or "_std_L" in col or "_season_avg" in col or col == "games_played_season"
    ]


def test_rolling_averages_columns_exist(feature_db):
    result = compute_rolling_features(_played_logs(feature_db))

    for stat in PRIMARY_STATS:
        for window in WINDOWS_PRIMARY:
            assert f"{stat}_avg_L{window}" in result.columns

    for stat in SECONDARY_STATS:
        for window in WINDOWS_SECONDARY:
            assert f"{stat}_avg_L{window}" in result.columns
        assert f"{stat}_avg_L20" not in result.columns


def test_rolling_averages_values_correct(feature_db):
    played = _played_logs(feature_db)
    result = compute_rolling_features(played)

    jokic = result[result["player_id"] == 203999].sort_values("game_date").reset_index(drop=True)
    expected = jokic.loc[:4, "pts"].mean()
    assert jokic.loc[5, "pts_avg_L5"] == pytest.approx(expected)


def test_rolling_std_computed(feature_db):
    result = compute_rolling_features(_played_logs(feature_db))
    assert "pts_std_L5" in result.columns

    non_nan = result["pts_std_L5"].dropna()
    assert (non_nan >= 0).all()

    jokic = result[result["player_id"] == 203999].sort_values("game_date").reset_index(drop=True)
    assert pd.isna(jokic.loc[0, "pts_std_L5"])
    assert not pd.isna(jokic.loc[2, "pts_std_L5"])


def test_combo_stats_computed(feature_db):
    played = _played_logs(feature_db)
    result = compute_rolling_features(played)

    assert "pra_avg_L5" in result.columns
    assert "pa_avg_L10" in result.columns
    assert "pr_avg_L20" in result.columns

    jokic_played = played[played["player_id"] == 203999].sort_values("game_date").reset_index(drop=True)
    jokic_result = result[result["player_id"] == 203999].sort_values("game_date").reset_index(drop=True)

    expected_pra = (
        jokic_played.loc[:4, ["pts", "reb", "ast"]]
        .sum(axis=1)
        .mean()
    )
    assert jokic_result.loc[5, "pra_avg_L5"] == pytest.approx(expected_pra)


def test_dnp_excluded_from_input(feature_db):
    logs = get_game_logs_df(feature_db)
    assert (logs["is_dnp"] == 1).any()

    played = logs[logs["is_dnp"] == 0].copy()
    result = compute_rolling_features(played)

    assert len(result) == len(played)

    # For Jokic game index 5, verify DNP row did not contribute to the previous L5 window.
    jokic = result[result["player_id"] == 203999].sort_values("game_date").reset_index(drop=True)
    expected_without_dnp = jokic.loc[:4, "pts"].mean()
    assert jokic.loc[5, "pts_avg_L5"] == pytest.approx(expected_without_dnp)


def test_temporal_guard_first_game_is_nan(feature_db):
    result = compute_rolling_features(_played_logs(feature_db))
    rolling_cols = _rolling_columns(result)

    sorted_result = result.sort_values(["player_id", "game_date"])
    first_games = sorted_result.groupby("player_id", as_index=False).nth(0)
    assert first_games[rolling_cols].isna().all().all()


def test_season_avg_and_games_played(feature_db):
    result = compute_rolling_features(_played_logs(feature_db))
    assert "games_played_season" in result.columns
    assert "pts_season_avg" in result.columns

    jokic_2023 = (
        result[(result["player_id"] == 203999) & (result["season"] == "2023-24")]
        .sort_values("game_date")
        .reset_index(drop=True)
    )
    assert pd.isna(jokic_2023.loc[0, "games_played_season"])
    assert jokic_2023.loc[4, "games_played_season"] == pytest.approx(4.0)
    assert pd.isna(jokic_2023.loc[0, "pts_season_avg"])


def test_secondary_stats_fewer_windows(feature_db):
    result = compute_rolling_features(_played_logs(feature_db))
    assert "oreb_avg_L5" in result.columns
    assert "oreb_avg_L10" in result.columns
    assert "oreb_avg_L20" not in result.columns

