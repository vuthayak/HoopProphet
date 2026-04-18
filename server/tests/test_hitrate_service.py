"""
Tests for hitrate_service — RED phase.

Hit rate = percentage of games where stat > default line for that stat.
Each window returns {rate: float, count: int}.
Windows with <5 games return None per D-11.
"""

import os
import shutil
import sqlite3
import tempfile

import pandas as pd
import pytest

from server.pipeline.db.queries import insert_game_logs, upsert_player, upsert_team
from server.pipeline.db.schema import init_db
from server.services import player_service
from server.services.hitrate_service import get_hit_rates


@pytest.fixture
def hitrate_db():
    """Provide a temp SQLite DB with Jokic game logs (20+ non-DNP games)."""
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "test.db")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    init_db(conn)

    lakers_id = 1610612747
    nuggets_id = 1610612743
    lebron_id = 2544
    jokic_id = 203999

    upsert_team(conn, lakers_id, "LAL", "Los Angeles Lakers")
    upsert_team(conn, nuggets_id, "DEN", "Denver Nuggets")
    upsert_player(conn, lebron_id, "LeBron James", True, "F", lakers_id)
    upsert_player(conn, jokic_id, "Nikola Jokic", True, "C", nuggets_id)

    # Jokic 2023-24: 20+ non-DNP games for full L20 testing
    # Game dates in reverse chronological order
    jokic_games = []
    base_date = 25
    base_month = 10
    base_year = 2023

    for i in range(25):
        day = (base_date + i) % 28 + 1
        month = base_month if i < 5 else 11 if i < 15 else 12
        year = base_year

        game_date = f"2023-{month:02d}-{day:02d}"
        pts = 30 - (i % 10) + 5  # Varied pts around 25
        is_dnp = 1 if i == 12 else 0  # One DNP game at index 12

        jokic_games.append({
            "player_id": jokic_id,
            "game_id": f"002230{i+1:03d}",
            "season": "2023-24",
            "game_date": game_date,
            "matchup": "DEN vs. LAL" if i % 2 == 0 else "DEN @ MEM",
            "wl": "W" if i % 3 != 2 else "L",
            "min": 0 if is_dnp else 35 - (i % 5),
            "pts": 0 if is_dnp else pts,
            "reb": 0 if is_dnp else 12 - (i % 6),
            "ast": 0 if is_dnp else 10 - (i % 8),
            "stl": 0 if is_dnp else 1 + (i % 3),
            "blk": 0 if is_dnp else 1 + (i % 2),
            "fg3m": 0 if is_dnp else 1 + (i % 4),
            "fgm": 0 if is_dnp else 10 + (i % 8),
            "fga": 0 if is_dnp else 18 + (i % 6),
            "ftm": 0 if is_dnp else 4 + (i % 3),
            "fta": 0 if is_dnp else 5 + (i % 4),
            "oreb": 0 if is_dnp else 2 + (i % 3),
            "dreb": 0 if is_dnp else 8 + (i % 5),
            "tov": 0 if is_dnp else 2 + (i % 3),
            "pf": 0 if is_dnp else 2 + (i % 2),
            "plus_minus": 0 if is_dnp else 5 - (i % 12),
            "is_dnp": is_dnp,
        })

    insert_game_logs(conn, pd.DataFrame(jokic_games))
    conn.commit()
    conn.close()

    yield db_path
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture
def hitrate_svc(hitrate_db, monkeypatch):
    """Patch player_service DB_PATH and return the service module."""
    monkeypatch.setattr(player_service, "DB_PATH", hitrate_db)
    return player_service


class TestGetHitRates:
    """Test get_hit_rates(player_id, stat, line_value, seasons)."""

    def test_hit_rates_returns_all_windows(self, hitrate_svc):
        """L5, L10, L20, season windows all returned with rate and count."""
        # Jokic (203999) has 24 non-DNP games in hitrate_db
        # Line value of 25.0 for pts
        result = get_hit_rates(player_id=203999, stat="pts", line_value=25.0)

        assert "L5" in result
        assert "L10" in result
        assert "L20" in result
        assert "season" in result

        # Each window has rate and count (L5, L10, L20, season all have 20+ games)
        for window in ["L5", "L10", "L20", "season"]:
            assert result[window] is not None, f"{window} should not be None"
            assert "rate" in result[window]
            assert "count" in result[window]
            assert isinstance(result[window]["rate"], float)
            assert isinstance(result[window]["count"], int)

    def test_hit_rates_unknown_player_raises(self, hitrate_svc):
        """Unknown player_id raises ValueError per D-12."""
        with pytest.raises(ValueError, match="Player not found"):
            get_hit_rates(player_id=99999, stat="pts", line_value=20.0)

    def test_hit_rates_requires_line_value(self):
        """get_hit_rates must accept line_value parameter."""
        import inspect
        sig = inspect.signature(get_hit_rates)
        assert "line_value" in sig.parameters
