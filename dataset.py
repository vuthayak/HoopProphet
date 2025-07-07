# Import necessary libraries
import pandas as pd
import numpy as np
from datetime import datetime
import time

# NBA API Endpoints
from nba_api.stats.endpoints import playercareerstats
from nba_api.stats.endpoints import commonplayerinfo
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.endpoints import boxscoresummaryv2
from nba_api.stats.endpoints import teamgamelog
from nba_api.stats.static.players import get_players


# Function to get player ID from player name
def get_player_id(player_name):
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
def get_team_games(team_id):
    curr_team_gamelog = teamgamelog.TeamGameLog(team_id=team_id, season=current_season, season_type_all_star="Regular Season").get_data_frames()[0] # Team game log
    
    # Check if team has played at least 21 games in the current season (1/4 season)
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
def get_player_gamelog(player_id, team_id):
    team_gamelog = teamgamelog.TeamGameLog(team_id=team_id, season=current_season, season_type_all_star="Regular Season").get_data_frames()[0] # Team game log
    
    if team_gamelog.count()['Game_ID'] <= 20:
        prev_gamelog = playergamelog.PlayerGameLog(player_id=player_id, season=previous_season, season_type_all_star="Regular Season").get_data_frames()[0] # Previous season game log
        curr_gamelog = playergamelog.PlayerGameLog(player_id=player_id, season=current_season, season_type_all_star="Regular Season").get_data_frames()[0] # Current season game log
        gamelog = pd.concat([curr_gamelog, prev_gamelog], ignore_index=True) # Combine current and previous season game logs

    else:
        gamelog = playergamelog.PlayerGameLog(player_id=player_id, season=current_season, season_type_all_star="Regular Season").get_data_frames()[0] # Game log

    print("Player game log retrieved")

    return gamelog

# Function to get box score summary for inactive players
def player_inactive(player_id):
    inactive_games = [] # List to store inactive games

    # Iterate through each box score summary in the gamelog to find games where the player was inactive
    for gameId in team_games['Game_ID']:
        boxscore = boxscoresummaryv2.BoxScoreSummaryV2(game_id=str(gameId)).get_data_frames()[3] # Inactive players
        time.sleep(1)

        if player_id in boxscore['PLAYER_ID'].values:
            inactive_games.append(gameId)
    
    print("Inactive games retrieved")

    return inactive_games # Return list of inactive games

# Function to grab additional rivalry matches for the player vs opponent team
def get_rivalry_games(player_id, opponent_team_abv, used_prev_season):
    # Determining the season to use based on whether previous season data was used
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
def dataset_cleaning(team_games, inactive_games):
    player_gamelog = get_player_gamelog(player_id=player_id, team_id=team_id) # Get player game log

    gamelog = pd.merge(player_gamelog, team_games, how='right', on=['Game_ID','MATCHUP', 'WL']) # Merge player gamelog with team game log

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

if __name__ == "__main__":
    # List of all players in the NBA currently (will be used to autofill in search bar)
    players = pd.DataFrame(get_players())

    # Idea: Dropdown to select player and opposing team in frontend, in order to account for rivalries 
    # (stronger/weaker performance against certain teams)
    test_name = 'Cade Cunningham' # TODO: Get user input from frontend (MUI autocomplete)
    opponent_team_abv = 'CLE' # Example opponent team ID (Cleveland Cavaliers)

    player_id = get_player_id(test_name) # Get player ID from player name

    # Fetching avg career data
    avg_career_stats = playercareerstats.PlayerCareerStats(player_id=player_id, per_mode36="PerGame").get_data_frames()[3] # Averaged career stats for regular season [Need for predicting prop]
    print("Average career stats retrieved")

    current_season, previous_season, prev_previous_season = get_season()

    commoninfo = commonplayerinfo.CommonPlayerInfo(player_id=player_id) # Player info
    team_id = commoninfo.get_data_frames()[0]['TEAM_ID'].values[0]

    team_games, used_prev_season = get_team_games(team_id) # Get team games

    inactive_games = player_inactive(player_id) # Check if player is inactive for any game in the gamelog

    rivalry_games = get_rivalry_games(player_id, opponent_team_abv, used_prev_season) # Get rivalry games

    dataset = dataset_cleaning(team_games, inactive_games) # Clean the dataset



    

