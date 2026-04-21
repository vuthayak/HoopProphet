import logging
import re
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Optional

import feedparser
import requests
from requests_cache import CachedSession
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from server.core.config import (
    CACHE_PATH,
    DB_PATH,
    ESPN_RSS_URL,
    NBA_INJURY_REPORT_URL,
    NBA_RSS_URL,
    NEWS_CLEANUP_DAYS,
    NEWS_STALE_WARNING_HOURS,
    NEWS_TTL_HOURS,
    ALERT_CATEGORIES,
)
from server.pipeline.db.connection import get_connection
from server.pipeline.db.queries import (
    cleanup_expired_alerts,
    cleanup_stale_news,
    get_news_items,
    get_players_df,
    get_player_alerts,
    insert_news_items,
    insert_player_alerts,
)
from server.pipeline.db.schema import init_db

logger = logging.getLogger(__name__)


def setup_cached_session(cache_path: str) -> CachedSession:
    """Configure HTTP caching for news fetches."""
    session = CachedSession(
        cache_name=cache_path,
        backend="sqlite",
        expire_after=None,
        allowable_methods=["GET", "POST"],
        stale_if_error=True,
    )
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.nba.com/",
        "Accept-Language": "en-US,en;q=0.9",
    })
    return session


class NewsService:
    """News and injury flag service — fetches NBA injury reports, RSS feeds,
    matches player names, generates alerts, and manages TTL-based caching.

    Follows the NBAClient pattern: rate-limited HTTP, tenacity retry,
    cached session for HTTP caching.
    """

    MIN_DELAY = 0.6

    def __init__(self, db_path: str = None, cache_path: str = None):
        if db_path is None:
            db_path = DB_PATH
        self._db_path = db_path
        if cache_path is None:
            cache_path = CACHE_PATH
        self._cache_path = cache_path
        self._last_call = 0.0
        self._session = setup_cached_session(cache_path)
        self._logger = logging.getLogger(__name__)

    def _enforce_rate_limit(self):
        """Apply minimum delay between HTTP calls."""
        elapsed = time.time() - self._last_call
        if elapsed < self.MIN_DELAY:
            time.sleep(self.MIN_DELAY - elapsed)
        self._last_call = time.time()

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential_jitter(initial=0.6, max=30, jitter=2),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, ValueError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def fetch_injury_report(self) -> list[dict]:
        """Fetch NBA Official Injury Report and extract player alerts.

        Parses the HTML injury report page to extract player name, team,
        status (probable/questionable/doubtful/out), and injury description.
        Returns list of alert dicts with player_id (if matched), alert_type,
        subcategory, severity, source, source_url, and headline.
        """
        self._enforce_rate_limit()
        self._logger.info("Fetching NBA injury report from %s", NBA_INJURY_REPORT_URL)

        try:
            response = self._session.get(NBA_INJURY_REPORT_URL, timeout=30)
            response.raise_for_status()
            content = response.text
        except Exception as e:
            self._logger.warning("Failed to fetch NBA injury report: %s", e)
            return []

        alerts = self._parse_injury_report_html(content)
        self._logger.info("Parsed %d alerts from NBA injury report", len(alerts))
        return alerts

    def _parse_injury_report_html(self, html: str) -> list[dict]:
        """Parse NBA injury report HTML into structured alert dicts.

        The NBA injury report HTML structure changes periodically.
        If parsing fails, log a warning and return empty list.
        """
        try:
            alerts = []
            players_df = None

            pattern = re.compile(
                r'<td[^>]*class="player[^"]*"[^>]*>(.*?)</td>',
                re.IGNORECASE | re.DOTALL,
            )
            status_pattern = re.compile(
                r'<td[^>]*class="status[^"]*"[^>]*>(.*?)</td>',
                re.IGNORECASE | re.DOTALL,
            )

            player_cells = pattern.findall(html)
            status_cells = status_pattern.findall(html)

            if not player_cells and not status_cells:
                self._logger.warning(
                    "NBA injury report HTML structure may have changed — no player/status cells found"
                )
                return []

            min_len = min(len(player_cells), len(status_cells))
            for i in range(min_len):
                raw_name = re.sub(r'<[^>]+>', '', player_cells[i]).strip()
                raw_name = unicodedata.normalize('NFKD', raw_name).encode('ascii', 'ignore').decode('ascii')
                if not raw_name or len(raw_name) < 3:
                    continue

                status_html = status_cells[i]
                status_text = re.sub(r'<[^>]+>', '', status_html).strip().lower()

                alert_type, subcategory, severity = self._categorize_injury_status(status_text)

                player_id, matched_name = self.match_player_name(raw_name)

                headline = f"{raw_name} - {status_text.upper()}"

                alerts.append({
                    "player_id": player_id,
                    "player_name": matched_name or raw_name,
                    "alert_type": alert_type,
                    "subcategory": subcategory,
                    "severity": severity,
                    "source": "nba_injury_report",
                    "source_url": NBA_INJURY_REPORT_URL,
                    "headline": headline,
                })

            return alerts

        except Exception as e:
            self._logger.warning("Failed to parse NBA injury report HTML: %s", e)
            return []

    def _categorize_injury_status(self, status_text: str) -> tuple[str, Optional[str], str]:
        """Categorize NBA injury report status text into alert type, subcategory, and severity.

        Returns (alert_type, subcategory, severity).
        """
        status_lower = status_text.lower()

        if any(kw in status_lower for kw in ["ruled out", "out", "not playing", "did not play"]):
            return "OUT", None, "critical"
        if any(kw in status_lower for kw in ["doubtful"]):
            return "INJURY", "DOUBTFUL", "warning"
        if any(kw in status_lower for kw in ["questionable", "gtc", "game-time decision"]):
            return "INJURY", "QUESTIONABLE", "warning"
        if any(kw in status_lower for kw in ["probable"]):
            return "INJURY", "PROBABLE", "warning"
        if any(kw in status_lower for kw in ["rest", "load management", "rest day"]):
            return "REST", None, "info"
        if any(kw in status_lower for kw in ["suspended", "suspension", "banned", "indefinitely"]):
            return "SUSPENSION", None, "critical"
        if any(kw in status_lower for kw in ["g league", "g-league", "assigned to", "recalled from", "two-way"]):
            return "G_LEAGUE", None, "info"

        return "INJURY", status_text or None, "warning"

    def fetch_rss(self, source_url: str) -> list[dict]:
        """Fetch and parse an RSS feed (ESPN or NBA.com).

        Returns list of news item dicts with source, source_url, headline,
        raw_content, published_at. Uses feedparser for robust RSS parsing.
        """
        self._enforce_rate_limit()
        self._logger.info("Fetching RSS feed from %s", source_url)

        try:
            response = self._session.get(source_url, timeout=10)
            response.raise_for_status()
            feed = feedparser.parse(response.text)
            if not feed.entries:
                self._logger.warning("No entries found in RSS feed: %s", source_url)
                return []

            source_name = "espn_rss" if "espn" in source_url else "nba_rss"
            items = []

            for entry in feed.entries:
                published_at = None
                if hasattr(entry, "published") and entry.published:
                    try:
                        published_at = entry.published
                    except Exception:
                        pass

                if not published_at:
                    published_at = datetime.utcnow().isoformat()

                headline = getattr(entry, "title", "") or ""
                raw_content = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
                source_url_val = getattr(entry, "link", "") or source_url

                items.append({
                    "source": source_name,
                    "source_url": source_url_val,
                    "headline": headline.strip(),
                    "raw_content": raw_content.strip(),
                    "published_at": published_at,
                    "fetched_at": datetime.utcnow().isoformat(),
                    "player_id": None,
                    "player_name": None,
                    "alert_keywords": None,
                })

            self._logger.info("Parsed %d items from %s RSS feed", len(items), source_name)
            return items

        except Exception as e:
            self._logger.warning("Failed to fetch RSS feed %s: %s", source_url, e)
            return []

    def match_player_name(self, news_name: str) -> tuple[Optional[int], Optional[str]]:
        """Fuzzy match a player name from news text against the players table.

        Returns (player_id, full_name) tuple or (None, None) if no match found.

        Matching strategy (in order):
        1. Exact case-insensitive match
        2. Fuzzy token-based match (handles accented chars, nicknames, last-name only)
           - Uses 80% token overlap threshold
        """
        if not news_name:
            return None, None

        conn = get_connection(self._db_path)
        try:
            players_df = get_players_df(conn)
        finally:
            conn.close()

        news_name_normalized = self._normalize_name(news_name)

        for _, player in players_df.iterrows():
            db_name = str(player["full_name"])
            db_name_normalized = self._normalize_name(db_name)

            if news_name_normalized.lower() == db_name_normalized.lower():
                return int(player["player_id"]), db_name

            if self._fuzzy_match(news_name_normalized, db_name_normalized):
                return int(player["player_id"]), db_name

        return None, None

    def _normalize_name(self, name: str) -> str:
        """Normalize a name for comparison: lowercase, remove accents, strip whitespace."""
        normalized = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
        return ' '.join(normalized.lower().split())

    def _fuzzy_match(self, name1: str, name2: str) -> bool:
        """Check if two normalized names match with >= 80% token overlap.

        Handles:
        - Accented characters: "Jokic" matches "Nikola Jokic"
        - Nicknames: "LeBron" matches "LeBron James"
        - Last-name only: "Embiid" matches "Joel Embiid"
        """
        tokens1 = set(name1.split())
        tokens2 = set(name2.split())

        if not tokens1 or not tokens2:
            return False

        if tokens1.issubset(tokens2) or tokens2.issubset(tokens1):
            return True

        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        overlap = len(intersection) / len(union) if union else 0

        return overlap >= 0.8

    def match_player_id(self, player_id: int) -> tuple[Optional[int], Optional[str]]:
        """Direct player ID lookup.

        Returns (player_id, full_name) if found, (None, None) if not.
        """
        conn = get_connection(self._db_path)
        try:
            players_df = get_players_df(conn)
        finally:
            conn.close()

        match = players_df[players_df["player_id"] == player_id]
        if match.empty:
            return None, None

        row = match.iloc[0]
        return int(row["player_id"]), str(row["full_name"])

    def generate_alerts(self, news_items: list[dict]) -> list[dict]:
        """Generate player_alerts from news items by applying keyword matching.

        For each news item with a matched player:
        - Scan headline + raw_content for keyword matches across ALERT_CATEGORIES
        - Priority: OUT > INJURY > QUESTIONABLE > SUSPENSION > TRADE > G_LEAGUE > REST
        - For items with matched player_id from injury report: use subcategory from status
        - For RSS items: subcategory is None

        Returns list of player_alerts dicts ready for insert_player_alerts.
        """
        priority_order = ["OUT", "INJURY", "QUESTIONABLE", "SUSPENSION", "TRADE", "G_LEAGUE", "REST"]

        alerts_by_player = {}

        for item in news_items:
            player_id = item.get("player_id")
            if not player_id:
                if item.get("player_name"):
                    player_id, _ = self.match_player_name(item["player_name"])
                if not player_id:
                    continue

            text = f"{item.get('headline', '')} {item.get('raw_content', '')}".lower()

            best_type = None
            best_priority = len(priority_order)

            for alert_type in priority_order:
                config = ALERT_CATEGORIES.get(alert_type, {})
                keywords = config.get("keywords", [])
                if any(kw in text for kw in keywords):
                    if priority_order.index(alert_type) < best_priority:
                        best_type = alert_type
                        best_priority = priority_order.index(alert_type)

            if not best_type:
                best_type = "INJURY"
                best_priority = priority_order.index("INJURY")

            severity = ALERT_CATEGORIES.get(best_type, {}).get("severity", "warning")

            subcategory = None
            if item.get("source") == "nba_injury_report":
                subcategory = item.get("subcategory")

            player_key = (player_id, best_type, item.get("source", "unknown"))

            if player_key not in alerts_by_player or priority_order.index(best_type) < priority_order.index(alerts_by_player[player_key]["alert_type"]):
                alerts_by_player[player_key] = {
                    "player_id": player_id,
                    "alert_type": best_type,
                    "subcategory": subcategory,
                    "severity": severity,
                    "source": item.get("source", "unknown"),
                    "source_url": item.get("source_url"),
                    "headline": item.get("headline"),
                }

        return list(alerts_by_player.values())

    def is_cache_fresh(self) -> tuple[bool, list[str]]:
        """Check if cached news data is fresh based on NEWS_TTL_HOURS.

        Returns (is_fresh: bool, stale_sources: list[str]).
        If no news items exist, returns (True, []) — no stale sources.
        """
        conn = get_connection(self._db_path)
        try:
            cursor = conn.execute(
                """SELECT source, MAX(fetched_at) as last_fetch
                   FROM news_items
                   GROUP BY source"""
            )
            rows = cursor.fetchall()
        finally:
            conn.close()

        if not rows:
            return True, []

        now = datetime.now(timezone.utc)
        stale_sources = []

        for source, last_fetch_str in rows:
            try:
                last_fetch = datetime.fromisoformat(last_fetch_str.replace('Z', '+00:00'))
            except Exception:
                try:
                    last_fetch = datetime.fromisoformat(last_fetch_str)
                except Exception:
                    stale_sources.append(source)
                    continue

            if last_fetch.tzinfo is None:
                last_fetch = last_fetch.replace(tzinfo=timezone.utc)

            age_hours = (now - last_fetch).total_seconds() / 3600

            if age_hours > NEWS_STALE_WARNING_HOURS:
                stale_sources.append(source)
            elif age_hours > NEWS_TTL_HOURS:
                stale_sources.append(source)

        is_fresh = len(stale_sources) == 0
        return is_fresh, stale_sources

    def process_all(self) -> dict:
        """Orchestrate full news fetch → match → alert generation → storage.

        Checks cache freshness, fetches from stale sources, matches players,
        generates alerts, stores to DB, and runs cleanup.

        Returns dict: {alerts_generated: int, sources_fetched: list[str], cache_status: dict}

        All errors are caught and logged — graceful degradation never raises.
        """
        self._logger.info("Starting news processing cycle")

        is_fresh, stale_sources = self.is_cache_fresh()
        sources_fetched = []

        if not is_fresh or stale_sources:
            conn = get_connection(self._db_path)
            try:
                init_db(conn)
            finally:
                conn.close()

            if "nba_injury_report" in stale_sources or not is_fresh:
                try:
                    injury_alerts = self.fetch_injury_report()
                    if injury_alerts:
                        player_ids = [a["player_id"] for a in injury_alerts if a.get("player_id")]
                        news_items = [
                            {
                                "source": a["source"],
                                "source_url": a.get("source_url"),
                                "headline": a.get("headline", ""),
                                "raw_content": "",
                                "published_at": datetime.utcnow().isoformat(),
                                "fetched_at": datetime.utcnow().isoformat(),
                                "player_id": a.get("player_id"),
                                "player_name": a.get("player_name"),
                                "alert_keywords": a.get("alert_type"),
                            }
                            for a in injury_alerts
                        ]
                        conn = get_connection(self._db_path)
                        try:
                            insert_news_items(conn, news_items)
                            insert_player_alerts(conn, injury_alerts)
                        finally:
                            conn.close()
                        sources_fetched.append("nba_injury_report")
                        self._logger.info("Processed %d injury report alerts", len(injury_alerts))
                except Exception as e:
                    self._logger.warning("Failed to process injury report: %s", e)

            for rss_url in [ESPN_RSS_URL, NBA_RSS_URL]:
                source_key = "espn_rss" if "espn" in rss_url else "nba_rss"
                if source_key in stale_sources or (not is_fresh and source_key not in sources_fetched):
                    try:
                        rss_items = self.fetch_rss(rss_url)
                        if rss_items:
                            matched_items = []
                            alerts_to_insert = []

                            for item in rss_items:
                                player_id, player_name = self.match_player_name(item.get("headline", ""))
                                if player_id:
                                    item["player_id"] = player_id
                                    item["player_name"] = player_name
                                    matched_items.append(item)

                            if matched_items:
                                alerts = self.generate_alerts(matched_items)
                                alerts_to_insert = alerts

                            conn = get_connection(self._db_path)
                            try:
                                insert_news_items(conn, rss_items)
                                if alerts_to_insert:
                                    insert_player_alerts(conn, alerts_to_insert)
                            finally:
                                conn.close()

                            sources_fetched.append(source_key)
                            self._logger.info(
                                "Processed %d RSS items (%d matched, %d alerts) from %s",
                                len(rss_items), len(matched_items), len(alerts_to_insert), source_key
                            )
                    except Exception as e:
                        self._logger.warning("Failed to process RSS feed %s: %s", rss_url, e)

            conn = get_connection(self._db_path)
            try:
                cleanup_stale_news(conn, max_age_days=NEWS_CLEANUP_DAYS)
                cleanup_expired_alerts(conn)
            finally:
                conn.close()

        conn = get_connection(self._db_path)
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM player_alerts")
            total_alerts = cursor.fetchone()[0]
        finally:
            conn.close()

        self._logger.info(
            "News processing complete: %d alerts, fetched: %s",
            total_alerts, sources_fetched
        )

        return {
            "alerts_generated": total_alerts,
            "sources_fetched": sources_fetched,
            "cache_status": {
                "is_fresh": is_fresh,
                "stale_sources": stale_sources,
            },
        }
