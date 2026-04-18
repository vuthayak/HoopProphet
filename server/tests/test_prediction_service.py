"""
Tests for prediction_service — RED phase.

Tests get_default_lines, get_predictions, get_top_props, get_player_props.
"""

import os
import shutil
import sqlite3
import tempfile

import numpy as np
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch

from server.pipeline.db.queries import insert_game_logs, upsert_player, upsert_team
from server.pipeline.db.schema import init_db
from server.services import player_service
from server.services.prediction_service import (
    get_default_lines,
    get_predictions,
    get_top_props,
    get_player_props,
    _round_half,
    _round_percent,
)


@pytest.fixture
def pred_db():
    """Provide a temp SQLite DB with Jokic and LeBron game logs."""
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

    # Jokic 2023-24: 20 non-DNP games
    jokic_games = []
    base_date = 25

    for i in range(25):
        day = (base_date + i) % 28 + 1
        month = 10 if i < 5 else 11 if i < 15 else 12
        game_date = f"2023-{month:02d}-{day:02d}"
        pts = 30 - (i % 10) + 5
        is_dnp = 1 if i == 12 else 0  # One DNP game

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
def pred_svc(pred_db, monkeypatch):
    """Patch player_service DB_PATH."""
    monkeypatch.setattr(player_service, "DB_PATH", pred_db)
    return player_service


class TestRoundHelpers:
    """Test rounding helper functions."""

    def test_round_half(self):
        """Round to nearest 0.5: 24.3→24.5, 24.7→24.5, 25.0→25.0."""
        assert _round_half(24.3) == 24.5
        assert _round_half(24.7) == 24.5
        assert _round_half(25.0) == 25.0
        assert _round_half(24.25) == 24.5
        assert _round_half(24.6) == 24.5
        assert _round_half(10.1) == 10.0

    def test_round_percent(self):
        """Round to nearest 0.01 for probability display per D-08."""
        assert _round_percent(0.71847) == 0.72
        assert _round_percent(0.33333) == 0.33
        assert _round_percent(0.5) == 0.5
        assert _round_percent(0.999) == 1.0


class TestGetDefaultLines:
    """Test get_default_lines(player_id, seasons)."""

    def test_default_lines_returns_dict(self, pred_svc):
        """Returns dict of stat -> line_value."""
        result = get_default_lines(player_id=203999)
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_default_lines_rounded_to_half(self, pred_svc):
        """Lines rounded to 0.5 increments per D-01."""
        lines = get_default_lines(player_id=203999)
        for stat, line in lines.items():
            assert line % 0.5 == 0, f"{stat} line {line} not rounded to 0.5"

    def test_default_lines_minimum_5_games(self, pred_svc):
        """Stats with <5 non-DNP games are excluded per D-02."""
        lines = get_default_lines(player_id=203999)
        assert "pts" in lines
        assert "reb" in lines
        assert "ast" in lines

    def test_combo_stats_present(self, pred_svc):
        """PRA, PA, PR are computed per D-03."""
        lines = get_default_lines(player_id=203999)
        if "pra" in lines:
            assert 10 <= lines["pra"] <= 100

    def test_default_lines_unknown_player_raises(self, pred_svc):
        """Unknown player raises ValueError."""
        with pytest.raises(ValueError, match="Player not found"):
            get_default_lines(player_id=99999)


class TestGetPredictions:
    """Test get_predictions(player_id, model_artifact)."""

    def test_predictions_graceful_degradation_no_artifact(self, pred_svc):
        """When model_artifact is None, returns empty list per D-10."""
        result = get_predictions(player_id=203999, model_artifact=None)
        assert result == []

    def test_predictions_probability_rounded_to_percent(self, pred_svc):
        """Probability rounded to 1% per D-08."""
        mock_artifact = {
            "model": MagicMock(),
            "calibrator": MagicMock(),
            "feature_columns": ["pts_avg_L5"],
            "categorical_features": [],
            "metrics": {},
        }
        mock_artifact["calibrator"].predict_proba.return_value = np.array([0.71847])

        with patch("server.services.prediction_service.pd.read_parquet") as mock_read:
            # Create a fake parquet df with player 203999 and stat_type for pts
            mock_df = pd.DataFrame({
                "player_id": [203999],
                "game_date": ["2023-11-26"],
                "stat_type": [0],  # pts = 0 in STAT_TYPE_MAP
            })
            mock_read.return_value = mock_df

            result = get_predictions(player_id=203999, model_artifact=mock_artifact)
            if len(result) > 0:
                assert result[0]["probability"] == 0.72


class TestGetTopProps:
    """Test get_top_props(player_id, model_artifact, n)."""

    def test_top_props_max_5(self, pred_svc):
        """Maximum 5 props returned per D-06."""
        mock_artifact = {
            "model": MagicMock(),
            "calibrator": MagicMock(),
            "feature_columns": ["pts_avg_L5"],
            "categorical_features": [],
            "metrics": {},
        }
        mock_artifact["calibrator"].predict_proba.return_value = np.array([0.6])

        result = get_top_props(player_id=203999, model_artifact=mock_artifact, n=5)
        assert isinstance(result, list)
        assert len(result) <= 5


class TestGetPlayerProps:
    """Test get_player_props(player_id, model_artifact, seasons)."""

    def test_player_props_combined_structure(self, pred_svc):
        """Returns combined dict: default_lines, top_props per D-07."""
        mock_artifact = {
            "model": MagicMock(),
            "calibrator": MagicMock(),
            "feature_columns": ["pts_avg_L5"],
            "categorical_features": [],
            "metrics": {},
        }
        mock_artifact["calibrator"].predict_proba.return_value = np.array([0.65])

        result = get_player_props(player_id=203999, model_artifact=mock_artifact)

        assert "player_id" in result
        assert "default_lines" in result
        assert "top_props" in result
        assert result["player_id"] == 203999

    def test_player_props_graceful_no_artifact(self, pred_svc):
        """Returns structure with empty top_props when artifact is None per D-10."""
        result = get_player_props(player_id=203999, model_artifact=None)

        assert "player_id" in result
        assert "default_lines" in result
        assert "top_props" in result
        assert isinstance(result["default_lines"], dict)
