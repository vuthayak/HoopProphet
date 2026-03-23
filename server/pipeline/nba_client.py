import logging
import time

import pandas as pd
from requests_cache import CachedSession
from nba_api.stats.library.http import NBAStatsHTTP
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from server.pipeline import CACHE_PATH

logger = logging.getLogger(__name__)


def setup_cached_session(cache_path: str) -> CachedSession:
    """Configure HTTP caching for all nba_api calls."""
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
    NBAStatsHTTP.set_session(session)
    return session


class NBAClient:
    """Rate-limited NBA API client with HTTP caching and retry logic."""

    MIN_DELAY = 0.6

    def __init__(self, cache_path: str = None):
        if cache_path is None:
            cache_path = CACHE_PATH
        self._last_call = 0.0
        self._session = setup_cached_session(cache_path)
        self.logger = logging.getLogger(__name__)

    def _enforce_rate_limit(self):
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
    def fetch_player_gamelog(self, player_id: int, season: str) -> pd.DataFrame:
        self._enforce_rate_limit()
        from nba_api.stats.endpoints import playergamelog
        df = playergamelog.PlayerGameLog(
            player_id=player_id,
            season=season,
            season_type_all_star="Regular Season",
            timeout=30,
        ).get_data_frames()[0]
        if df.empty:
            raise ValueError(f"Empty gamelog for player {player_id} season {season}")
        self.logger.info("Fetched %d games for player %d season %s", len(df), player_id, season)
        return df

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential_jitter(initial=0.6, max=30, jitter=2),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, ValueError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def fetch_team_roster(self, team_id: int, season: str) -> pd.DataFrame:
        self._enforce_rate_limit()
        from nba_api.stats.endpoints import commonteamroster
        df = commonteamroster.CommonTeamRoster(
            team_id=team_id,
            season=season,
            timeout=30,
        ).get_data_frames()[0]
        if df.empty:
            raise ValueError(f"Empty roster for team {team_id} season {season}")
        return df

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential_jitter(initial=0.6, max=30, jitter=2),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, ValueError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def fetch_team_schedule(self, team_id: int, season: str) -> pd.DataFrame:
        self._enforce_rate_limit()
        from nba_api.stats.endpoints import leaguegamefinder
        df = leaguegamefinder.LeagueGameFinder(
            team_id_nullable=team_id,
            season_nullable=season,
            player_or_team_abbreviation="T",
            season_type_nullable="Regular Season",
            timeout=30,
        ).get_data_frames()[0]
        if df.empty:
            raise ValueError(f"Empty schedule for team {team_id} season {season}")
        return df

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential_jitter(initial=0.6, max=30, jitter=2),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, ValueError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def fetch_team_advanced_stats(self, season: str) -> pd.DataFrame:
        self._enforce_rate_limit()
        from nba_api.stats.endpoints import leaguedashteamstats
        df = leaguedashteamstats.LeagueDashTeamStats(
            measure_type_detailed_defense="Advanced",
            season=season,
            season_type_all_star="Regular Season",
            per_mode_detailed="PerGame",
            timeout=30,
        ).get_data_frames()[0]
        if df.empty:
            raise ValueError(f"Empty team stats for season {season}")
        if "DEF_RATING" not in df.columns:
            self.logger.warning(
                "Expected DEF_RATING column not found. Available columns: %s",
                df.columns.tolist(),
            )
        return df

    def get_all_active_players(self) -> list[dict]:
        from nba_api.stats.static.players import get_players
        return [p for p in get_players() if p["is_active"]]

    def get_all_teams(self) -> list[dict]:
        from nba_api.stats.static.teams import get_teams
        return get_teams()
