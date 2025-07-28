import pandas as pd
from nba_api.stats.static.players import get_players
from nba_api.stats.endpoints import playercareerstats

# Function to get player ID from player name
def get_player_id(player_name):
    # List of all players in the NBA currently (will be used to autofill in search bar)
    players = pd.DataFrame(get_players())

    active_players = players[players['is_active']== True]

    # Retrieve player ID provided player name
    player_id = active_players[active_players['full_name'] == player_name]['id'].values[0]
    print("Player ID Retrieved")

    return player_id

def get_avg_career_stats(player_id):
    """
    Fetches the average career stats for a given player ID.
    
    Args:
        player_id (int): The ID of the player for whom to fetch career stats.
        
    Returns:
        pd.DataFrame: A DataFrame containing the player's average career stats.
    """    
    # Fetching avg career data
    avg_career_stats = playercareerstats.PlayerCareerStats(player_id=player_id, per_mode36="PerGame").get_data_frames()[3]  # Averaged career stats for regular season

    # Cleaning up the DataFrame
    avg_career_stats = avg_career_stats[['PTS','REB','AST','STL','BLK','FG3M']]
    print(avg_career_stats)

    # Write/Overwrite the average career stats to data folder
    avg_career_stats.to_csv('../data/avg_career_stats.csv', index=False)
    print("Average career stats retrieved")

    return None

if __name__ == "__main__":
    test_name = 'Cade Cunningham'
    player_id = get_player_id(test_name) # Get player ID from player name
    get_avg_career_stats(player_id) # Get average career stats for the player