import os
import shutil
import tempfile

import pandas as pd
import pytest

from server.pipeline.db.connection import get_connection
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
