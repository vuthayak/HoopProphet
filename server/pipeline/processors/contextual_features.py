import logging

import pandas as pd

logger = logging.getLogger(__name__)


def _extract_opponent(matchup: str) -> str | None:
    if not isinstance(matchup, str):
        return None
    if " vs. " in matchup:
        return matchup.split(" vs. ", 1)[1].strip()
    if " @ " in matchup:
        return matchup.split(" @ ", 1)[1].strip()
    return None


def compute_contextual_features(
    df: pd.DataFrame,
    team_stats_df: pd.DataFrame,
    teams_df: pd.DataFrame,
    players_df: pd.DataFrame,
) -> pd.DataFrame:
    """Compute schedule, venue, and team-context features for each played game row."""
    logger.info("Computing contextual features for %d rows", len(df))

    out = df.sort_values(["player_id", "game_date"]).copy()

    out["game_date_dt"] = pd.to_datetime(out["game_date"])
    out["rest_days"] = (
        out.groupby("player_id")["game_date_dt"].diff().dt.days.fillna(7).clip(upper=14)
    )
    out["is_b2b"] = (out["rest_days"] == 1).astype(int)

    out["is_home"] = out["matchup"].str.contains(" vs. ", regex=False).astype(int)

    out["opp_abbr"] = out["matchup"].apply(_extract_opponent)
    abbr_to_id = dict(zip(teams_df["abbreviation"], teams_df["team_id"]))
    out["opp_team_id"] = out["opp_abbr"].map(abbr_to_id)

    out["player_team_abbr"] = (
        out["matchup"].str.split(r" vs\. | @ ", regex=True).str[0].str.strip()
    )
    out["player_team_id"] = out["player_team_abbr"].map(abbr_to_id)

    opp_stats = team_stats_df[["team_id", "season", "def_rating", "pace"]].rename(
        columns={"team_id": "opp_team_id", "def_rating": "opp_def_rating", "pace": "opp_pace"}
    )
    out = out.merge(opp_stats, on=["opp_team_id", "season"], how="left")

    team_pace = team_stats_df[["team_id", "season", "pace"]].rename(
        columns={"team_id": "player_team_id", "pace": "team_pace"}
    )
    out = out.merge(team_pace, on=["player_team_id", "season"], how="left")

    position_map = players_df[["player_id", "position"]]
    out = out.merge(position_map, on="player_id", how="left")

    out.drop(columns=["game_date_dt", "player_team_abbr"], inplace=True)

    logger.info(
        "Completed contextual feature computation: columns added=%d",
        len(
            [
                "rest_days",
                "is_b2b",
                "is_home",
                "opp_abbr",
                "opp_team_id",
                "player_team_id",
                "opp_def_rating",
                "opp_pace",
                "team_pace",
                "position",
            ]
        ),
    )
    return out
