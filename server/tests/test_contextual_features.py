import pandas as pd

from server.pipeline.db.queries import (
    get_game_logs_df,
    get_players_df,
    get_team_stats_df,
    get_teams_df,
)
from server.pipeline.feature_config import PRIMARY_STATS
from server.pipeline.processors.contextual_features import compute_contextual_features
from server.pipeline.processors.matchup_features import compute_matchup_features
from server.pipeline.processors.rolling_features import compute_rolling_features


def _prepare_data(feature_db):
    game_logs = get_game_logs_df(feature_db)
    played = game_logs[game_logs["is_dnp"] == 0].copy()
    played = compute_rolling_features(played)
    team_stats = get_team_stats_df(feature_db)
    teams = get_teams_df(feature_db)
    players = get_players_df(feature_db)
    return played, game_logs, team_stats, teams, players


def test_rest_days_computed(feature_db):
    played, _, team_stats, teams, players = _prepare_data(feature_db)
    out = compute_contextual_features(played, team_stats, teams, players)

    assert "rest_days" in out.columns

    first_by_player = out.sort_values("game_date").groupby("player_id").first()
    assert (first_by_player["rest_days"] == 7).all()

    lebron_b2b_game = out[(out["player_id"] == 2544) & (out["game_id"] == "0022301011")]
    assert lebron_b2b_game["rest_days"].iloc[0] == 1
    assert out["rest_days"].between(1, 14).all()


def test_b2b_flag_correct(feature_db):
    played, _, team_stats, teams, players = _prepare_data(feature_db)
    out = compute_contextual_features(played, team_stats, teams, players)

    assert "is_b2b" in out.columns
    assert ((out["is_b2b"] == 1) == (out["rest_days"] == 1)).all()
    assert out["is_b2b"].isin([0, 1]).all()
    assert (out["is_b2b"] == 1).any()


def test_home_away_parsed(feature_db):
    played, _, team_stats, teams, players = _prepare_data(feature_db)
    out = compute_contextual_features(played, team_stats, teams, players)

    assert "is_home" in out.columns
    assert out.loc[out["matchup"] == "DEN vs. LAL", "is_home"].eq(1).all()
    assert out.loc[out["matchup"] == "DEN @ PHX", "is_home"].eq(0).all()
    assert out["is_home"].isin([0, 1]).all()


def test_opponent_defense_joined(feature_db):
    played, _, team_stats, teams, players = _prepare_data(feature_db)
    out = compute_contextual_features(played, team_stats, teams, players)

    assert "opp_def_rating" in out.columns
    jokic_vs_lal = out[
        (out["player_id"] == 203999)
        & (out["season"] == "2023-24")
        & (out["matchup"] == "DEN vs. LAL")
    ]
    assert jokic_vs_lal["opp_def_rating"].iloc[0] == 110.3
    known_opponents = out[out["opp_team_id"].isin([1610612743, 1610612747])]
    assert known_opponents["opp_def_rating"].notna().all()


def test_pace_features_joined(feature_db):
    played, _, team_stats, teams, players = _prepare_data(feature_db)
    out = compute_contextual_features(played, team_stats, teams, players)

    assert "opp_pace" in out.columns
    assert "team_pace" in out.columns

    jokic_vs_lal = out[
        (out["player_id"] == 203999)
        & (out["season"] == "2023-24")
        & (out["matchup"] == "DEN vs. LAL")
    ]
    assert jokic_vs_lal["opp_pace"].iloc[0] == 99.8
    assert jokic_vs_lal["team_pace"].iloc[0] == 98.1
    known_opponents = out[out["opp_team_id"].isin([1610612743, 1610612747])]
    known_player_teams = out[out["player_team_id"].isin([1610612743, 1610612747])]
    assert known_opponents["opp_pace"].between(90, 110).all()
    assert known_player_teams["team_pace"].between(90, 110).all()


def test_position_joined(feature_db):
    played, _, team_stats, teams, players = _prepare_data(feature_db)
    out = compute_contextual_features(played, team_stats, teams, players)

    assert "position" in out.columns
    assert out.loc[out["player_id"] == 203999, "position"].eq("C").all()
    assert out.loc[out["player_id"] == 2544, "position"].eq("F").all()


def test_matchup_avg_columns_exist(feature_db):
    played, game_logs, team_stats, teams, players = _prepare_data(feature_db)
    contextual = compute_contextual_features(played, team_stats, teams, players)
    out = compute_matchup_features(contextual, game_logs)

    for stat in PRIMARY_STATS:
        assert f"matchup_avg_{stat}" in out.columns


def test_matchup_avg_values_correct(feature_db):
    played, game_logs, team_stats, teams, players = _prepare_data(feature_db)
    contextual = compute_contextual_features(played, team_stats, teams, players)
    out = compute_matchup_features(contextual, game_logs)

    # First 2023-24 Jokic vs LAL game should use the prior-season 2022-23 Jokic vs LAL game.
    first_2023_meeting = out[(out["player_id"] == 203999) & (out["game_id"] == "0022300001")].iloc[0]
    assert first_2023_meeting["matchup_avg_pts"] == 28


def test_matchup_history_2_season_limit(feature_db):
    played, game_logs, team_stats, teams, players = _prepare_data(feature_db)
    contextual = compute_contextual_features(played, team_stats, teams, players)
    out = compute_matchup_features(contextual, game_logs).sort_values("game_date")

    target = out[(out["player_id"] == 203999) & (out["game_id"] == "0022300004")].iloc[0]
    # Prior Jokic vs LAL games before this date: 2023-03-10 and 2023-10-25
    assert target["matchup_avg_pts"] == (28 + 29) / 2


def test_matchup_avg_nan_for_first_meeting(feature_db):
    played, game_logs, team_stats, teams, players = _prepare_data(feature_db)
    contextual = compute_contextual_features(played, team_stats, teams, players)
    out = compute_matchup_features(contextual, game_logs).sort_values("game_date")

    first_jokic_vs_lal = out[(out["player_id"] == 203999) & (out["game_id"] == "0022200901")].iloc[0]
    assert pd.isna(first_jokic_vs_lal["matchup_avg_pts"])
