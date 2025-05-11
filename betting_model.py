# pip freeze > requirements.txt (to save the current environment)

# Import necessary libraries
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
# TODO: Model import goes here


# NBA API Endpoints
from nba_api.stats.endpoints import playercareerstats
from nba_api.stats.endpoints import commonplayerinfo
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.endpoints import boxscoresummaryv2

'''
Workflow:
1. [FRONTEND] Get player name 
2. [DONE] Get player ID from player name
3. Fetch career stats, gamelog, team gamelog using player ID
    Stats to fetch:
    - Career stats (averaged stats) [Need for predicting over/under prop]
    - Game log (past season games; grab prev season if <25% season completed; grab past 2 seasons games against certain team) [Need for dataset]
        - Core stats (PTS, REBOUNDS, ASSISTS, STEALS, 3PT MADE, DOUBLE-DOUBLES, TRIPLE-DOUBLES) [For dataset]
    - Box score summary (injury report) [Need for injury report]
    
4. Form dataset from all fetched endpoints
5. Preprocess the dataset
6. Train-test split (or any other splitting method)
7. Train the model + evaluate (fine tune)
8. Run predictions
9. Get LLM to summarize the predictions
'''


# List of all players in the NBA currently (will be used to autofill in search bar)
from nba_api.stats.static.players import get_players
players = pd.DataFrame(get_players())

# Function to get player ID from player name
def get_player_id(player_name):
    active_players = players[players['is_active']== True]

    # Retrieve player ID provided player name
    player_id = active_players[active_players['full_name'] == player_name]['id'].values[0]
    return player_id

test_name = 'Cade Cunningham' # TODO: Get user input from frontend (MUI autocomplete)

player_id = get_player_id(test_name) # Get player ID from player name
print(test_name, player_id) # Print player ID

# Fetching data from NBA API endpoints for dataset creation
career = playercareerstats.PlayerCareerStats(player_id=player_id, per_mode36="PerGame") # Averaged stats [Need for predicting prop]
print(career.get_data_frames()[0]) # Print career stats

# commoninfo = commonplayerinfo.CommonPlayerInfo(player_id=player_id) # Player info
# gamelog = playergamelog.PlayerGameLog(player_id=player_id) # Game log (# TODO: Verify parameters)
# boxscore = boxscoresummaryv2.BoxScoreSummaryV2(player_id=player_id) # Box score summary [Need for injury report] (TODO: Verify parameters)

# team_id = commoninfo.get_data_frames()[0]['TEAM_ID'].values[0]