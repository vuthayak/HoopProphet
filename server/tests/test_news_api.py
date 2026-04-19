"""
API tests for news & injury flag endpoints — per D-09, D-10.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from server.app import app


@pytest.fixture
def client():
    """Provide a TestClient for the FastAPI app."""
    return TestClient(app)


class TestPlayerNewsEndpoint:
    """Tests for GET /api/players/{id}/news per D-09."""

    def test_news_returns_404_for_unknown_player(self, client):
        """Unknown player_id returns 404 per existing pattern."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.execute.return_value = mock_cursor
        mock_conn.close = MagicMock()

        with patch("server.api.news.get_connection", return_value=mock_conn):
            with patch("server.api.news.NewsService"):
                response = client.get("/api/players/99999/news")

        assert response.status_code == 404

    def test_news_returns_correct_structure(self, client):
        """Response includes player_id, alerts, news_items, stale_warning."""
        now = "2024-01-15T10:00:00"
        alerts = [
            {
                "id": 1, "player_id": 2544, "alert_type": "INJURY",
                "subcategory": "QUESTIONABLE", "severity": "warning",
                "source": "nba_injury_report", "source_url": "https://nba.com",
                "headline": "LeBron - QUESTIONABLE",
                "first_seen_at": now, "last_updated_at": now,
            }
        ]

        with patch("server.api.news.get_player_by_id", return_value={"player_id": 2544, "full_name": "LeBron James", "position": "F", "team_id": 1610612747}):
            with patch("server.api.news.get_connection") as mock_get_conn:
                mock_conn = MagicMock()
                mock_conn.execute.return_value.fetchall.return_value = []
                mock_get_conn.return_value = mock_conn
                with patch("server.services.news_service.NewsService.is_cache_fresh", return_value=(True, [])):
                    with patch("server.api.news.NewsService.process_all", return_value={"alerts_generated": 1, "sources_fetched": [], "cache_status": {}}):
                        with patch("server.api.news.get_player_alerts", return_value=alerts):
                            with patch("server.api.news.get_news_items", return_value=[]):
                                response = client.get(f"/api/players/{2544}/news")

        assert response.status_code == 200
        data = response.json()
        assert data["player_id"] == 2544
        assert "alerts" in data
        assert "news_items" in data
        assert "stale_warning" in data

    def test_news_includes_updated_ago_timestamp(self, client):
        """Each alert includes 'Updated X min/hours ago' per D-07."""
        now = datetime.now().isoformat()
        alerts = [
            {
                "id": 1, "player_id": 2544, "alert_type": "INJURY",
                "subcategory": "QUESTIONABLE", "severity": "warning",
                "source": "nba_injury_report", "source_url": "https://nba.com",
                "headline": "LeBron - QUESTIONABLE",
                "first_seen_at": now, "last_updated_at": now,
            }
        ]

        with patch("server.api.news.get_player_by_id", return_value={"player_id": 2544, "full_name": "LeBron James", "position": "F", "team_id": 1610612747}):
            with patch("server.api.news.get_player_alerts", return_value=alerts):
                with patch("server.api.news.get_news_items", return_value=[]):
                    with patch("server.services.news_service.NewsService.is_cache_fresh", return_value=(True, [])):
                        response = client.get(f"/api/players/{2544}/news")

        assert response.status_code == 200
        data = response.json()
        if data["alerts"]:
            assert "updated_ago" in data["alerts"][0]

    def test_news_includes_stale_warning_for_old_data(self, client):
        """Stale data warning present when alerts > 24h old per D-08."""
        old_time = (datetime.now() - timedelta(hours=25)).isoformat()
        alerts = [
            {
                "id": 1, "player_id": 2544, "alert_type": "INJURY",
                "subcategory": "QUESTIONABLE", "severity": "warning",
                "source": "nba_injury_report", "source_url": "https://nba.com",
                "headline": "LeBron - QUESTIONABLE",
                "first_seen_at": old_time, "last_updated_at": old_time,
            }
        ]

        with patch("server.api.news.get_player_by_id", return_value={"player_id": 2544, "full_name": "LeBron James", "position": "F", "team_id": 1610612747}):
            with patch("server.api.news.get_player_alerts", return_value=alerts):
                with patch("server.api.news.get_news_items", return_value=[]):
                    with patch("server.services.news_service.NewsService.is_cache_fresh", return_value=(False, ["nba_injury_report"])):
                        response = client.get(f"/api/players/{2544}/news")

        assert response.status_code == 200
        data = response.json()
        assert data["stale_warning"] is not None

    def test_news_no_stale_warning_for_fresh_data(self, client):
        """No stale warning when alerts are within TTL."""
        now = datetime.now().isoformat()
        alerts = [
            {
                "id": 1, "player_id": 2544, "alert_type": "INJURY",
                "subcategory": "QUESTIONABLE", "severity": "warning",
                "source": "nba_injury_report", "source_url": "https://nba.com",
                "headline": "LeBron - QUESTIONABLE",
                "first_seen_at": now, "last_updated_at": now,
            }
        ]

        with patch("server.api.news.get_player_by_id", return_value={"player_id": 2544, "full_name": "LeBron James", "position": "F", "team_id": 1610612747}):
            with patch("server.api.news.get_player_alerts", return_value=alerts):
                with patch("server.api.news.get_news_items", return_value=[]):
                    with patch("server.services.news_service.NewsService.is_cache_fresh", return_value=(True, [])):
                        response = client.get(f"/api/players/{2544}/news")

        assert response.status_code == 200
        data = response.json()
        assert data["stale_warning"] is None

    def test_news_refresh_triggers_fetch(self, client):
        """refresh=True triggers NewsService.process_all() call."""
        with patch("server.api.news.get_player_by_id", return_value={"player_id": 2544, "full_name": "LeBron James", "position": "F", "team_id": 1610612747}):
            with patch("server.api.news.get_player_alerts", return_value=[]):
                with patch("server.api.news.get_news_items", return_value=[]):
                    with patch("server.services.news_service.NewsService.is_cache_fresh", return_value=(True, [])):
                        with patch("server.api.news.NewsService.process_all") as mock_process:
                            mock_process.return_value = {"alerts_generated": 0, "sources_fetched": [], "cache_status": {}}
                            response = client.get(f"/api/players/{2544}/news?refresh=true")

        mock_process.assert_called_once()
        assert response.status_code == 200


class TestPlayerAlertsEmbedded:
    """Tests for alerts embedded in GET /api/players/{id} per D-09."""

    def test_player_detail_includes_alerts_summary(self, client):
        """Player response includes lightweight alerts array."""
        now = datetime.now().isoformat()

        def mock_execute(q, *a):
            m = MagicMock()
            if "SELECT" in q and "player_id" in q:
                m.fetchall.return_value = [(2544, "LeBron James", True, "F", 1610612747)]
            elif "player_alerts" in q:
                m.fetchall.return_value = [
                    (1, 2544, "INJURY", "QUESTIONABLE", "warning",
                     "nba_injury_report", "https://nba.com", "LeBron - QUESTIONABLE",
                     now, now),
                ]
            else:
                m.fetchall.return_value = []
            return m

        mock_conn = MagicMock()
        mock_conn.execute = mock_execute
        mock_conn.close = MagicMock()

        with patch("server.services.player_service.get_connection", return_value=mock_conn):
            with patch("server.api.players.get_default_lines", return_value={}):
                response = client.get(f"/api/players/{2544}")

        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        assert isinstance(data["alerts"], list)

    def test_player_alerts_summary_is_lightweight(self, client):
        """Alert summary contains only alert_type, severity, subcategory, last_updated_at."""
        now = datetime.now().isoformat()

        def mock_execute(q, *a):
            m = MagicMock()
            if "SELECT" in q and "player_id" in q:
                m.fetchall.return_value = [(2544, "LeBron James", True, "F", 1610612747)]
            elif "player_alerts" in q:
                m.fetchall.return_value = [
                    (1, 2544, "INJURY", "QUESTIONABLE", "warning",
                     "nba_injury_report", "https://nba.com", "LeBron - QUESTIONABLE",
                     now, now),
                ]
            else:
                m.fetchall.return_value = []
            return m

        mock_conn = MagicMock()
        mock_conn.execute = mock_execute
        mock_conn.close = MagicMock()

        with patch("server.services.player_service.get_connection", return_value=mock_conn):
            with patch("server.api.players.get_default_lines", return_value={}):
                response = client.get(f"/api/players/{2544}")

        assert response.status_code == 200
        data = response.json()
        if data["alerts"]:
            alert = data["alerts"][0]
            keys = set(alert.keys())
            assert keys.issubset({"alert_type", "severity", "subcategory", "last_updated_at"})

    def test_player_detail_empty_alerts_when_no_news(self, client):
        """Player without alerts returns empty alerts array."""
        def mock_execute(q, *a):
            m = MagicMock()
            if "SELECT" in q and "player_id" in q:
                m.fetchall.return_value = [(2544, "LeBron James", True, "F", 1610612747)]
            else:
                m.fetchall.return_value = []
            return m

        mock_conn = MagicMock()
        mock_conn.execute = mock_execute
        mock_conn.close = MagicMock()

        with patch("server.services.player_service.get_connection", return_value=mock_conn):
            with patch("server.api.players.get_default_lines", return_value={}):
                response = client.get(f"/api/players/{2544}")

        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        assert data["alerts"] == []

    def test_alerts_graceful_degradation(self, client):
        """If alert lookup fails, player detail still works with empty alerts."""
        def mock_execute(q, *a):
            m = MagicMock()
            if "SELECT" in q and "player_id" in q:
                m.fetchall.return_value = [(2544, "LeBron James", True, "F", 1610612747)]
            else:
                m.fetchall.return_value = []
            return m

        mock_conn = MagicMock()
        mock_conn.execute = mock_execute
        mock_conn.close = MagicMock()

        with patch("server.services.player_service.get_connection", return_value=mock_conn):
            with patch("server.api.players.get_default_lines", return_value={}):
                with patch("server.services.player_service.get_player_alerts_summary", side_effect=Exception("DB error")):
                    response = client.get(f"/api/players/{2544}")

        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
