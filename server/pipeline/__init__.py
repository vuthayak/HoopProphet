import os

SEASONS = ["2020-21", "2021-22", "2022-23", "2023-24", "2024-25"]

SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(SERVER_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "hoopprophet.db")
CACHE_PATH = os.path.join(DATA_DIR, "nba_cache")
