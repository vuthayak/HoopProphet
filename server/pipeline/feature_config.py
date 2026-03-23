import os

from server.pipeline import DATA_DIR

STAT_COLS = [
    "pts",
    "reb",
    "ast",
    "stl",
    "blk",
    "fg3m",
    "fgm",
    "fga",
    "ftm",
    "fta",
    "oreb",
    "dreb",
    "tov",
    "pf",
    "plus_minus",
    "min",
]

PRIMARY_STATS = ["pts", "reb", "ast", "stl", "blk", "fg3m", "plus_minus", "min"]
SECONDARY_STATS = [s for s in STAT_COLS if s not in PRIMARY_STATS]

COMBO_STATS = {
    "pra": ["pts", "reb", "ast"],
    "pa": ["pts", "ast"],
    "pr": ["pts", "reb"],
}

ALL_TARGET_STATS = ["pts", "reb", "ast", "stl", "blk", "fg3m", "pra", "pa", "pr", "min"]
STAT_TYPE_MAP = {stat: idx for idx, stat in enumerate(ALL_TARGET_STATS)}

WINDOWS_PRIMARY = [5, 10, 20]
WINDOWS_SECONDARY = [5, 10]

MIN_GAMES_PER_SEASON = 10
N_THRESHOLD_LINES = 3

PARQUET_PATH = os.path.join(DATA_DIR, "features.parquet")
