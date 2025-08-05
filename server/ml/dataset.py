# Import necessary libraries
import pandas as pd
import numpy as np
from datetime import datetime
import time

# NBA API Endpoints
from nba_api.stats.endpoints import commonplayerinfo
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.endpoints import boxscoresummaryv2
from nba_api.stats.endpoints import teamgamelog
from nba_api.stats.static.players import get_players


# Function to get player ID from player name
def get_player_id(player_name):
    # List of all players in the NBA currently (will be used to autofill in search bar)
    players = pd.DataFrame(get_players())

    active_players = players[players['is_active']== True]

    # Retrieve player ID provided player name
    player_id = active_players[active_players['full_name'] == player_name]['id'].values[0]
    print("Player Name Retrieved")

    return player_id

# Function to get current and previous NBA season based on the current date
def get_season():
    today = datetime.today()
    year = today.year
    month = today.month

    if month >= 10:  # October to December: new season starts
        start_year = year
    else:  # January to September: still part of the previous season
        start_year = year - 1

    current_season = f"{start_year}-{str(start_year + 1)[-2:]}"
    previous_season = f"{start_year - 1}-{str(start_year)[-2:]}"
    prev_previous_season = f"{start_year - 2}-{str(start_year - 1)[-2:]}"

    print("Seasons Retrieved")
    
    return current_season, previous_season, prev_previous_season

# Function to get team game logs
def get_team_games(team_id, current_season, previous_season):
    curr_team_gamelog = teamgamelog.TeamGameLog(team_id=team_id, season=current_season, season_type_all_star="Regular Season").get_data_frames()[0]
    if curr_team_gamelog.count()['Game_ID'] <= 20:
        print("Not enough games played in current season, using previous season data as well")
        prev_team_gamelog = teamgamelog.TeamGameLog(team_id=team_id, season=previous_season, season_type_all_star="Regular Season").get_data_frames()[0]
        team_gamelog = pd.concat([curr_team_gamelog, prev_team_gamelog], ignore_index=True) # Combine current and previous season game logs
        used_prev_season = True # Flag to indicate previous season data is used
    
    else:
        print("Enough games played in current season, using only current season data")
        team_gamelog = curr_team_gamelog
        used_prev_season = False # Flag to indicate previous season data is not used
    
    return team_gamelog[['Game_ID', "MATCHUP", "WL"]], used_prev_season # DataFrame of non-player stats for each game

# Function to get player game logs
def get_player_gamelog(player_id, current_season, previous_season, used_prev_season):
    curr_gamelog = playergamelog.PlayerGameLog(player_id=player_id, season=current_season, season_type_all_star="Regular Season").get_data_frames()[0]
    if used_prev_season:
        prev_gamelog = playergamelog.PlayerGameLog(player_id=player_id, season=previous_season, season_type_all_star="Regular Season").get_data_frames()[0]
        gamelog = pd.concat([curr_gamelog, prev_gamelog], ignore_index=True)
    else:
        gamelog = curr_gamelog
    print("Player game log retrieved")
    return gamelog

# Function to get box score summary for inactive players
def player_inactive(player_id, game_ids):
    inactive_games = []
    for gameId in game_ids:
        try:
            boxscore = boxscoresummaryv2.BoxScoreSummaryV2(game_id=str(gameId)).get_data_frames()[3]
            time.sleep(1)
            if player_id in boxscore['PLAYER_ID'].values:
                inactive_games.append(gameId)
        except Exception as e:
            print(f"Error processing game {gameId}: {e}")
            continue
    print("Inactive games retrieved")

    return inactive_games # Return list of inactive games

# Function to grab additional rivalry matches for the player vs opponent team
def get_rivalry_games(player_id, opponent_team_abv, used_prev_season, previous_season, prev_previous_season):
    if used_prev_season:
        search_season = prev_previous_season
    else:
        search_season = previous_season
    search_gamelog = playergamelog.PlayerGameLog(player_id=player_id, season=search_season, season_type_all_star="Regular Season").get_data_frames()[0]

    return search_gamelog[search_gamelog['MATCHUP'].str.contains(str(opponent_team_abv))] # Filter games against the opponent team

# Functions to classify triple-doubles and double-doubles
def triple_double(row):
    count = sum([row['PTS'] >= 10, 
                 row['REB'] >= 10, 
                 row['AST'] >= 10, 
                 row['STL'] >= 10, 
                 row['BLK'] >= 10])

    return 1 if count >= 3 else 0

def double_double(row):
    count = sum([row['PTS'] >= 10, 
                 row['REB'] >= 10, 
                 row['AST'] >= 10, 
                 row['STL'] >= 10, 
                 row['BLK'] >= 10])

    return 1 if count >= 2 else 0

# Function to clean and arrange dataset with all pieces together
def dataset_cleaning(player_gamelog, team_games, inactive_games, rivalry_games):
    # If team_games is empty, skip the merge and use player_gamelog as base
    if team_games is not None and not team_games.empty:
        gamelog = pd.merge(player_gamelog, team_games, how='right', on=['Game_ID','MATCHUP', 'WL'])
    else:
        print("Warning: team_games is empty, using player_gamelog only.")
        gamelog = player_gamelog.copy()

    gamelog = pd.concat([gamelog, rivalry_games], ignore_index=True) # Combine current and previous season game logs
    gamelog.set_index('Game_ID', inplace=True) # Set Game_ID as index

    # Drop unnecessary columns
    gamelog = gamelog[['PTS','REB','AST','STL','BLK','FG3M','WL']]

    # Adding columns for triple doubles and double doubles
    gamelog['TRIPLE_DOUBLE'] = gamelog.apply(triple_double, axis=1)
    gamelog['DOUBLE_DOUBLE'] = gamelog.apply(double_double, axis=1)

    # Encode WL as 1 and 0
    gamelog['W'] = gamelog['WL'].map({'W': 1, 'L': 0})
    gamelog.drop(columns=['WL'], inplace=True) # Drop the original WL column

    # 0 if player played, 1 if inactive
    gamelog['PLAYER_INACTIVE'] = gamelog.index.isin(inactive_games).astype(int) 

    # If player did not score any points and is not inactive, then they did not dress
    gamelog['PLAYER_DND'] = gamelog.apply(
        lambda row: 1 if pd.isna(row['PTS']) and row['PLAYER_INACTIVE'] == 0 else 0,
        axis=1)

    # Adding rolling counts for total unplayed, did-not-dress, and inactive games in last 10 games
    gamelog['INACTIVE_ROLLING'] = gamelog['PLAYER_INACTIVE'].rolling(window=10, min_periods=1).sum()
    gamelog['DND_ROLLING'] = gamelog['PLAYER_DND'].rolling(window=10, min_periods=1).sum()
    gamelog['GAMES_MISSED_ROLLING'] = gamelog['INACTIVE_ROLLING'] + gamelog['DND_ROLLING']

    # Fill Nans with 0
    gamelog.fillna(0, inplace=True) # Fill NaNs with 0

    # Type formatting
    gamelog = gamelog.astype(int)
    print("Dataset cleaned and arranged")
    return gamelog

def build_dataset(player_name, opponent_team_abv):
    """
    Build a cleaned dataset for a given player and opponent team abbreviation.
    Returns the processed DataFrame.
    """
    player_id = get_player_id(player_name)
    current_season, previous_season, prev_previous_season = get_season()
    commoninfo = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
    team_id = commoninfo.get_data_frames()[0]['TEAM_ID'].values[0]
    team_games, used_prev_season = get_team_games(team_id, current_season, previous_season)
    player_gamelog = get_player_gamelog(player_id, current_season, previous_season, used_prev_season)
    inactive_games = player_inactive(player_id, game_ids=team_games['Game_ID'])
    rivalry_games = get_rivalry_games(player_id, opponent_team_abv, used_prev_season, previous_season, prev_previous_season)
    dataset = dataset_cleaning(player_gamelog, team_games, inactive_games, rivalry_games)
    return dataset

if __name__ == "__main__":
    test_name = 'Cade Cunningham'
    opponent_team_abv = 'CLE'
    dataset = build_dataset(test_name, opponent_team_abv)
    print(dataset.head(), len(dataset))

