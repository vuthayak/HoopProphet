# pip freeze > requirements.txt (to save the current environment)

# Import necessary libraries
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

# Model import goes here


# NBA API Endpoints
from nba_api.stats.endpoints import playercareerstats
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.endpoints import commonplayerinfo
from nba_api.stats.endpoints import teamgamelog

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

# assume playerID provided for now (Jokic ID = 203999)
player_id = 203999

career = playercareerstats.PlayerCareerStats(player_id=player_id)
commoninfo = commonplayerinfo.CommonPlayerInfo(player_id=player_id)

team_id = commoninfo.get_data_frames()[0]['TEAM_ID'].values[0]