import logging
import sqlite3

from tqdm import tqdm

from server.pipeline import SEASONS
from server.pipeline.nba_client import NBAClient
from server.pipeline.db import queries

logger = logging.getLogger(__name__)


def collect_team_schedules(
    client: NBAClient, conn: sqlite3.Connection, seasons: list[str] = None
) -> dict:
    """Fetch team schedules for all teams across specified seasons.

    Reads team list from the already-seeded teams table,
    tracks progress per (team_id, season) for resumability.
    """
    if seasons is None:
        seasons = SEASONS

    cursor = conn.execute("SELECT team_id, abbreviation FROM teams")
    teams = cursor.fetchall()
    if not teams:
        raise RuntimeError(
            "Teams table is empty — run roster collection first to seed teams"
        )

    completed = set()
    prog_cursor = conn.execute(
        "SELECT entity_id, season FROM collection_progress "
        "WHERE entity_type = 'team_schedule' AND status = 'completed'"
    )
    for row in prog_cursor.fetchall():
        completed.add((row[0], row[1]))

    work = [
        (tid, season)
        for tid, _ in teams
        for season in seasons
        if (tid, season) not in completed
    ]

    skipped = len(teams) * len(seasons) - len(work)
    completed_count = 0
    failed_count = 0

    for team_id, season in tqdm(work, desc="Collecting schedules"):
        try:
            df = client.fetch_team_schedule(team_id, season)
            for _, row in df.iterrows():
                queries.insert_team_schedule(
                    conn, team_id, row["GAME_ID"], season,
                    row["GAME_DATE"], row["MATCHUP"], row["WL"],
                )
            queries.mark_progress(conn, "team_schedule", team_id, season, "completed")
            completed_count += 1
        except Exception as e:
            queries.mark_progress(
                conn, "team_schedule", team_id, season, "failed", str(e)
            )
            logger.error(
                "Schedule collection failed for team %d season %s: %s",
                team_id, season, e,
            )
            failed_count += 1

    return {
        "total": len(teams) * len(seasons),
        "completed": completed_count,
        "failed": failed_count,
        "skipped": skipped,
    }
