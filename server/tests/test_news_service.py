import sqlite3
import tempfile
import shutil
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from server.pipeline.db.connection import get_connection
from server.pipeline.db.schema import init_db
from server.pipeline.db.queries import (
    insert_news_items,
    insert_player_alerts,
    get_player_alerts,
    get_news_items,
    get_stale_alerts,
    cleanup_stale_news,
    cleanup_expired_alerts,
    upsert_player,
    upsert_team,
)
from server.core.config import (
    ESPN_RSS_URL,
    NBA_RSS_URL,
    NBA_INJURY_REPORT_URL,
    NEWS_TTL_HOURS,
    NEWS_STALE_WARNING_HOURS,
    ALERT_CATEGORIES,
)


class TestNewsSchema:
    """Tests for news_items and player_alerts table creation via init_db."""

    def test_init_db_creates_news_items_table(self, tmp_db):
        """Schema creates news_items table with correct columns."""
        cursor = tmp_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='news_items'"
        )
        assert cursor.fetchone() is not None

    def test_init_db_creates_player_alerts_table(self, tmp_db):
        """Schema creates player_alerts table with correct columns."""
        cursor = tmp_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='player_alerts'"
        )
        assert cursor.fetchone() is not None

    def test_news_items_has_correct_columns(self, tmp_db):
        """news_items table has all required columns."""
        cursor = tmp_db.execute("PRAGMA table_info(news_items)")
        columns = {row[1] for row in cursor.fetchall()}
        required = {"id", "source", "source_url", "headline", "raw_content",
                    "published_at", "fetched_at", "player_id", "player_name", "alert_keywords"}
        assert required.issubset(columns)

    def test_player_alerts_has_correct_columns(self, tmp_db):
        """player_alerts table has all required columns."""
        cursor = tmp_db.execute("PRAGMA table_info(player_alerts)")
        columns = {row[1] for row in cursor.fetchall()}
        required = {"id", "player_id", "alert_type", "subcategory", "severity",
                    "source", "source_url", "headline", "first_seen_at", "last_updated_at"}
        assert required.issubset(columns)

    def test_player_alerts_foreign_key_to_players(self, tmp_db):
        """player_alerts.player_id references players.player_id."""
        cursor = tmp_db.execute("PRAGMA foreign_key_list(player_alerts)")
        fks = cursor.fetchall()
        assert any(fk[2] == "players" and fk[3] == "player_id" for fk in fks)

    def test_news_items_indexes_exist(self, tmp_db):
        """Indexes are created for news_items table."""
        cursor = tmp_db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='news_items'"
        )
        indexes = {row[0] for row in cursor.fetchall()}
        assert "idx_news_items_player" in indexes
        assert "idx_news_items_source" in indexes

    def test_player_alerts_indexes_exist(self, tmp_db):
        """Indexes are created for player_alerts table."""
        cursor = tmp_db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='player_alerts'"
        )
        indexes = {row[0] for row in cursor.fetchall()}
        assert "idx_player_alerts_player" in indexes
        assert "idx_player_alerts_type" in indexes


class TestInsertNewsItems:
    """Tests for insert_news_items function."""

    def test_insert_news_items_basic(self, tmp_db):
        """insert_news_items inserts rows successfully."""
        items = [
            {
                "source": "espn_rss",
                "source_url": "https://espn.com/story/1",
                "headline": "LeBron James questionable",
                "raw_content": "LeBron James is questionable with knee soreness",
                "published_at": "2024-01-15T10:00:00",
                "fetched_at": "2024-01-15T12:00:00",
                "player_id": 2544,
                "player_name": "LeBron James",
                "alert_keywords": "questionable,injury",
            }
        ]
        insert_news_items(tmp_db, items)
        cursor = tmp_db.execute("SELECT COUNT(*) FROM news_items")
        assert cursor.fetchone()[0] == 1

    def test_insert_news_items_ignores_duplicates(self, tmp_db):
        """Duplicate news items are ignored via INSERT OR IGNORE."""
        item = {
            "source": "espn_rss",
            "source_url": "https://espn.com/story/1",
            "headline": "LeBron James questionable",
            "raw_content": "Content",
            "published_at": "2024-01-15T10:00:00",
            "fetched_at": "2024-01-15T12:00:00",
            "player_id": 2544,
            "player_name": "LeBron James",
            "alert_keywords": None,
        }
        insert_news_items(tmp_db, [item])
        insert_news_items(tmp_db, [item])
        cursor = tmp_db.execute("SELECT COUNT(*) FROM news_items")
        assert cursor.fetchone()[0] == 1


class TestInsertPlayerAlerts:
    """Tests for insert_player_alerts function."""

    @pytest.fixture
    def db_with_player(self, tmp_db):
        """Provide a DB with a test player."""
        upsert_team(tmp_db, 1610612747, "LAL", "Los Angeles Lakers")
        upsert_player(tmp_db, 2544, "LeBron James", True, "F", 1610612747)
        return tmp_db

    def test_insert_player_alerts_basic(self, db_with_player):
        """insert_player_alerts inserts alerts successfully."""
        alerts = [
            {
                "player_id": 2544,
                "alert_type": "INJURY",
                "subcategory": "QUESTIONABLE",
                "severity": "warning",
                "source": "nba_injury_report",
                "source_url": "https://official.nba.com/injury-report",
                "headline": "LeBron James - QUESTIONABLE - knee soreness",
            }
        ]
        insert_player_alerts(db_with_player, alerts)
        result = get_player_alerts(db_with_player, 2544)
        assert len(result) == 1
        assert result[0]["alert_type"] == "INJURY"
        assert result[0]["severity"] == "warning"

    def test_insert_player_alerts_upserts_on_rematch(self, db_with_player):
        """Same player+type+source updates last_updated_at and severity."""
        alert = {
            "player_id": 2544,
            "alert_type": "INJURY",
            "subcategory": "QUESTIONABLE",
            "severity": "warning",
            "source": "nba_injury_report",
            "source_url": "https://official.nba.com/injury-report",
            "headline": "LeBron James - QUESTIONABLE - knee soreness",
        }
        insert_player_alerts(db_with_player, [alert])

        updated_alert = {
            "player_id": 2544,
            "alert_type": "INJURY",
            "subcategory": "OUT",
            "severity": "critical",
            "source": "nba_injury_report",
            "source_url": "https://official.nba.com/injury-report",
            "headline": "LeBron James - OUT - knee soreness",
        }
        insert_player_alerts(db_with_player, [updated_alert])

        result = get_player_alerts(db_with_player, 2544)
        assert len(result) == 1
        assert result[0]["subcategory"] == "OUT"
        assert result[0]["severity"] == "critical"
        assert result[0]["headline"] == "LeBron James - OUT - knee soreness"


class TestGetPlayerAlerts:
    """Tests for get_player_alerts function."""

    @pytest.fixture
    def db_with_alerts(self, tmp_db):
        """Provide a DB with test player and alerts."""
        upsert_team(tmp_db, 1610612747, "LAL", "Los Angeles Lakers")
        upsert_player(tmp_db, 2544, "LeBron James", True, "F", 1610612747)
        now = datetime.now()
        hour_ago = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
        two_hours_ago = (now - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S")
        tmp_db.execute(
            """INSERT INTO player_alerts (player_id, alert_type, subcategory, severity, source, source_url, headline, first_seen_at, last_updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (2544, "INJURY", "QUESTIONABLE", "warning", "nba_injury_report",
             "https://official.nba.com/injury-report", "LeBron James - QUESTIONABLE",
             hour_ago, hour_ago)
        )
        tmp_db.execute(
            """INSERT INTO player_alerts (player_id, alert_type, subcategory, severity, source, source_url, headline, first_seen_at, last_updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (2544, "REST", None, "info", "espn_rss",
             "https://espn.com/story/2", "LeBron James resting",
             two_hours_ago, two_hours_ago)
        )
        tmp_db.commit()
        return tmp_db

    def test_get_player_alerts_returns_alerts(self, db_with_alerts):
        """get_player_alerts returns alerts for the given player."""
        result = get_player_alerts(db_with_alerts, 2544)
        assert len(result) == 2

    def test_get_player_alerts_ordered_by_last_updated_desc(self, db_with_alerts):
        """Alerts are ordered by last_updated_at DESC."""
        result = get_player_alerts(db_with_alerts, 2544)
        alert_types = [r["alert_type"] for r in result]
        assert alert_types == ["INJURY", "REST"]


class TestGetNewsItems:
    """Tests for get_news_items function."""

    @pytest.fixture
    def db_with_news(self, tmp_db):
        """Provide a DB with test news items."""
        upsert_team(tmp_db, 1610612747, "LAL", "Los Angeles Lakers")
        upsert_player(tmp_db, 2544, "LeBron James", True, "F", 1610612747)
        items = [
            {
                "source": "espn_rss",
                "source_url": "https://espn.com/story/1",
                "headline": "LeBron James questionable",
                "raw_content": "LeBron is questionable",
                "published_at": "2024-01-15T10:00:00",
                "fetched_at": "2024-01-15T12:00:00",
                "player_id": 2544,
                "player_name": "LeBron James",
                "alert_keywords": "questionable",
            },
            {
                "source": "nba_rss",
                "source_url": "https://nba.com/story/2",
                "headline": "LeBron traded",
                "raw_content": "LeBron was traded",
                "published_at": "2024-01-14T10:00:00",
                "fetched_at": "2024-01-14T12:00:00",
                "player_id": 2544,
                "player_name": "LeBron James",
                "alert_keywords": "trade",
            },
        ]
        insert_news_items(tmp_db, items)
        return tmp_db

    def test_get_news_items_returns_items(self, db_with_news):
        """get_news_items returns news items for the given player."""
        result = get_news_items(db_with_news, 2544)
        assert len(result) == 2

    def test_get_news_items_ordered_by_published_at_desc(self, db_with_news):
        """News items are ordered by published_at DESC."""
        result = get_news_items(db_with_news, 2544)
        assert result[0]["headline"] == "LeBron James questionable"
        assert result[1]["headline"] == "LeBron traded"

    def test_get_news_items_respects_limit(self, db_with_news):
        """get_news_items respects the limit parameter."""
        result = get_news_items(db_with_news, 2544, limit=1)
        assert len(result) == 1


class TestKeywordMatching:
    """Tests for keyword matching categorization."""

    def test_categorize_injury(self):
        """'LeBron James questionable with knee soreness' → INJURY."""
        text = "LeBron James questionable with knee soreness"
        found_type = None
        for alert_type, config in ALERT_CATEGORIES.items():
            if any(kw in text.lower() for kw in config["keywords"]):
                found_type = alert_type
                break
        assert found_type == "INJURY"

    def test_categorize_out(self):
        """'Jayson Tatum ruled out for personal reasons' → OUT."""
        text = "Jayson Tatum ruled out for personal reasons"
        found_type = None
        for alert_type, config in ALERT_CATEGORIES.items():
            if any(kw in text.lower() for kw in config["keywords"]):
                found_type = alert_type
                break
        assert found_type == "OUT"

    def test_categorize_trade(self):
        """'Kevin Durant traded to Phoenix' → TRADE."""
        text = "Kevin Durant traded to Phoenix"
        found_type = None
        for alert_type, config in ALERT_CATEGORIES.items():
            if any(kw in text.lower() for kw in config["keywords"]):
                found_type = alert_type
                break
        assert found_type == "TRADE"

    def test_categorize_questionable(self):
        """'Player questionable for game' → QUESTIONABLE."""
        text = "Player is questionable for tonight's game"
        found_type = None
        for alert_type, config in ALERT_CATEGORIES.items():
            if any(kw in text.lower() for kw in config["keywords"]):
                found_type = alert_type
                break
        assert found_type == "QUESTIONABLE"

    def test_categorize_suspension(self):
        """'Player suspended for 10 games' → SUSPENSION."""
        text = "Player suspended indefinitely for conduct"
        found_type = None
        for alert_type, config in ALERT_CATEGORIES.items():
            if any(kw in text.lower() for kw in config["keywords"]):
                found_type = alert_type
                break
        assert found_type == "SUSPENSION"

    def test_categorize_g_league(self):
        """'Player assigned to G League' → G_LEAGUE."""
        text = "Player recalled from G League"
        found_type = None
        for alert_type, config in ALERT_CATEGORIES.items():
            if any(kw in text.lower() for kw in config["keywords"]):
                found_type = alert_type
                break
        assert found_type == "G_LEAGUE"

    def test_categorize_rest(self):
        """'Player resting for load management' → REST."""
        text = "Player on rest day due to load management"
        found_type = None
        for alert_type, config in ALERT_CATEGORIES.items():
            if any(kw in text.lower() for kw in config["keywords"]):
                found_type = alert_type
                break
        assert found_type == "REST"

    def test_severity_mapping_injury(self):
        """INJURY category maps to severity 'warning'."""
        assert ALERT_CATEGORIES["INJURY"]["severity"] == "warning"

    def test_severity_mapping_out(self):
        """OUT category maps to severity 'critical'."""
        assert ALERT_CATEGORIES["OUT"]["severity"] == "critical"

    def test_severity_mapping_rest(self):
        """REST category maps to severity 'info'."""
        assert ALERT_CATEGORIES["REST"]["severity"] == "info"


class TestConfigConstants:
    """Tests for news-related config constants."""

    def test_news_rss_urls_defined(self):
        """ESPN_RSS_URL, NBA_RSS_URL, NBA_INJURY_REPORT_URL are defined."""
        assert ESPN_RSS_URL is not None
        assert NBA_RSS_URL is not None
        assert NBA_INJURY_REPORT_URL is not None

    def test_news_ttl_hours_is_six(self):
        """NEWS_TTL_HOURS is 6 (within 4-6 hour range)."""
        assert NEWS_TTL_HOURS == 6

    def test_news_stale_warning_hours_is_24(self):
        """NEWS_STALE_WARNING_HOURS is 24."""
        assert NEWS_STALE_WARNING_HOURS == 24

    def test_alert_categories_has_all_seven(self):
        """ALERT_CATEGORIES has all 7 required categories."""
        expected = {"INJURY", "OUT", "QUESTIONABLE", "TRADE", "SUSPENSION", "G_LEAGUE", "REST"}
        assert set(ALERT_CATEGORIES.keys()) == expected


class TestStaleAlerts:
    """Tests for stale alert detection."""

    @pytest.fixture
    def db_with_stale_alerts(self, tmp_db):
        """Provide a DB with a stale alert."""
        upsert_team(tmp_db, 1610612747, "LAL", "Los Angeles Lakers")
        upsert_player(tmp_db, 2544, "LeBron James", True, "F", 1610612747)

        old_time = (datetime.now() - timedelta(hours=30)).strftime("%Y-%m-%dT%H:%M:%S")
        tmp_db.execute(
            """INSERT INTO player_alerts (player_id, alert_type, subcategory, severity, source, source_url, headline, first_seen_at, last_updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (2544, "INJURY", "QUESTIONABLE", "warning", "nba_injury_report",
             "https://official.nba.com", "LeBron James - QUESTIONABLE",
             old_time, old_time)
        )
        tmp_db.commit()
        return tmp_db

    def test_get_stale_alerts_detects_old_alerts(self, db_with_stale_alerts):
        """get_stale_alerts returns alerts older than max_age_hours."""
        stale = get_stale_alerts(db_with_stale_alerts, max_age_hours=24)
        assert len(stale) == 1
        assert stale[0]["player_id"] == 2544

    def test_get_stale_alerts_excludes_recent_alerts(self, db_with_stale_alerts):
        """get_stale_alerts excludes alerts within max_age_hours."""
        stale = get_stale_alerts(db_with_stale_alerts, max_age_hours=48)
        assert len(stale) == 0


class TestNewsServiceIntegration:
    """Integration tests for NewsService (Plan 01 Task 2)."""

    @pytest.fixture
    def news_service(self, tmp_path):
        """Provide a NewsService with temporary DB path and cache."""
        tmp_db_path = str(tmp_path / "test_news.db")
        tmp_cache = str(tmp_path / "news_cache")
        from server.services.news_service import NewsService
        svc = NewsService(db_path=tmp_db_path, cache_path=tmp_cache)
        conn = get_connection(tmp_db_path)
        init_db(conn)
        conn.close()
        yield svc
        shutil.rmtree(tmp_cache, ignore_errors=True)

    @pytest.fixture
    def svc_db(self, news_service):
        """Provide a DB connection for the news_service's DB."""
        from server.pipeline.db.connection import get_connection
        conn = get_connection(news_service._db_path)
        init_db(conn)
        yield conn
        conn.close()

    def test_match_player_name_exact(self, news_service, svc_db):
        """match_player_name finds player via exact match."""
        upsert_team(svc_db, 1610612743, "DEN", "Denver Nuggets")
        upsert_player(svc_db, 203999, "Nikola Jokic", True, "C", 1610612743)
        player_id, full_name = news_service.match_player_name("Nikola Jokic")
        assert player_id == 203999
        assert full_name == "Nikola Jokic"

    def test_match_player_name_fuzzy_accent(self, news_service, svc_db):
        """match_player_name handles accented characters (Jokic/Jokic)."""
        upsert_team(svc_db, 1610612743, "DEN", "Denver Nuggets")
        upsert_player(svc_db, 203999, "Nikola Jokic", True, "C", 1610612743)
        player_id, full_name = news_service.match_player_name("Jokic")
        assert player_id == 203999

    def test_match_player_name_nickname(self, news_service, svc_db):
        """match_player_name handles nickname (LeBron → LeBron James)."""
        upsert_team(svc_db, 1610612747, "LAL", "Los Angeles Lakers")
        upsert_player(svc_db, 2544, "LeBron James", True, "F", 1610612747)
        player_id, full_name = news_service.match_player_name("LeBron")
        assert player_id == 2544

    def test_match_player_name_last_name_only(self, news_service, svc_db):
        """match_player_name handles last-name only (Embiid → Joel Embiid)."""
        upsert_team(svc_db, 1610612743, "DEN", "Denver Nuggets")
        upsert_player(svc_db, 203999, "Nikola Jokic", True, "C", 1610612743)
        upsert_team(svc_db, 1610612755, "PHI", "Philadelphia 76ers")
        upsert_player(svc_db, 203954, "Joel Embiid", True, "C", 1610612755)
        player_id, full_name = news_service.match_player_name("Embiid")
        assert player_id == 203954

    def test_match_player_id_direct(self, news_service, svc_db):
        """match_player_id looks up player by ID directly."""
        upsert_team(svc_db, 1610612743, "DEN", "Denver Nuggets")
        upsert_player(svc_db, 203999, "Nikola Jokic", True, "C", 1610612743)
        player_id, full_name = news_service.match_player_id(203999)
        assert player_id == 203999
        assert full_name == "Nikola Jokic"

    def test_match_player_id_not_found(self, news_service, svc_db):
        """match_player_id returns (None, None) for unknown ID."""
        player_id, full_name = news_service.match_player_id(999999)
        assert player_id is None

    def test_generate_alerts_injury_keyword(self, news_service):
        """generate_alerts categorizes 'LeBron James questionable' as INJURY."""
        items = [
            {
                "source": "espn_rss",
                "source_url": "https://espn.com/story/1",
                "headline": "LeBron James questionable with knee soreness",
                "raw_content": "",
                "published_at": "2024-01-15T10:00:00",
                "fetched_at": "2024-01-15T12:00:00",
                "player_id": 2544,
                "player_name": "LeBron James",
                "alert_keywords": None,
            }
        ]
        alerts = news_service.generate_alerts(items)
        assert len(alerts) == 1
        assert alerts[0]["alert_type"] == "INJURY"
        assert alerts[0]["severity"] == "warning"

    def test_generate_alerts_out_keyword(self, news_service):
        """generate_alerts categorizes 'Jayson Tatum ruled out' as OUT."""
        items = [
            {
                "source": "espn_rss",
                "source_url": "https://espn.com/story/1",
                "headline": "Jayson Tatum ruled out for personal reasons",
                "raw_content": "",
                "published_at": "2024-01-15T10:00:00",
                "fetched_at": "2024-01-15T12:00:00",
                "player_id": 1628369,
                "player_name": "Jayson Tatum",
                "alert_keywords": None,
            }
        ]
        alerts = news_service.generate_alerts(items)
        assert len(alerts) == 1
        assert alerts[0]["alert_type"] == "OUT"
        assert alerts[0]["severity"] == "critical"

    def test_generate_alerts_trade_keyword(self, news_service):
        """generate_alerts categorizes 'Kevin Durant traded' as TRADE."""
        items = [
            {
                "source": "espn_rss",
                "source_url": "https://espn.com/story/1",
                "headline": "Kevin Durant traded to Phoenix",
                "raw_content": "",
                "published_at": "2024-01-15T10:00:00",
                "fetched_at": "2024-01-15T12:00:00",
                "player_id": 201142,
                "player_name": "Kevin Durant",
                "alert_keywords": None,
            }
        ]
        alerts = news_service.generate_alerts(items)
        assert len(alerts) == 1
        assert alerts[0]["alert_type"] == "TRADE"
        assert alerts[0]["severity"] == "warning"

    def test_generate_alerts_priority_out_over_injury(self, news_service):
        """OUT takes priority over INJURY when both match."""
        items = [
            {
                "source": "nba_injury_report",
                "source_url": "https://official.nba.com",
                "headline": "Player ruled out with injury",
                "raw_content": "",
                "published_at": "2024-01-15T10:00:00",
                "fetched_at": "2024-01-15T12:00:00",
                "player_id": 2544,
                "player_name": "LeBron James",
                "alert_keywords": None,
            }
        ]
        alerts = news_service.generate_alerts(items)
        assert len(alerts) == 1
        assert alerts[0]["alert_type"] == "OUT"

    def test_generate_alerts_graceful_no_match(self, news_service):
        """generate_alerts returns empty when no player_id and name doesn't match."""
        items = [
            {
                "source": "espn_rss",
                "source_url": "https://espn.com/story/1",
                "headline": "Random NBA news",
                "raw_content": "",
                "published_at": "2024-01-15T10:00:00",
                "fetched_at": "2024-01-15T12:00:00",
                "player_id": None,
                "player_name": None,
                "alert_keywords": None,
            }
        ]
        alerts = news_service.generate_alerts(items)
        assert len(alerts) == 0

    def test_is_cache_fresh_no_data(self, news_service):
        """is_cache_fresh returns (True, []) when no news items exist."""
        is_fresh, stale = news_service.is_cache_fresh()
        assert is_fresh is True
        assert stale == []

    def test_is_cache_fresh_with_fresh_data(self, news_service, svc_db):
        """is_cache_fresh returns (True, []) when data is within TTL."""
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        svc_db.execute(
            """INSERT INTO news_items (source, source_url, headline, published_at, fetched_at, player_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("espn_rss", "https://espn.com", "Test headline", now, now, 2544)
        )
        svc_db.commit()
        is_fresh, stale = news_service.is_cache_fresh()
        assert is_fresh is True
        assert "espn_rss" not in stale

    def test_is_cache_fresh_stale_after_ttl(self, news_service, svc_db):
        """is_cache_fresh marks source stale after NEWS_TTL_HOURS."""
        old_time = (datetime.now() - timedelta(hours=7)).strftime("%Y-%m-%dT%H:%M:%S")
        svc_db.execute(
            """INSERT INTO news_items (source, source_url, headline, published_at, fetched_at, player_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("espn_rss", "https://espn.com", "Test headline", old_time, old_time, 2544)
        )
        svc_db.commit()
        is_fresh, stale = news_service.is_cache_fresh()
        assert is_fresh is False
        assert "espn_rss" in stale

    def test_process_all_handles_empty_db(self, news_service):
        """process_all completes without error on empty DB."""
        result = news_service.process_all()
        assert "alerts_generated" in result
        assert "sources_fetched" in result
        assert "cache_status" in result

    def test_process_all_graceful_degradation_on_fetch_error(self, news_service):
        """process_all returns partial results when some sources fail."""
        with patch.object(news_service, "fetch_rss", side_effect=Exception("Network error")):
            with patch.object(news_service, "fetch_injury_report", return_value=[]):
                result = news_service.process_all()
                assert "alerts_generated" in result
                assert isinstance(result["sources_fetched"], list)

    def test_categorize_injury_status_out(self, news_service):
        """_categorize_injury_status maps 'ruled out' to OUT/critical."""
        alert_type, subcategory, severity = news_service._categorize_injury_status("ruled out for tonight")
        assert alert_type == "OUT"
        assert severity == "critical"

    def test_categorize_injury_status_questionable(self, news_service):
        """_categorize_injury_status maps 'questionable' to INJURY/QUESTIONABLE."""
        alert_type, subcategory, severity = news_service._categorize_injury_status("questionable (left knee)")
        assert alert_type == "INJURY"
        assert subcategory == "QUESTIONABLE"
        assert severity == "warning"

    def test_categorize_injury_status_probable(self, news_service):
        """_categorize_injury_status maps 'probable' to INJURY/PROBABLE."""
        alert_type, subcategory, severity = news_service._categorize_injury_status("probable (ankle)")
        assert alert_type == "INJURY"
        assert subcategory == "PROBABLE"
        assert severity == "warning"

    def test_categorize_injury_status_rest(self, news_service):
        """_categorize_injury_status maps 'load management' to REST/info."""
        alert_type, subcategory, severity = news_service._categorize_injury_status("load management")
        assert alert_type == "REST"
        assert severity == "info"

    def test_categorize_injury_status_suspended(self, news_service):
        """_categorize_injury_status maps 'suspended' to SUSPENSION/critical."""
        alert_type, subcategory, severity = news_service._categorize_injury_status("suspended indefinitely")
        assert alert_type == "SUSPENSION"
        assert severity == "critical"

    def test_normalize_name_removes_accents(self, news_service):
        """_normalize_name converts accented characters to ASCII."""
        normalized = news_service._normalize_name("Nikola Jokic")
        assert normalized == "nikola jokic"

    def test_fuzzy_match_high_overlap(self, news_service):
        """_fuzzy_match returns True for >= 80% token overlap."""
        assert news_service._fuzzy_match("jokic", "nikola jokic") is True

    def test_fuzzy_match_subset(self, news_service):
        """_fuzzy_match returns True when one name is subset of other."""
        assert news_service._fuzzy_match("lebron", "lebron james") is True

    def test_fuzzy_match_low_overlap(self, news_service):
        """_fuzzy_match returns False for < 80% token overlap."""
        assert news_service._fuzzy_match("kobe", "lebron james") is False

