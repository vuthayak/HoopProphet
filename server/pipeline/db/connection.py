import os
import sqlite3

from server.pipeline import DB_PATH


def get_connection(db_path: str = None) -> sqlite3.Connection:
    """Return a SQLite connection with WAL mode and foreign keys enabled."""
    if db_path is None:
        db_path = DB_PATH

    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn
