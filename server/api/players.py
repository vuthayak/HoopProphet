"""
FastAPI router for player endpoints — per D-15.

GET /api/players — list all players (active only by default)
GET /api/players/{player_id} — single player with default lines
GET /api/players/{player_id}/props — top props with hit rates and ML probability
GET /api/players/{player_id}/gamelogs — recent game logs
GET /api/players/{player_id}/hitrates — hit rates for a specific stat
GET /api/players/{player_id}/lines — default lines only
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from server.services.player_service import (
    get_players,
    search_players,
    get_player_by_id,
    get_player_game_logs,
    get_player_alerts_summary,
)
from server.services.prediction_service import (
    get_player_props,
    get_default_lines,
)
from server.services.hitrate_service import get_hit_rates

router = APIRouter(prefix="/api", tags=["players"])


@router.get("/players")
def list_players(
    search: Optional[str] = None,
    active_only: bool = True,
):
    """List all players (active only by default).

    Query params:
    - search: case-insensitive partial match on full_name
    - active_only: if True (default), only return is_active players
    """
    if search:
        return search_players(query=search, active_only=active_only)
    return get_players(active_only=active_only)


@router.get("/players/{player_id}")
def get_player(player_id: int):
    """Single player detail with default lines and alert summary per D-09.

    Raises 404 if player not found per D-12.
    """
    try:
        player = get_player_by_id(player_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Player not found")

    try:
        lines = get_default_lines(player_id)
    except ValueError:
        lines = {}

    alerts_summary = get_player_alerts_summary(player_id)

    return {**player, "default_lines": lines, "alerts": alerts_summary}


@router.get("/players/{player_id}/props")
def get_props(player_id: int, request: Request):
    """Top props with ML probability and hit rates.

    Model artifact from app.state (may be None for graceful degradation per D-10).
    Returns top 5 props ranked by probability per D-05, D-06.
    """
    model_artifact = getattr(request.app.state, "model_artifact", None)

    try:
        return get_player_props(player_id, model_artifact)
    except ValueError:
        raise HTTPException(status_code=404, detail="Player not found")


@router.get("/players/{player_id}/gamelogs")
def get_gamelogs(
    player_id: int,
    limit: int = 50,
    seasons: Optional[str] = None,
):
    """Recent game logs for a player.

    Query params:
    - limit: number of games to return (default 50)
    - seasons: comma-separated season strings (e.g., "2023-24,2024-25")
    """
    season_list = None
    if seasons:
        season_list = [s.strip() for s in seasons.split(",")]

    try:
        return get_player_game_logs(player_id, seasons=season_list, limit=limit)
    except ValueError:
        raise HTTPException(status_code=404, detail="Player not found")


@router.get("/players/{player_id}/hitrates")
def get_hitrates(
    player_id: int,
    stat: str,
    seasons: Optional[str] = None,
):
    """Hit rates for a specific stat across L5/L10/L20/season windows.

    Query params:
    - stat: stat name (e.g., "pts", "reb", "ast")
    - seasons: optional comma-separated season strings
    """
    season_list = None
    if seasons:
        season_list = [s.strip() for s in seasons.split(",")]

    try:
        lines = get_default_lines(player_id, seasons=season_list)
    except ValueError:
        raise HTTPException(status_code=404, detail="Player not found")

    if stat not in lines:
        raise HTTPException(status_code=400, detail=f"No default line for stat: {stat}")

    line_value = lines[stat]

    try:
        hit_rates = get_hit_rates(player_id, stat, line_value, seasons=season_list)
    except ValueError:
        raise HTTPException(status_code=404, detail="Player not found")

    return {
        "player_id": player_id,
        "stat": stat,
        "line": line_value,
        "hit_rates": hit_rates,
    }


@router.get("/players/{player_id}/lines")
def get_lines(player_id: int):
    """Default stat lines for a player.

    Returns only stats that meet minimum volume (>1.0 avg) and
    minimum game count (>=5 games) thresholds.
    """
    try:
        lines = get_default_lines(player_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Player not found")

    return {"player_id": player_id, "lines": lines}
