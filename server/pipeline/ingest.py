"""CLI orchestrator for the HoopProphet data collection pipeline.

Runs collectors in dependency order, synthesizes DNP rows, and validates
data completeness.  Supports full multi-season collection, incremental
current-season refresh, and validation-only mode.

Usage:
    python -m server.pipeline.ingest --full
    python -m server.pipeline.ingest --refresh
    python -m server.pipeline.ingest --validate
"""

import argparse
import datetime
import logging
import os
import sys
import time

from server.pipeline import SEASONS, DATA_DIR, DB_PATH, CACHE_PATH
from server.pipeline.db.connection import get_connection
from server.pipeline.db.schema import init_db
from server.pipeline.db import queries
from server.pipeline.nba_client import NBAClient
from server.pipeline.collectors.rosters import collect_team_rosters
from server.pipeline.collectors.schedules import collect_team_schedules
from server.pipeline.collectors.team_stats import collect_team_stats
from server.pipeline.collectors.game_logs import collect_player_gamelogs
from server.pipeline.processors.dnp_synthesis import synthesize_all_dnp_rows

logger = logging.getLogger("server.pipeline.ingest")


def validate_completeness(conn) -> bool:
    """Check row counts per table and flag any failures.

    Returns True if all minimum thresholds are met.
    """
    checks_passed = True

    counts = {
        "players": conn.execute("SELECT COUNT(*) FROM players").fetchone()[0],
        "teams": conn.execute("SELECT COUNT(*) FROM teams").fetchone()[0],
        "game_logs_real": conn.execute(
            "SELECT COUNT(*) FROM player_game_logs WHERE is_dnp = 0"
        ).fetchone()[0],
        "game_logs_dnp": conn.execute(
            "SELECT COUNT(*) FROM player_game_logs WHERE is_dnp = 1"
        ).fetchone()[0],
        "team_stats": conn.execute("SELECT COUNT(*) FROM team_stats").fetchone()[0],
        "roster_entries": conn.execute("SELECT COUNT(*) FROM team_rosters").fetchone()[0],
        "schedule_entries": conn.execute("SELECT COUNT(*) FROM team_schedules").fetchone()[0],
    }

    logger.info("=== Data Completeness Report ===")
    for label, cnt in counts.items():
        logger.info("  %-20s %d", label, cnt)

    season_cursor = conn.execute(
        "SELECT season, COUNT(*) FROM player_game_logs GROUP BY season ORDER BY season"
    )
    logger.info("  Per-season game logs:")
    for season, cnt in season_cursor.fetchall():
        logger.info("    %-10s %d", season, cnt)

    progress_cursor = conn.execute(
        "SELECT status, COUNT(*) FROM collection_progress GROUP BY status"
    )
    logger.info("  Collection progress:")
    for status, cnt in progress_cursor.fetchall():
        logger.info("    %-12s %d", status, cnt)

    failed_cursor = conn.execute(
        "SELECT entity_type, entity_id, season, error_message "
        "FROM collection_progress WHERE status = 'failed' LIMIT 20"
    )
    failed_rows = failed_cursor.fetchall()
    if failed_rows:
        logger.warning("  Failed collection entries (%d shown):", len(failed_rows))
        for etype, eid, season, err in failed_rows:
            logger.warning("    %s/%s/%s: %s", etype, eid, season, err)

    thresholds = [
        ("teams", counts["teams"], 30),
        ("players", counts["players"], 400),
        ("team_stats", counts["team_stats"], 100),
        ("game_logs_real", counts["game_logs_real"], 50000),
    ]
    for label, actual, minimum in thresholds:
        if actual < minimum:
            logger.warning("VALIDATION FAIL: %s = %d (expected >= %d)", label, actual, minimum)
            checks_passed = False
        else:
            logger.info("VALIDATION PASS: %s = %d (>= %d)", label, actual, minimum)

    return checks_passed


def _get_current_season() -> str:
    """Return the NBA season string for the current date."""
    now = datetime.date.today()
    if now.month >= 10:
        return f"{now.year}-{str(now.year + 1)[-2:]}"
    return f"{now.year - 1}-{str(now.year)[-2:]}"


def _run_collection(client: NBAClient, conn, seasons: list[str]):
    """Execute the collection pipeline in dependency order."""
    logger.info("Seeding teams...")
    teams = client.get_all_teams()
    for t in teams:
        queries.upsert_team(conn, t["id"], t["abbreviation"], t["full_name"])
    conn.commit()
    logger.info("Seeded %d teams", len(teams))

    logger.info("Seeding active players...")
    players = client.get_all_active_players()
    for p in players:
        queries.upsert_player(conn, p["id"], p["full_name"], True)
    conn.commit()
    logger.info("Seeded %d active players", len(players))

    logger.info("Collecting team rosters...")
    result = collect_team_rosters(client, conn, seasons)
    logger.info("Rosters: %s", result)

    logger.info("Collecting team schedules...")
    result = collect_team_schedules(client, conn, seasons)
    logger.info("Schedules: %s", result)

    logger.info("Collecting team advanced stats...")
    result = collect_team_stats(client, conn, seasons)
    logger.info("Team stats: %s", result)

    logger.info("Collecting player game logs...")
    result = collect_player_gamelogs(client, conn, seasons)
    logger.info("Game logs: %s", result)

    logger.info("Synthesizing DNP rows...")
    result = synthesize_all_dnp_rows(conn, seasons)
    logger.info("DNP synthesis complete: %d rows", result["total_dnp_rows"])


def main():
    parser = argparse.ArgumentParser(
        description="HoopProphet NBA data collection pipeline"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--full", action="store_true",
        help="Run full 5-season collection (default)",
    )
    mode.add_argument(
        "--refresh", action="store_true",
        help="Only fetch current season delta",
    )
    mode.add_argument(
        "--validate", action="store_true",
        help="Run completeness checks only, no collection",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable DEBUG logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        level=logging.DEBUG if args.verbose else logging.INFO,
    )

    os.makedirs(DATA_DIR, exist_ok=True)

    conn = get_connection(DB_PATH)
    init_db(conn)

    try:
        if args.validate:
            valid = validate_completeness(conn)
            conn.close()
            sys.exit(0 if valid else 1)

        if args.refresh:
            current_season = _get_current_season()
            logger.info("Refreshing data for current season: %s", current_season)
            seasons = [current_season]
        else:
            logger.info("Starting full data collection for seasons: %s", SEASONS)
            seasons = SEASONS

        start_time = time.time()
        client = NBAClient(cache_path=CACHE_PATH)

        _run_collection(client, conn, seasons)

        valid = validate_completeness(conn)

        elapsed = time.time() - start_time
        logger.info("Collection completed in %.1f minutes", elapsed / 60)
        conn.close()
        sys.exit(0 if valid else 1)

    except KeyboardInterrupt:
        logger.info("Collection interrupted. Progress saved — re-run to resume.")
        conn.close()
        sys.exit(130)
    except Exception:
        logger.exception("Fatal error during collection")
        conn.close()
        sys.exit(1)


if __name__ == "__main__":
    main()
