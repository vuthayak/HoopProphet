import logging
import os
import time

from server.pipeline.feature_config import MIN_GAMES_PER_SEASON, PARQUET_PATH
from server.pipeline.db.queries import (
    get_game_logs_df,
    get_players_df,
    get_team_stats_df,
    get_teams_df,
)
from server.pipeline.processors.contextual_features import compute_contextual_features
from server.pipeline.processors.matchup_features import compute_matchup_features
from server.pipeline.processors.rolling_features import compute_rolling_features
from server.pipeline.processors.target_generator import generate_targets

logger = logging.getLogger(__name__)


def run_feature_pipeline(conn, output_path: str | None = None) -> dict:
    """Run the full feature engineering pipeline and persist parquet output."""
    start = time.time()
    output_path = output_path or PARQUET_PATH

    game_logs_df = get_game_logs_df(conn)
    team_stats_df = get_team_stats_df(conn)
    players_df = get_players_df(conn)
    teams_df = get_teams_df(conn)
    logger.info(
        "Loaded %d game logs, %d team stats, %d players, %d teams",
        len(game_logs_df),
        len(team_stats_df),
        len(players_df),
        len(teams_df),
    )

    played_df = game_logs_df[game_logs_df["is_dnp"] == 0].copy()
    logger.info(
        "Filtered to %d played games (excluded %d DNPs)",
        len(played_df),
        len(game_logs_df) - len(played_df),
    )

    games_per_player_season = played_df.groupby(["player_id", "season"]).size()
    valid_pairs = games_per_player_season[games_per_player_season >= MIN_GAMES_PER_SEASON].index
    before_count = len(played_df)
    played_df = played_df.set_index(["player_id", "season"]).loc[valid_pairs].reset_index()
    logger.info(
        "Minimum games filter (%d): %d -> %d rows (%d player-seasons)",
        MIN_GAMES_PER_SEASON,
        before_count,
        len(played_df),
        len(valid_pairs),
    )

    logger.info("Computing rolling features...")
    played_df = compute_rolling_features(played_df)

    logger.info("Computing contextual features...")
    played_df = compute_contextual_features(played_df, team_stats_df, teams_df, players_df)

    logger.info("Computing matchup features...")
    all_played = game_logs_df[game_logs_df["is_dnp"] == 0].copy()
    played_df = compute_matchup_features(played_df, all_played)

    logger.info("Generating binary targets...")
    long_df = generate_targets(played_df)
    logger.info(
        "Generated %d target rows across %d stat types",
        len(long_df),
        long_df["stat_type"].nunique() if not long_df.empty else 0,
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    long_df.to_parquet(output_path, engine="pyarrow", compression="snappy", index=False)
    elapsed = time.time() - start
    logger.info(
        "Feature matrix written: %d rows, %d columns -> %s (%.1fs)",
        len(long_df),
        len(long_df.columns),
        output_path,
        elapsed,
    )

    return {
        "rows": len(long_df),
        "columns": len(long_df.columns),
        "stat_types": int(long_df["stat_type"].nunique()) if not long_df.empty else 0,
        "players": int(long_df["player_id"].nunique()) if not long_df.empty else 0,
        "output_path": output_path,
        "elapsed_seconds": round(elapsed, 1),
    }
