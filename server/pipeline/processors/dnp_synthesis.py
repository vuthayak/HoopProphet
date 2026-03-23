import logging
import sqlite3

import pandas as pd

from server.pipeline import SEASONS

logger = logging.getLogger(__name__)


def _get_player_team_tenure(
    conn: sqlite3.Connection, player_id: int, season: str
) -> dict[int, tuple[str, str]]:
    """Determine date ranges a player was on each team from game log matchups.

    Returns dict mapping team_id → (start_date, end_date) for this player in
    this season.  Handles mid-season trades by parsing the team abbreviation
    from the MATCHUP column (format "TEA vs. OPP" or "TEA @ OPP").

    For single-team players the end date extends to the team's last scheduled
    game so that late-season DNPs are captured.  For traded players, each
    team's window is bounded by the actual game log dates to avoid creating
    false DNP rows on the old team.
    """
    cursor = conn.execute(
        "SELECT game_date, matchup FROM player_game_logs "
        "WHERE player_id = ? AND season = ? AND is_dnp = 0 "
        "ORDER BY game_date",
        (player_id, season),
    )
    rows = cursor.fetchall()
    if not rows:
        return {}

    team_dates: dict[str, list[str]] = {}
    for game_date, matchup in rows:
        abbr = matchup.split(" ")[0] if matchup else None
        if not abbr:
            continue
        team_dates.setdefault(abbr, []).append(game_date)

    abbr_cursor = conn.execute(
        "SELECT team_id, abbreviation FROM teams"
    )
    abbr_to_id = {row[1]: row[0] for row in abbr_cursor.fetchall()}

    played_for_multiple_teams = len(team_dates) > 1

    tenure: dict[int, tuple[str, str]] = {}
    for abbr, dates in team_dates.items():
        tid = abbr_to_id.get(abbr)
        if tid is None:
            continue

        start_date = min(dates)

        if played_for_multiple_teams:
            end_date = max(dates)
        else:
            sched_max = conn.execute(
                "SELECT MAX(game_date) FROM team_schedules "
                "WHERE team_id = ? AND season = ?",
                (tid, season),
            ).fetchone()
            end_date = sched_max[0] if sched_max and sched_max[0] else max(dates)

        tenure[tid] = (start_date, end_date)
    return tenure


def synthesize_dnp_rows(conn: sqlite3.Connection, season: str) -> int:
    """Find roster × schedule gaps and insert zero-minute DNP rows.

    For each rostered player, determines the date range they were on each team
    (from actual game log matchups), then finds team schedule games within that
    range where the player has no game log entry.  Those gaps become DNP rows.
    """
    roster_cursor = conn.execute(
        "SELECT DISTINCT player_id, team_id FROM team_rosters WHERE season = ?",
        (season,),
    )
    roster_pairs = roster_cursor.fetchall()

    dnp_rows = []

    for player_id, team_id in roster_pairs:
        tenure = _get_player_team_tenure(conn, player_id, season)
        if team_id not in tenure:
            continue
        start_date, end_date = tenure[team_id]

        schedule_cursor = conn.execute(
            "SELECT game_id, game_date, matchup FROM team_schedules "
            "WHERE team_id = ? AND season = ? "
            "AND game_date >= ? AND game_date <= ?",
            (team_id, season, start_date, end_date),
        )
        scheduled_games = schedule_cursor.fetchall()

        for game_id, game_date, matchup in scheduled_games:
            exists = conn.execute(
                "SELECT 1 FROM player_game_logs "
                "WHERE player_id = ? AND game_id = ?",
                (player_id, game_id),
            ).fetchone()
            if exists:
                continue

            dnp_rows.append({
                "player_id": player_id,
                "game_id": game_id,
                "season": season,
                "game_date": game_date,
                "matchup": matchup,
                "wl": None,
                "min": 0, "pts": 0, "reb": 0, "ast": 0,
                "stl": 0, "blk": 0, "fg3m": 0, "fgm": 0, "fga": 0,
                "ftm": 0, "fta": 0, "oreb": 0, "dreb": 0,
                "tov": 0, "pf": 0, "plus_minus": 0,
                "is_dnp": 1,
            })

    if dnp_rows:
        cols = [
            "player_id", "game_id", "season", "game_date", "matchup", "wl",
            "min", "pts", "reb", "ast", "stl", "blk", "fg3m",
            "fgm", "fga", "ftm", "fta", "oreb", "dreb", "tov", "pf",
            "plus_minus", "is_dnp",
        ]
        placeholders = ", ".join(["?"] * len(cols))
        sql = (
            f"INSERT OR IGNORE INTO player_game_logs ({', '.join(cols)}) "
            f"VALUES ({placeholders})"
        )
        conn.executemany(
            sql,
            [tuple(row[c] for c in cols) for row in dnp_rows],
        )
        conn.commit()

    logger.info("Synthesized %d DNP rows for season %s", len(dnp_rows), season)
    return len(dnp_rows)


def synthesize_all_dnp_rows(
    conn: sqlite3.Connection, seasons: list[str] = None
) -> dict:
    """Run DNP synthesis across all specified seasons."""
    if seasons is None:
        seasons = SEASONS

    total = 0
    per_season: dict[str, int] = {}
    for season in seasons:
        count = synthesize_dnp_rows(conn, season)
        per_season[season] = count
        total += count

    return {"total_dnp_rows": total, "per_season": per_season}
