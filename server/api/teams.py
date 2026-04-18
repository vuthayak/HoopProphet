"""
FastAPI router for team endpoints — per D-15.

GET /api/teams — list all teams
GET /api/teams/{team_id} — single team detail
"""

from fastapi import APIRouter, HTTPException

from server.services.team_service import get_teams, get_team_by_id

router = APIRouter(prefix="/api", tags=["teams"])


@router.get("/teams")
def list_teams():
    """List all teams with team_id, abbreviation, and full_name."""
    return get_teams()


@router.get("/teams/{team_id}")
def get_team(team_id: int):
    """Single team detail.

    Raises 404 if team not found per D-12.
    """
    try:
        return get_team_by_id(team_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Team not found")
