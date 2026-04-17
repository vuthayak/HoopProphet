import pandas as pd
import pytest
from server.pipeline.splits import walk_forward_split, get_seasons_sorted


def test_get_seasons_sorted_chronological(training_parquet):
    from server.pipeline.dataset import load_training_data
    df = load_training_data(training_parquet)
    seasons = get_seasons_sorted(df)
    assert seasons == ["2021-22", "2022-23", "2023-24"]
    # Verify chronological order: start year of each season increases
    years = [int(s.split("-")[0]) for s in seasons]
    assert years == sorted(years)


def test_walk_forward_split_fold_count(training_parquet):
    from server.pipeline.dataset import load_training_data
    df = load_training_data(training_parquet)
    # With 3 seasons and min_train_seasons=2, expect 1 fold
    folds = walk_forward_split(df, min_train_seasons=2)
    assert len(folds) == 1, "With 3 seasons and min_train=2, expect 1 fold"
    # With 3 seasons and min_train_seasons=1, expect 2 folds
    folds = walk_forward_split(df, min_train_seasons=1)
    assert len(folds) == 2, "With 3 seasons and min_train=1, expect 2 folds"


def test_walk_forward_split_no_temporal_leakage(training_parquet):
    from server.pipeline.dataset import load_training_data
    df = load_training_data(training_parquet)
    folds = walk_forward_split(df, min_train_seasons=2)
    for train_df, val_df in folds:
        train_seasons = set(train_df["season"].unique())
        val_seasons = set(val_df["season"].unique())
        # Validation seasons must be chronologically AFTER all training seasons
        train_max_year = max(int(s.split("-")[0]) for s in train_seasons)
        val_min_year = min(int(s.split("-")[0]) for s in val_seasons)
        assert val_min_year > train_max_year, (
            f"Validation season {val_seasons} must be after training seasons {train_seasons}"
        )
        # No overlap at all
        assert train_seasons.isdisjoint(val_seasons), (
            f"Train and validation seasons must not overlap: {train_seasons} ∩ {val_seasons}"
        )


def test_walk_forward_split_no_row_leakage(training_parquet):
    from server.pipeline.dataset import load_training_data
    df = load_training_data(training_parquet)
    folds = walk_forward_split(df, min_train_seasons=2)
    for train_df, val_df in folds:
        train_game_ids = set(train_df["game_id"].unique())
        val_game_ids = set(val_df["game_id"].unique())
        overlap = train_game_ids & val_game_ids
        assert len(overlap) == 0, (
            f"No game should appear in both train and validation: {len(overlap)} overlapping"
        )


def test_walk_forward_split_insufficient_seasons(training_parquet):
    from server.pipeline.dataset import load_training_data
    df = load_training_data(training_parquet)
    # Filter to only 2 seasons (need at least 3 for min_train_seasons=2)
    df_2 = df[df["season"].isin(["2022-23", "2023-24"])].copy()
    with pytest.raises(ValueError, match="at least"):
        walk_forward_split(df_2, min_train_seasons=2)


def test_walk_forward_split_expanding_window(training_parquet):
    from server.pipeline.dataset import load_training_data
    df = load_training_data(training_parquet)
    folds = walk_forward_split(df, min_train_seasons=1)
    # Each subsequent fold should have MORE training rows
    train_sizes = [len(train) for train, _ in folds]
    for i in range(1, len(train_sizes)):
        assert train_sizes[i] > train_sizes[i-1], (
            f"Fold {i+1} should have more training data than fold {i}"
        )