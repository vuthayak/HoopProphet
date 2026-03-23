import logging
import sqlite3

from tqdm import tqdm

from server.pipeline import SEASONS
from server.pipeline.nba_client import NBAClient
from server.pipeline.db import queries

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {"DEF_RATING", "OFF_RATING", "NET_RATING", "PACE"}


def collect_team_stats(
    client: NBAClient, conn: sqlite3.Connection, seasons: list[str] = None
) -> dict:
    """Fetch team advanced stats (DEF_RATING, PACE, etc.) per season.

    One API call per season returns all 30 teams.
    Uses entity_id=0 in collection_progress since stats are season-level.
    """
    if seasons is None:
        seasons = SEASONS

    completed = set()
    cursor = conn.execute(
        "SELECT season FROM collection_progress "
        "WHERE entity_type = 'team_stats' AND entity_id = 0 AND status = 'completed'"
    )
    for row in cursor.fetchall():
        completed.add(row[0])

    remaining = [s for s in seasons if s not in completed]
    skipped = len(seasons) - len(remaining)
    completed_count = 0
    failed_count = 0

    for season in tqdm(remaining, desc="Collecting team stats"):
        try:
            df = client.fetch_team_advanced_stats(season)

            missing = REQUIRED_COLUMNS - set(df.columns)
            if missing:
                logger.warning(
                    "Season %s missing columns %s. Available: %s",
                    season, missing, df.columns.tolist(),
                )
                queries.mark_progress(
                    conn, "team_stats", 0, season, "failed",
                    f"Missing columns: {missing}",
                )
                failed_count += 1
                continue

            for _, row in df.iterrows():
                queries.insert_team_stats(
                    conn,
                    int(row["TEAM_ID"]),
                    season,
                    float(row["DEF_RATING"]),
                    float(row["OFF_RATING"]),
                    float(row["NET_RATING"]),
                    float(row["PACE"]),
                )
            queries.mark_progress(conn, "team_stats", 0, season, "completed")
            completed_count += 1
        except Exception as e:
            queries.mark_progress(
                conn, "team_stats", 0, season, "failed", str(e)
            )
            logger.error("Team stats collection failed for season %s: %s", season, e)
            failed_count += 1

    return {
        "total": len(seasons),
        "completed": completed_count,
        "failed": failed_count,
        "skipped": skipped,
    }
