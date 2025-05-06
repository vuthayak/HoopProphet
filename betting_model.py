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
1. Get player name
2. Get player ID from player name
3. Fetch career stats, gamelog, team gamelog using player ID
4. Form dataset from all fetched endpoints
5. Preprocess the dataset
6. Train-test split (or any other splitting method)
7. Train the model + evaluate (fine tune)
8. Run predictions
9. Get LLM to summarize the predictions
'''

# TODO: Function to get player ID from player name

# List of all players in the NBA currently (will be used to autofill in search bar)
from nba_api.stats.static.players import get_players
players = pd.DataFrame(get_players())
full_names = players[players['is_active']== True]['full_name']

input_full_name = 'Cade Cunningham'
player_id = players[players['full_name'] == input_full_name]['id'].values[0]

# assume playerID provided for now (Jokic ID = 203999)

# career = playercareerstats.PlayerCareerStats(player_id=player_id) # Averaged stats
# commoninfo = commonplayerinfo.CommonPlayerInfo(player_id=player_id) # Player info
# gamelog = playergamelog.PlayerGameLog(player_id=player_id) # Game log (# TODO: Verify parameters)
# boxscore = boxscoresummaryv2.BoxScoreSummaryV2(player_id=player_id) # Box score summary [Need for injury report] (TODO: Verify parameters)

# team_id = commoninfo.get_data_frames()[0]['TEAM_ID'].values[0]

print('Player ID:', player_id)