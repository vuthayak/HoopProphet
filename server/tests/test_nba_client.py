import tempfile
import time
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from tenacity import RetryError

from server.pipeline.nba_client import NBAClient


def _make_client():
    """Create an NBAClient with a disposable temp cache."""
    tmp = tempfile.mkdtemp()
    return NBAClient(cache_path=f"{tmp}/test_cache")


def test_rate_limit_enforcement():
    client = _make_client()
    start = time.monotonic()
    client._enforce_rate_limit()
    client._enforce_rate_limit()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.6, f"Expected >= 0.6s between calls, got {elapsed:.3f}s"


def test_retry_on_connection_error():
    client = _make_client()

    sample_df = pd.DataFrame([{
        "SEASON_ID": "22023", "Player_ID": 203999, "Game_ID": "0022300001",
        "GAME_DATE": "OCT 25, 2023", "MATCHUP": "DEN vs. LAL", "WL": "W",
        "MIN": 35, "PTS": 29, "REB": 12, "AST": 11,
    }])

    mock_instance = MagicMock()
    mock_instance.get_data_frames.return_value = [sample_df]

    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise ConnectionError("Simulated network error")
        return mock_instance

    with patch("nba_api.stats.endpoints.playergamelog.PlayerGameLog", side_effect=side_effect):
        result = client.fetch_player_gamelog(203999, "2023-24")

    assert len(result) == 1
    assert call_count == 3


def test_cached_session_injected():
    from requests_cache import CachedSession
    client = _make_client()
    assert isinstance(client._session, CachedSession)
    assert client._session.headers["User-Agent"].startswith("Mozilla/5.0")


def test_empty_response_raises_valueerror():
    client = _make_client()
    empty_df = pd.DataFrame()
    mock_instance = MagicMock()
    mock_instance.get_data_frames.return_value = [empty_df]

    with patch("nba_api.stats.endpoints.playergamelog.PlayerGameLog", return_value=mock_instance):
        with pytest.raises((ValueError, RetryError)):
            client.fetch_player_gamelog(203999, "2023-24")


def test_static_data_no_rate_limit():
    client = _make_client()
    players = client.get_all_active_players()
    assert isinstance(players, list)
    assert len(players) > 0
    for p in players[:5]:
        assert "id" in p
        assert "full_name" in p
        assert "is_active" in p
        assert p["is_active"] is True
