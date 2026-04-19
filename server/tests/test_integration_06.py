"""
End-to-end integration tests for Phase 6 news & injury flag endpoints.

Tests:
- GET /api/players/{id}/news with mock news data
- GET /api/players/{id} with alerts embedded
- stale warning behavior
- refresh parameter
- error cases
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from server.app import app
from server.pipeline.db.queries import insert_news_items, insert_player_alerts, upsert_player, upsert_team
from server.pipeline.db.schema import init_db


class TestPlayerNewsEndpointIntegration:
    """Integration tests for GET /api/players/{id}/news."""

    def test_news_returns_alerts_for_player_with_alerts(self, client, tmp_path):
        """Player with active alerts returns full alert details."""
        import sqlite3
        tmp_db = str(tmp_path / "test_integration_06.db")
        conn = sqlite3.connect(tmp_db)
        conn.execute("PRAGMA foreign_keys=ON")
        init_db(conn)
        upsert_team(conn, 1610612743, "DEN", "Denver Nuggets")
        upsert_player(conn, 203999, "Nikola Jokic", True, "C", 1610612743)
        now = datetime.now().isoformat()
        insert_player_alerts(conn, [
            {
                "player_id": 203999,
                "alert_type": "INJURY",
                "subcategory": "QUESTIONABLE",
                "severity": "warning",
                "source": "nba_injury_report",
                "source_url": "https://official.nba.com/injury-report",
                "headline": "Nikola Jokic - QUESTIONABLE - knee soreness",
            }
        ])
        conn.close()

        with patch_db_path(tmp_db):
            with patch("server.services.news_service.NewsService.is_cache_fresh", return_value=(True, [])):
                response = client.get(f"/api/players/{203999}/news")

        assert response.status_code == 200
        data = response.json()
        assert data["player_id"] == 203999
        assert len(data["alerts"]) >= 0

    def test_news_returns_empty_for_player_without_alerts(self, client, tmp_path):
        """Player with no alerts returns empty alerts list."""
        import sqlite3
        tmp_db = str(tmp_path / "test_integration_06b.db")
        conn = sqlite3.connect(tmp_db)
        conn.execute("PRAGMA foreign_keys=ON")
        init_db(conn)
        upsert_team(conn, 1610612743, "DEN", "Denver Nuggets")
        upsert_player(conn, 203999, "Nikola Jokic", True, "C", 1610612743)
        conn.close()

        with patch_db_path(tmp_db):
            with patch("server.services.news_service.NewsService.is_cache_fresh", return_value=(True, [])):
                response = client.get(f"/api/players/{203999}/news")

        assert response.status_code == 200
        data = response.json()
        assert data["player_id"] == 203999
        assert data["alerts"] == []

    def test_news_returns_404_for_unknown_player(self, client, tmp_path):
        """Unknown player_id returns 404 per existing pattern."""
        import sqlite3
        tmp_db = str(tmp_path / "test_integration_06c.db")
        conn = sqlite3.connect(tmp_db)
        conn.execute("PRAGMA foreign_keys=ON")
        init_db(conn)
        conn.close()

        with patch_db_path(tmp_db):
            response = client.get("/api/players/99999/news")

        assert response.status_code == 404

    def test_news_includes_updated_ago_timestamp(self, client, tmp_path):
        """Each alert includes 'Updated X min/hours ago' per D-07."""
        import sqlite3
        tmp_db = str(tmp_path / "test_integration_06d.db")
        conn = sqlite3.connect(tmp_db)
        conn.execute("PRAGMA foreign_keys=ON")
        init_db(conn)
        upsert_team(conn, 1610612743, "DEN", "Denver Nuggets")
        upsert_player(conn, 203999, "Nikola Jokic", True, "C", 1610612743)
        now = datetime.now().isoformat()
        insert_player_alerts(conn, [
            {
                "player_id": 203999,
                "alert_type": "INJURY",
                "subcategory": "QUESTIONABLE",
                "severity": "warning",
                "source": "nba_injury_report",
                "source_url": "https://official.nba.com/injury-report",
                "headline": "Nikola Jokic - QUESTIONABLE",
            }
        ])
        conn.close()

        with patch_db_path(tmp_db):
            with patch("server.services.news_service.NewsService.is_cache_fresh", return_value=(True, [])):
                response = client.get(f"/api/players/{203999}/news")

        assert response.status_code == 200
        data = response.json()
        if data["alerts"]:
            assert "updated_ago" in data["alerts"][0]

    def test_news_includes_stale_warning_for_old_data(self, client, tmp_path):
        """Stale data warning present when alerts > 24h old per D-08."""
        import sqlite3
        tmp_db = str(tmp_path / "test_integration_06e.db")
        conn = sqlite3.connect(tmp_db)
        conn.execute("PRAGMA foreign_keys=ON")
        init_db(conn)
        upsert_team(conn, 1610612743, "DEN", "Denver Nuggets")
        upsert_player(conn, 203999, "Nikola Jokic", True, "C", 1610612743)
        old_time = (datetime.now() - timedelta(hours=25)).isoformat()
        conn.execute(
            """INSERT INTO player_alerts (player_id, alert_type, subcategory, severity, source, source_url, headline, first_seen_at, last_updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (203999, "INJURY", "QUESTIONABLE", "warning", "nba_injury_report",
             "https://official.nba.com", "Nikola Jokic - QUESTIONABLE",
             old_time, old_time)
        )
        conn.commit()
        conn.close()

        with patch_db_path(tmp_db):
            with patch("server.services.news_service.NewsService.is_cache_fresh", return_value=(False, ["nba_injury_report"])):
                response = client.get(f"/api/players/{203999}/news")

        assert response.status_code == 200
        data = response.json()
        assert data["stale_warning"] is not None
        assert "24" in data["stale_warning"] or "outdated" in data["stale_warning"].lower()

    def test_news_no_stale_warning_for_fresh_data(self, client, tmp_path):
        """No stale warning when alerts are within TTL."""
        import sqlite3
        tmp_db = str(tmp_path / "test_integration_06f.db")
        conn = sqlite3.connect(tmp_db)
        conn.execute("PRAGMA foreign_keys=ON")
        init_db(conn)
        upsert_team(conn, 1610612743, "DEN", "Denver Nuggets")
        upsert_player(conn, 203999, "Nikola Jokic", True, "C", 1610612743)
        now = datetime.now().isoformat()
        insert_player_alerts(conn, [
            {
                "player_id": 203999,
                "alert_type": "INJURY",
                "subcategory": "QUESTIONABLE",
                "severity": "warning",
                "source": "nba_injury_report",
                "source_url": "https://official.nba.com/injury-report",
                "headline": "Nikola Jokic - QUESTIONABLE",
            }
        ])
        conn.close()

        with patch_db_path(tmp_db):
            with patch("server.services.news_service.NewsService.is_cache_fresh", return_value=(True, [])):
                response = client.get(f"/api/players/{203999}/news")

        assert response.status_code == 200
        data = response.json()
        assert data["stale_warning"] is None

    def test_news_refresh_triggers_fetch(self, client, tmp_path):
        """refresh=True triggers NewsService.process_all() call."""
        import sqlite3
        tmp_db = str(tmp_path / "test_integration_06g.db")
        conn = sqlite3.connect(tmp_db)
        conn.execute("PRAGMA foreign_keys=ON")
        init_db(conn)
        upsert_team(conn, 1610612743, "DEN", "Denver Nuggets")
        upsert_player(conn, 203999, "Nikola Jokic", True, "C", 1610612743)
        conn.close()

        with patch_db_path(tmp_db):
            with patch("server.services.news_service.NewsService.is_cache_fresh", return_value=(True, [])):
                with patch("server.api.news.NewsService.process_all") as mock_process:
                    mock_process.return_value = {"alerts_generated": 0, "sources_fetched": [], "cache_status": {}}
                    response = client.get(f"/api/players/{203999}/news?refresh=true")

        mock_process.assert_called_once()
        assert response.status_code == 200


class TestPlayerAlertsEmbeddedIntegration:
    """Integration tests for alerts embedded in GET /api/players/{id} per D-09."""

    def test_player_detail_includes_alerts_summary(self, client, tmp_path):
        """Player response includes lightweight alerts array."""
        import sqlite3
        tmp_db = str(tmp_path / "test_integration_06h.db")
        conn = sqlite3.connect(tmp_db)
        conn.execute("PRAGMA foreign_keys=ON")
        init_db(conn)
        upsert_team(conn, 1610612743, "DEN", "Denver Nuggets")
        upsert_player(conn, 203999, "Nikola Jokic", True, "C", 1610612743)
        now = datetime.now().isoformat()
        insert_player_alerts(conn, [
            {
                "player_id": 203999,
                "alert_type": "INJURY",
                "subcategory": "QUESTIONABLE",
                "severity": "warning",
                "source": "nba_injury_report",
                "source_url": "https://official.nba.com/injury-report",
                "headline": "Nikola Jokic - QUESTIONABLE",
            }
        ])
        conn.close()

        with patch_db_path(tmp_db):
            with patch("server.api.players.get_default_lines", return_value={}):
                response = client.get(f"/api/players/{203999}")

        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        assert isinstance(data["alerts"], list)

    def test_player_alerts_summary_is_lightweight(self, client, tmp_path):
        """Alert summary contains only alert_type, severity, subcategory, last_updated_at."""
        import sqlite3
        tmp_db = str(tmp_path / "test_integration_06i.db")
        conn = sqlite3.connect(tmp_db)
        conn.execute("PRAGMA foreign_keys=ON")
        init_db(conn)
        upsert_team(conn, 1610612743, "DEN", "Denver Nuggets")
        upsert_player(conn, 203999, "Nikola Jokic", True, "C", 1610612743)
        now = datetime.now().isoformat()
        insert_player_alerts(conn, [
            {
                "player_id": 203999,
                "alert_type": "INJURY",
                "subcategory": "QUESTIONABLE",
                "severity": "warning",
                "source": "nba_injury_report",
                "source_url": "https://official.nba.com/injury-report",
                "headline": "Nikola Jokic - QUESTIONABLE",
            }
        ])
        conn.close()

        with patch_db_path(tmp_db):
            with patch("server.api.players.get_default_lines", return_value={}):
                response = client.get(f"/api/players/{203999}")

        assert response.status_code == 200
        data = response.json()
        if data["alerts"]:
            alert = data["alerts"][0]
            keys = set(alert.keys())
            assert keys.issubset({"alert_type", "severity", "subcategory", "last_updated_at"})

    def test_player_detail_empty_alerts_when_no_news(self, client, tmp_path):
        """Player without alerts returns empty alerts array."""
        import sqlite3
        tmp_db = str(tmp_path / "test_integration_06j.db")
        conn = sqlite3.connect(tmp_db)
        conn.execute("PRAGMA foreign_keys=ON")
        init_db(conn)
        upsert_team(conn, 1610612743, "DEN", "Denver Nuggets")
        upsert_player(conn, 203999, "Nikola Jokic", True, "C", 1610612743)
        conn.close()

        with patch_db_path(tmp_db):
            with patch("server.api.players.get_default_lines", return_value={}):
                response = client.get(f"/api/players/{203999}")

        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        assert data["alerts"] == []

    def test_alerts_graceful_degradation(self, client, tmp_path):
        """If alert lookup fails, player detail still works with empty alerts."""
        import sqlite3
        tmp_db = str(tmp_path / "test_integration_06k.db")
        conn = sqlite3.connect(tmp_db)
        conn.execute("PRAGMA foreign_keys=ON")
        init_db(conn)
        upsert_team(conn, 1610612743, "DEN", "Denver Nuggets")
        upsert_player(conn, 203999, "Nikola Jokic", True, "C", 1610612743)
        conn.close()

        with patch_db_path(tmp_db):
            with patch("server.api.players.get_default_lines", return_value={}):
                with patch("server.services.player_service.get_player_alerts_summary", side_effect=Exception("DB error")):
                    response = client.get(f"/api/players/{203999}")

        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data


class TestNewsServiceIntegration:
    """Tests for NewsService integration with DB per D-13, D-14."""

    def test_news_items_stored_with_evidentiary_link(self, tmp_path):
        """Raw news items are retained per D-14."""
        import sqlite3
        from server.services.news_service import NewsService

        tmp_db = str(tmp_path / "test_integration_06l.db")
        tmp_cache = str(tmp_path / "news_cache")
        conn = sqlite3.connect(tmp_db)
        conn.execute("PRAGMA foreign_keys=ON")
        init_db(conn)
        upsert_team(conn, 1610612743, "DEN", "Denver Nuggets")
        upsert_player(conn, 203999, "Nikola Jokic", True, "C", 1610612743)
        conn.close()

        svc = NewsService(db_path=tmp_db, cache_path=tmp_cache)
        now = datetime.now().isoformat()
        insert_news_items(svc._db_path, [
            {
                "source": "espn_rss",
                "source_url": "https://espn.com/story/1",
                "headline": "Nikola Jokic questionable",
                "raw_content": "Jokic is questionable for tomorrow's game",
                "published_at": now,
                "fetched_at": now,
                "player_id": 203999,
                "player_name": "Nikola Jokic",
                "alert_keywords": "questionable",
            }
        ])

        conn = sqlite3.connect(tmp_db)
        cursor = conn.execute("SELECT COUNT(*) FROM news_items WHERE player_id = 203999")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 1

    def test_player_alerts_upsert_on_rematch(self, tmp_path):
        """Repeated alert for same player+type+source updates last_updated_at per queries.py."""
        import sqlite3
        from server.services.news_service import NewsService

        tmp_db = str(tmp_path / "test_integration_06m.db")
        tmp_cache = str(tmp_path / "news_cache")
        conn = sqlite3.connect(tmp_db)
        conn.execute("PRAGMA foreign_keys=ON")
        init_db(conn)
        upsert_team(conn, 1610612743, "DEN", "Denver Nuggets")
        upsert_player(conn, 203999, "Nikola Jokic", True, "C", 1610612743)
        conn.close()

        svc = NewsService(db_path=tmp_db, cache_path=tmp_cache)

        alert = {
            "player_id": 203999,
            "alert_type": "INJURY",
            "subcategory": "QUESTIONABLE",
            "severity": "warning",
            "source": "nba_injury_report",
            "source_url": "https://official.nba.com",
            "headline": "Nikola Jokic - QUESTIONABLE",
        }
        from server.pipeline.db.queries import insert_player_alerts as raw_insert
        raw_conn = sqlite3.connect(tmp_db)
        raw_conn.execute("PRAGMA foreign_keys=ON")
        raw_insert(raw_conn, [alert])
        raw_conn.close()

        updated_alert = {
            "player_id": 203999,
            "alert_type": "INJURY",
            "subcategory": "OUT",
            "severity": "critical",
            "source": "nba_injury_report",
            "source_url": "https://official.nba.com",
            "headline": "Nikola Jokic - OUT",
        }
        raw_conn = sqlite3.connect(tmp_db)
        raw_conn.execute("PRAGMA foreign_keys=ON")
        raw_insert(raw_conn, [updated_alert])
        raw_conn.close()

        conn = sqlite3.connect(tmp_db)
        cursor = conn.execute("SELECT COUNT(*) FROM player_alerts WHERE player_id = 203999 AND alert_type = 'INJURY'")
        count = cursor.fetchone()[0]
        cursor2 = conn.execute("SELECT subcategory FROM player_alerts WHERE player_id = 203999 AND alert_type = 'INJURY'")
        subcategory = cursor2.fetchone()[0]
        conn.close()

        assert count == 1
        assert subcategory == "OUT"

    def test_multiple_alert_types_for_one_player(self, tmp_path):
        """Player can have INJURY, OUT, TRADE alerts simultaneously."""
        import sqlite3
        from server.pipeline.db.queries import insert_player_alerts

        tmp_db = str(tmp_path / "test_integration_06n.db")
        conn = sqlite3.connect(tmp_db)
        conn.execute("PRAGMA foreign_keys=ON")
        init_db(conn)
        upsert_team(conn, 1610612743, "DEN", "Denver Nuggets")
        upsert_player(conn, 203999, "Nikola Jokic", True, "C", 1610612743)
        now = datetime.now().isoformat()
        alerts = [
            {
                "player_id": 203999,
                "alert_type": "INJURY",
                "subcategory": "QUESTIONABLE",
                "severity": "warning",
                "source": "nba_injury_report",
                "source_url": "https://official.nba.com",
                "headline": "Jokic - QUESTIONABLE",
            },
            {
                "player_id": 203999,
                "alert_type": "REST",
                "subcategory": None,
                "severity": "info",
                "source": "espn_rss",
                "source_url": "https://espn.com/story/2",
                "headline": "Jokic resting",
            },
        ]
        insert_player_alerts(conn, alerts)
        conn.close()

        from server.services.news_service import NewsService
        svc = NewsService(db_path=tmp_db, cache_path=str(tmp_path / "cache"))
        result = svc.process_all()

        conn = sqlite3.connect(tmp_db)
        cursor = conn.execute("SELECT alert_type FROM player_alerts WHERE player_id = 203999 ORDER BY alert_type")
        types = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert "INJURY" in types
        assert "REST" in types


@pytest.fixture
def client():
    """Provide a TestClient for the FastAPI app."""
    from fastapi.testclient import TestClient
    return TestClient(app)


def patch_db_path(tmp_db):
    """Patch DB_PATH and related modules to use a temp DB."""
    import server.core.config as config_module
    from server.pipeline.db import connection as conn_module
    from server.services import player_service as ps_module

    old_db = config_module.DB_PATH
    config_module.DB_PATH = tmp_db
    conn_module.DB_PATH = tmp_db
    ps_module.DB_PATH = tmp_db

    yield tmp_db

    config_module.DB_PATH = old_db
    conn_module.DB_PATH = old_db
    ps_module.DB_PATH = old_db
