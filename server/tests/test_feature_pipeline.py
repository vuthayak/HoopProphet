import pandas as pd

from server.pipeline.feature_config import ALL_TARGET_STATS, MIN_GAMES_PER_SEASON, N_THRESHOLD_LINES
from server.pipeline.features import run_feature_pipeline


def _run_and_read(feature_db, tmp_path):
    output_path = tmp_path / "features.parquet"
    result = run_feature_pipeline(feature_db, output_path=str(output_path))
    df = pd.read_parquet(output_path)
    return result, output_path, df


def test_full_pipeline_produces_parquet(feature_db, tmp_path):
    result, output_path, _ = _run_and_read(feature_db, tmp_path)

    assert output_path.exists()
    assert {"rows", "columns", "stat_types", "players", "output_path"}.issubset(result.keys())
    assert result["rows"] > 0
    assert result["stat_types"] == len(ALL_TARGET_STATS)
    assert result["players"] >= 1


def test_parquet_schema_correct(feature_db, tmp_path):
    _, _, df = _run_and_read(feature_db, tmp_path)

    assert "stat_type" in df.columns
    assert pd.api.types.is_integer_dtype(df["stat_type"])
    assert df["stat_type"].between(0, len(ALL_TARGET_STATS) - 1).all()
    assert "line_value" in df.columns
    assert pd.api.types.is_float_dtype(df["line_value"])
    assert (df["line_value"] > 0).all()
    assert "hit" in df.columns
    assert set(df["hit"].unique()).issubset({0, 1})
    for required in ["player_id", "game_id", "season", "game_date", "pts_avg_L5"]:
        assert required in df.columns


def test_long_format_multiple_rows_per_game(feature_db, tmp_path):
    _, _, df = _run_and_read(feature_db, tmp_path)

    group_sizes = df.groupby(["player_id", "game_id"]).size()
    expected = len(ALL_TARGET_STATS) * N_THRESHOLD_LINES
    assert (group_sizes == expected).all()
    assert set(df["stat_type"].unique()) == set(range(len(ALL_TARGET_STATS)))


def test_no_temporal_leakage_end_to_end(feature_db, tmp_path):
    _, _, df = _run_and_read(feature_db, tmp_path)
    per_game = (
        df.sort_values(["player_id", "game_date"])
        .drop_duplicates(subset=["player_id", "game_id"])
    )

    for player_id in per_game["player_id"].unique():
        history = pd.read_sql_query(
            "SELECT game_id, game_date, pts FROM player_game_logs "
            "WHERE player_id = ? AND is_dnp = 0 ORDER BY game_date",
            feature_db,
            params=[int(player_id)],
        )
        history["pts_avg_L5_expected"] = (
            history["pts"].rolling(5, min_periods=1).mean().shift(1)
        )

        merged = per_game[per_game["player_id"] == player_id][["game_id", "pts_avg_L5"]].merge(
            history[["game_id", "pts_avg_L5_expected"]],
            on="game_id",
            how="left",
        )
        assert merged["pts_avg_L5_expected"].notna().all()
        assert (merged["pts_avg_L5"] - merged["pts_avg_L5_expected"]).abs().max() < 1e-9


def test_binary_target_values_correct(feature_db, tmp_path):
    _, _, df = _run_and_read(feature_db, tmp_path)

    pts_row = df[df["stat_type"] == 0].iloc[0]
    actual = feature_db.execute(
        "SELECT pts FROM player_game_logs WHERE player_id = ? AND game_id = ?",
        (int(pts_row["player_id"]), str(pts_row["game_id"])),
    ).fetchone()[0]
    expected_hit = int(actual > pts_row["line_value"])
    assert int(pts_row["hit"]) == expected_hit


def test_min_games_filter_applied(feature_db, tmp_path):
    _, _, df = _run_and_read(feature_db, tmp_path)

    assert not ((df["player_id"] == 203999) & (df["season"] == "2022-23")).any()

    season_counts = (
        df[["player_id", "season"]]
        .drop_duplicates()
        .groupby(["player_id", "season"])
        .size()
        .index
    )
    for player_id, season in season_counts:
        games = feature_db.execute(
            "SELECT COUNT(*) FROM player_game_logs WHERE player_id = ? AND season = ? AND is_dnp = 0",
            (int(player_id), str(season)),
        ).fetchone()[0]
        assert games >= MIN_GAMES_PER_SEASON


def test_threshold_lines_are_half_point_rounded(feature_db, tmp_path):
    _, _, df = _run_and_read(feature_db, tmp_path)

    assert (((df["line_value"] * 2) % 1) == 0).all()
    assert (df["line_value"] >= 0.5).all()


def test_pipeline_returns_summary(feature_db, tmp_path):
    result, output_path, _ = _run_and_read(feature_db, tmp_path)

    assert isinstance(result["rows"], int) and result["rows"] > 0
    assert isinstance(result["columns"], int) and result["columns"] > 10
    assert isinstance(result["elapsed_seconds"], float) and result["elapsed_seconds"] >= 0
    assert result["output_path"] == str(output_path)
