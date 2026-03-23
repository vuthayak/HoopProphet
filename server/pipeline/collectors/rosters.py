import logging
import sqlite3

from tqdm import tqdm

from server.pipeline import SEASONS
from server.pipeline.nba_client import NBAClient
from server.pipeline.db import queries

logger = logging.getLogger(__name__)


def collect_team_rosters(
    client: NBAClient, conn: sqlite3.Connection, seasons: list[str] = None
) -> dict:
    """Fetch team rosters for all 30 teams across specified seasons.

    Seeds the teams and players tables, inserts roster associations,
    and tracks progress per (team_id, season) for resumability.
    """
    if seasons is None:
        seasons = SEASONS

    teams = client.get_all_teams()
    for team in teams:
        queries.upsert_team(conn, team["id"], team["abbreviation"], team["full_name"])

    completed = set()
    cursor = conn.execute(
        "SELECT entity_id, season FROM collection_progress "
        "WHERE entity_type = 'team_roster' AND status = 'completed'"
    )
    for row in cursor.fetchall():
        completed.add((row[0], row[1]))

    work = [
        (team["id"], season)
        for team in teams
        for season in seasons
        if (team["id"], season) not in completed
    ]

    skipped = len(teams) * len(seasons) - len(work)
    completed_count = 0
    failed_count = 0

    for team_id, season in tqdm(work, desc="Collecting rosters"):
        try:
            df = client.fetch_team_roster(team_id, season)
            for _, row in df.iterrows():
                pid = int(row["PLAYER_ID"])
                queries.upsert_player(
                    conn, pid, row["PLAYER"], True,
                    row.get("POSITION"), team_id,
                )
                queries.insert_team_roster(conn, team_id, pid, season)
            queries.mark_progress(conn, "team_roster", team_id, season, "completed")
            completed_count += 1
        except Exception as e:
            queries.mark_progress(
                conn, "team_roster", team_id, season, "failed", str(e)
            )
            logger.error("Roster collection failed for team %d season %s: %s", team_id, season, e)
            failed_count += 1

    return {
        "total": len(teams) * len(seasons),
        "completed": completed_count,
        "failed": failed_count,
        "skipped": skipped,
    }
