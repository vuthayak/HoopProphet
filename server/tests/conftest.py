import os
import shutil
import tempfile

import numpy as np
import pandas as pd
import pytest

from server.pipeline.feature_config import ALL_TARGET_STATS, STAT_TYPE_MAP
from server.pipeline.db.connection import get_connection
from server.pipeline.db.queries import insert_game_logs, insert_team_stats, upsert_player, upsert_team
from server.pipeline.db.schema import init_db


@pytest.fixture
def tmp_db():
    """Provide a temporary SQLite database with all tables created."""
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "test.db")
    conn = get_connection(db_path)
    init_db(conn)
    yield conn
    conn.close()
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture
def sample_game_log_df():
    """Return a DataFrame with 5 realistic game log rows."""
    return pd.DataFrame([
        {"player_id": 203999, "game_id": "0022300001", "season": "2023-24",
         "game_date": "2023-10-25", "matchup": "DEN vs. LAL", "wl": "W",
         "min": 35.0, "pts": 29.0, "reb": 12.0, "ast": 11.0, "stl": 1.0,
         "blk": 1.0, "fg3m": 2.0, "fgm": 11.0, "fga": 18.0, "ftm": 5.0,
         "fta": 6.0, "oreb": 2.0, "dreb": 10.0, "tov": 3.0, "pf": 2.0,
         "plus_minus": 15.0, "is_dnp": 0},
        {"player_id": 203999, "game_id": "0022300002", "season": "2023-24",
         "game_date": "2023-10-27", "matchup": "DEN @ PHX", "wl": "L",
         "min": 38.0, "pts": 25.0, "reb": 10.0, "ast": 8.0, "stl": 2.0,
         "blk": 0.0, "fg3m": 1.0, "fgm": 10.0, "fga": 20.0, "ftm": 4.0,
         "fta": 4.0, "oreb": 1.0, "dreb": 9.0, "tov": 4.0, "pf": 3.0,
         "plus_minus": -5.0, "is_dnp": 0},
        {"player_id": 203999, "game_id": "0022300003", "season": "2023-24",
         "game_date": "2023-10-30", "matchup": "DEN vs. MIN", "wl": "W",
         "min": 33.0, "pts": 32.0, "reb": 8.0, "ast": 7.0, "stl": 0.0,
         "blk": 2.0, "fg3m": 3.0, "fgm": 13.0, "fga": 22.0, "ftm": 3.0,
         "fta": 3.0, "oreb": 0.0, "dreb": 8.0, "tov": 2.0, "pf": 1.0,
         "plus_minus": 10.0, "is_dnp": 0},
        {"player_id": 203999, "game_id": "0022300004", "season": "2023-24",
         "game_date": "2023-11-01", "matchup": "DEN @ UTA", "wl": "W",
         "min": 30.0, "pts": 21.0, "reb": 14.0, "ast": 9.0, "stl": 1.0,
         "blk": 0.0, "fg3m": 0.0, "fgm": 9.0, "fga": 15.0, "ftm": 3.0,
         "fta": 4.0, "oreb": 3.0, "dreb": 11.0, "tov": 5.0, "pf": 4.0,
         "plus_minus": 8.0, "is_dnp": 0},
        {"player_id": 203999, "game_id": "0022300005", "season": "2023-24",
         "game_date": "2023-11-03", "matchup": "DEN vs. SAC", "wl": "L",
         "min": 36.0, "pts": 18.0, "reb": 11.0, "ast": 12.0, "stl": 3.0,
         "blk": 1.0, "fg3m": 1.0, "fgm": 7.0, "fga": 16.0, "ftm": 3.0,
         "fta": 5.0, "oreb": 1.0, "dreb": 10.0, "tov": 3.0, "pf": 2.0,
         "plus_minus": -3.0, "is_dnp": 0},
    ])


@pytest.fixture
def sample_team_stats_df():
    """Return a single-row DataFrame of team advanced stats."""
    return pd.DataFrame([{
        "TEAM_ID": 1610612739,
        "TEAM_NAME": "Cleveland Cavaliers",
        "DEF_RATING": 108.5,
        "OFF_RATING": 115.2,
        "NET_RATING": 6.7,
        "PACE": 99.3,
    }])


@pytest.fixture
def feature_db():
    """Provide a temporary DB preloaded with feature-engineering test data."""
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "feature.db")
    conn = get_connection(db_path)
    init_db(conn)

    lakers_id = 1610612747
    nuggets_id = 1610612743
    lebron_id = 2544
    jokic_id = 203999

    upsert_team(conn, lakers_id, "LAL", "Los Angeles Lakers")
    upsert_team(conn, nuggets_id, "DEN", "Denver Nuggets")

    upsert_player(conn, lebron_id, "LeBron James", True, "F", lakers_id)
    upsert_player(conn, jokic_id, "Nikola Jokic", True, "C", nuggets_id)

    insert_team_stats(conn, lakers_id, "2022-23", 112.5, 114.8, 2.3, 100.5)
    insert_team_stats(conn, lakers_id, "2023-24", 110.3, 116.1, 5.8, 99.8)
    insert_team_stats(conn, nuggets_id, "2022-23", 110.1, 117.2, 7.1, 97.3)
    insert_team_stats(conn, nuggets_id, "2023-24", 111.8, 118.5, 6.7, 98.1)

    game_logs = [
        # Jokic 2022-23 (3 played)
        {"player_id": jokic_id, "game_id": "0022200901", "season": "2022-23", "game_date": "2023-03-10", "matchup": "DEN vs. LAL", "wl": "W", "min": 35, "pts": 28, "reb": 12, "ast": 10, "stl": 1, "blk": 1, "fg3m": 1, "fgm": 11, "fga": 18, "ftm": 5, "fta": 6, "oreb": 2, "dreb": 10, "tov": 3, "pf": 2, "plus_minus": 9, "is_dnp": 0},
        {"player_id": jokic_id, "game_id": "0022200902", "season": "2022-23", "game_date": "2023-03-13", "matchup": "DEN @ PHX", "wl": "L", "min": 34, "pts": 24, "reb": 11, "ast": 8, "stl": 2, "blk": 0, "fg3m": 1, "fgm": 10, "fga": 19, "ftm": 3, "fta": 4, "oreb": 1, "dreb": 10, "tov": 4, "pf": 3, "plus_minus": -4, "is_dnp": 0},
        {"player_id": jokic_id, "game_id": "0022200903", "season": "2022-23", "game_date": "2023-03-16", "matchup": "DEN vs. LAC", "wl": "W", "min": 36, "pts": 30, "reb": 14, "ast": 9, "stl": 1, "blk": 1, "fg3m": 2, "fgm": 12, "fga": 20, "ftm": 4, "fta": 5, "oreb": 3, "dreb": 11, "tov": 2, "pf": 2, "plus_minus": 11, "is_dnp": 0},
        # Jokic 2023-24 (11 played + 1 DNP)
        {"player_id": jokic_id, "game_id": "0022300001", "season": "2023-24", "game_date": "2023-10-25", "matchup": "DEN vs. LAL", "wl": "W", "min": 35, "pts": 29, "reb": 12, "ast": 11, "stl": 1, "blk": 1, "fg3m": 2, "fgm": 11, "fga": 18, "ftm": 5, "fta": 6, "oreb": 2, "dreb": 10, "tov": 3, "pf": 2, "plus_minus": 15, "is_dnp": 0},
        {"player_id": jokic_id, "game_id": "0022300002", "season": "2023-24", "game_date": "2023-10-27", "matchup": "DEN @ MEM", "wl": "W", "min": 37, "pts": 27, "reb": 10, "ast": 9, "stl": 2, "blk": 0, "fg3m": 1, "fgm": 10, "fga": 19, "ftm": 6, "fta": 7, "oreb": 2, "dreb": 8, "tov": 4, "pf": 2, "plus_minus": 7, "is_dnp": 0},
        {"player_id": jokic_id, "game_id": "0022300003", "season": "2023-24", "game_date": "2023-10-30", "matchup": "DEN vs. OKC", "wl": "L", "min": 33, "pts": 22, "reb": 9, "ast": 8, "stl": 1, "blk": 1, "fg3m": 1, "fgm": 9, "fga": 17, "ftm": 3, "fta": 4, "oreb": 1, "dreb": 8, "tov": 5, "pf": 3, "plus_minus": -6, "is_dnp": 0},
        {"player_id": jokic_id, "game_id": "0022300004", "season": "2023-24", "game_date": "2023-11-02", "matchup": "DEN @ LAL", "wl": "W", "min": 36, "pts": 31, "reb": 13, "ast": 10, "stl": 1, "blk": 2, "fg3m": 2, "fgm": 12, "fga": 21, "ftm": 5, "fta": 6, "oreb": 3, "dreb": 10, "tov": 3, "pf": 2, "plus_minus": 12, "is_dnp": 0},
        {"player_id": jokic_id, "game_id": "0022300005", "season": "2023-24", "game_date": "2023-11-05", "matchup": "DEN vs. DAL", "wl": "W", "min": 34, "pts": 25, "reb": 11, "ast": 12, "stl": 2, "blk": 1, "fg3m": 1, "fgm": 10, "fga": 18, "ftm": 4, "fta": 5, "oreb": 2, "dreb": 9, "tov": 2, "pf": 2, "plus_minus": 10, "is_dnp": 0},
        {"player_id": jokic_id, "game_id": "0022300006", "season": "2023-24", "game_date": "2023-11-08", "matchup": "DEN @ NOP", "wl": "L", "min": 0, "pts": 0, "reb": 0, "ast": 0, "stl": 0, "blk": 0, "fg3m": 0, "fgm": 0, "fga": 0, "ftm": 0, "fta": 0, "oreb": 0, "dreb": 0, "tov": 0, "pf": 0, "plus_minus": 0, "is_dnp": 1},
        {"player_id": jokic_id, "game_id": "0022300007", "season": "2023-24", "game_date": "2023-11-11", "matchup": "DEN vs. HOU", "wl": "W", "min": 35, "pts": 34, "reb": 16, "ast": 13, "stl": 1, "blk": 1, "fg3m": 2, "fgm": 13, "fga": 22, "ftm": 6, "fta": 7, "oreb": 4, "dreb": 12, "tov": 3, "pf": 2, "plus_minus": 14, "is_dnp": 0},
        {"player_id": jokic_id, "game_id": "0022300008", "season": "2023-24", "game_date": "2023-11-14", "matchup": "DEN @ GSW", "wl": "L", "min": 32, "pts": 20, "reb": 8, "ast": 7, "stl": 0, "blk": 1, "fg3m": 1, "fgm": 8, "fga": 16, "ftm": 3, "fta": 4, "oreb": 1, "dreb": 7, "tov": 4, "pf": 3, "plus_minus": -8, "is_dnp": 0},
        {"player_id": jokic_id, "game_id": "0022300009", "season": "2023-24", "game_date": "2023-11-17", "matchup": "DEN vs. MIL", "wl": "W", "min": 37, "pts": 33, "reb": 15, "ast": 11, "stl": 2, "blk": 1, "fg3m": 2, "fgm": 12, "fga": 20, "ftm": 7, "fta": 8, "oreb": 3, "dreb": 12, "tov": 2, "pf": 2, "plus_minus": 13, "is_dnp": 0},
        {"player_id": jokic_id, "game_id": "0022300010", "season": "2023-24", "game_date": "2023-11-20", "matchup": "DEN @ SAC", "wl": "L", "min": 34, "pts": 24, "reb": 10, "ast": 9, "stl": 1, "blk": 0, "fg3m": 1, "fgm": 9, "fga": 18, "ftm": 5, "fta": 6, "oreb": 2, "dreb": 8, "tov": 3, "pf": 3, "plus_minus": -2, "is_dnp": 0},
        {"player_id": jokic_id, "game_id": "0022300011", "season": "2023-24", "game_date": "2023-11-23", "matchup": "DEN vs. PHX", "wl": "W", "min": 36, "pts": 30, "reb": 12, "ast": 10, "stl": 1, "blk": 2, "fg3m": 3, "fgm": 11, "fga": 19, "ftm": 5, "fta": 5, "oreb": 3, "dreb": 9, "tov": 2, "pf": 2, "plus_minus": 11, "is_dnp": 0},
        {"player_id": jokic_id, "game_id": "0022300012", "season": "2023-24", "game_date": "2023-11-26", "matchup": "DEN @ MIN", "wl": "L", "min": 33, "pts": 26, "reb": 11, "ast": 8, "stl": 1, "blk": 1, "fg3m": 1, "fgm": 10, "fga": 17, "ftm": 5, "fta": 6, "oreb": 2, "dreb": 9, "tov": 4, "pf": 3, "plus_minus": -1, "is_dnp": 0},
        # LeBron 2023-24 (11 played + 1 DNP, with one b2b)
        {"player_id": lebron_id, "game_id": "0022301001", "season": "2023-24", "game_date": "2023-10-24", "matchup": "LAL @ DEN", "wl": "L", "min": 36, "pts": 27, "reb": 8, "ast": 9, "stl": 1, "blk": 1, "fg3m": 2, "fgm": 10, "fga": 20, "ftm": 5, "fta": 7, "oreb": 1, "dreb": 7, "tov": 3, "pf": 2, "plus_minus": -7, "is_dnp": 0},
        {"player_id": lebron_id, "game_id": "0022301002", "season": "2023-24", "game_date": "2023-10-26", "matchup": "LAL vs. PHX", "wl": "W", "min": 35, "pts": 31, "reb": 9, "ast": 8, "stl": 2, "blk": 0, "fg3m": 3, "fgm": 11, "fga": 21, "ftm": 6, "fta": 8, "oreb": 1, "dreb": 8, "tov": 4, "pf": 2, "plus_minus": 6, "is_dnp": 0},
        {"player_id": lebron_id, "game_id": "0022301003", "season": "2023-24", "game_date": "2023-10-29", "matchup": "LAL @ SAC", "wl": "L", "min": 34, "pts": 25, "reb": 7, "ast": 6, "stl": 1, "blk": 1, "fg3m": 2, "fgm": 9, "fga": 19, "ftm": 5, "fta": 6, "oreb": 1, "dreb": 6, "tov": 3, "pf": 3, "plus_minus": -5, "is_dnp": 0},
        {"player_id": lebron_id, "game_id": "0022301004", "season": "2023-24", "game_date": "2023-11-01", "matchup": "LAL vs. LAC", "wl": "W", "min": 37, "pts": 33, "reb": 10, "ast": 7, "stl": 2, "blk": 1, "fg3m": 2, "fgm": 12, "fga": 22, "ftm": 7, "fta": 9, "oreb": 2, "dreb": 8, "tov": 4, "pf": 2, "plus_minus": 8, "is_dnp": 0},
        {"player_id": lebron_id, "game_id": "0022301005", "season": "2023-24", "game_date": "2023-11-03", "matchup": "LAL @ ORL", "wl": "L", "min": 32, "pts": 26, "reb": 6, "ast": 9, "stl": 1, "blk": 0, "fg3m": 1, "fgm": 10, "fga": 18, "ftm": 5, "fta": 7, "oreb": 1, "dreb": 5, "tov": 2, "pf": 2, "plus_minus": -3, "is_dnp": 0},
        {"player_id": lebron_id, "game_id": "0022301006", "season": "2023-24", "game_date": "2023-11-06", "matchup": "LAL vs. MIA", "wl": "W", "min": 35, "pts": 30, "reb": 8, "ast": 10, "stl": 2, "blk": 1, "fg3m": 3, "fgm": 11, "fga": 20, "ftm": 5, "fta": 6, "oreb": 1, "dreb": 7, "tov": 3, "pf": 2, "plus_minus": 9, "is_dnp": 0},
        {"player_id": lebron_id, "game_id": "0022301007", "season": "2023-24", "game_date": "2023-11-09", "matchup": "LAL @ DEN", "wl": "L", "min": 0, "pts": 0, "reb": 0, "ast": 0, "stl": 0, "blk": 0, "fg3m": 0, "fgm": 0, "fga": 0, "ftm": 0, "fta": 0, "oreb": 0, "dreb": 0, "tov": 0, "pf": 0, "plus_minus": 0, "is_dnp": 1},
        {"player_id": lebron_id, "game_id": "0022301008", "season": "2023-24", "game_date": "2023-11-12", "matchup": "LAL vs. POR", "wl": "W", "min": 36, "pts": 32, "reb": 9, "ast": 8, "stl": 1, "blk": 1, "fg3m": 2, "fgm": 12, "fga": 21, "ftm": 6, "fta": 8, "oreb": 2, "dreb": 7, "tov": 3, "pf": 2, "plus_minus": 12, "is_dnp": 0},
        {"player_id": lebron_id, "game_id": "0022301009", "season": "2023-24", "game_date": "2023-11-15", "matchup": "LAL @ PHX", "wl": "L", "min": 34, "pts": 28, "reb": 7, "ast": 7, "stl": 1, "blk": 0, "fg3m": 2, "fgm": 10, "fga": 19, "ftm": 6, "fta": 7, "oreb": 1, "dreb": 6, "tov": 4, "pf": 3, "plus_minus": -4, "is_dnp": 0},
        {"player_id": lebron_id, "game_id": "0022301010", "season": "2023-24", "game_date": "2023-11-17", "matchup": "LAL @ DEN", "wl": "L", "min": 35, "pts": 29, "reb": 8, "ast": 6, "stl": 2, "blk": 1, "fg3m": 3, "fgm": 10, "fga": 20, "ftm": 6, "fta": 8, "oreb": 1, "dreb": 7, "tov": 3, "pf": 2, "plus_minus": -2, "is_dnp": 0},
        {"player_id": lebron_id, "game_id": "0022301011", "season": "2023-24", "game_date": "2023-11-18", "matchup": "LAL vs. UTA", "wl": "W", "min": 34, "pts": 26, "reb": 6, "ast": 9, "stl": 1, "blk": 0, "fg3m": 2, "fgm": 9, "fga": 18, "ftm": 6, "fta": 7, "oreb": 1, "dreb": 5, "tov": 2, "pf": 2, "plus_minus": 7, "is_dnp": 0},
        {"player_id": lebron_id, "game_id": "0022301012", "season": "2023-24", "game_date": "2023-11-21", "matchup": "LAL vs. DAL", "wl": "W", "min": 37, "pts": 33, "reb": 10, "ast": 10, "stl": 2, "blk": 1, "fg3m": 3, "fgm": 12, "fga": 22, "ftm": 6, "fta": 8, "oreb": 2, "dreb": 8, "tov": 4, "pf": 2, "plus_minus": 10, "is_dnp": 0},
    ]
    insert_game_logs(conn, pd.DataFrame(game_logs))

    try:
        yield conn
    finally:
        conn.close()
        shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture
def training_parquet(tmp_path):
    """Create a synthetic long-format training Parquet for model pipeline tests.

    Mimics the Phase 2 output: long-format with stat_type, line_value, hit,
    plus feature columns named like rolling/contextual features.
    """
    rng = np.random.RandomState(42)

    # 3 seasons, 10 games per player-season, 2 players, 2 target stats
    seasons = ["2021-22", "2022-23", "2023-24"]
    players = [203999, 2544]  # Jokic, LeBron
    stats = ["pts", "reb"]
    n_games = 10

    rows = []
    for season in seasons:
        for pid in players:
            for g in range(n_games):
                game_date = f"{season[:4]}-{11 + g // 30:02d}-{(g % 28) + 1:02d}"
                for stat in stats:
                    for offset in [-0.5, 0.0, 0.5]:
                        line = round(rng.uniform(10, 30) * 2) / 2 + offset
                        line = max(0.5, line)
                        hit = int(rng.random() > 0.45)
                        row = {
                            "player_id": pid,
                            "game_id": f"002{season[:4]}00{g:03d}",
                            "season": season,
                            "game_date": game_date,
                            "stat_type": STAT_TYPE_MAP[stat],
                            "line_value": line,
                            "hit": hit,
                            # Feature columns (rolling, contextual, matchup)
                            f"{stat}_avg_L5": rng.uniform(5, 30),
                            f"{stat}_avg_L10": rng.uniform(5, 30),
                            f"{stat}_std_L5": rng.uniform(1, 8),
                            f"{stat}_season_avg": rng.uniform(10, 25),
                            "games_played_season": g + 1,
                            "rest_days": rng.choice([0, 1, 2, 3]),
                            "is_back_to_back": int(rng.random() > 0.8),
                            "is_home": int(rng.random() > 0.5),
                            "opp_def_rating": rng.uniform(105, 115),
                            "opp_pace": rng.uniform(95, 105),
                            f"opp_{stat}_avg_allowed": rng.uniform(5, 25),
                            f"{stat}_vs_opp_avg": rng.uniform(5, 25),
                            "min_avg_L5": rng.uniform(15, 40),
                            "min_avg_L10": rng.uniform(15, 40),
                        }
                        rows.append(row)

    df = pd.DataFrame(rows)
    parquet_path = str(tmp_path / "test_features.parquet")
    df.to_parquet(parquet_path, engine="pyarrow", compression="snappy", index=False)
    return parquet_path
