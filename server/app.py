from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
from typing import List, Dict, Optional

# Import your ML modules
from ml.prop_line import get_player_id, get_prop_line
from ml.dataset import build_dataset
from ml.model_train import train_models, predict_stats, predictions_vs_propline, generate_model_summary
from nba_api.stats.static.players import get_players
from nba_api.stats.static.teams import get_teams

app = FastAPI(title="HoopProphet API", description="NBA Player Analytics & Predictions")

# Add CORS middleware to allow React app to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000",
                   "https://hoopprophet.vercel.app",
                   "https://*.vercel.app",
                   "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response
class PlayerRequest(BaseModel):
    player_name: str
    opponent_team: Optional[str] = None

class PlayerResponse(BaseModel):
    player_id: int
    full_name: str
    is_active: bool

class PredictionRequest(BaseModel):
    player_name: str
    opponent_team_abv: str

class PredictionResponse(BaseModel):
    player_name: str
    opponent_team_abv: str
    predictions: Dict[str, float]
    vs_prop_line: Dict[str, str]
    ml_metrics: Dict[str, str]
    model_summary: str

class PropLineResponse(BaseModel):
    player_name: str
    prop_lines: Dict[str, float]

class TeamResponse(BaseModel):
    team_id: int
    full_name: str
    abbreviation: str
    nickname: str
    city: str
    state: str

@app.get("/")
def read_root():
    return {"message": "HoopProphet API is running!", "version": "1.0.0"}

@app.get("/players", response_model=List[dict])
def get_active_players():
    """
    Get all active NBA players for the autocomplete dropdown.
    Returns a list of player names.
    """
    try:
        # Get all players from NBA API
        players = pd.DataFrame(get_players())
        
        # Filter for active players only
        active_players = players[players['is_active'] == True]
        
        # Return just the full names and Ids as a list, sorted alphabetically
        players_list = active_players[['full_name', 'id']].sort_values('full_name').to_dict(orient='records')

        return players_list

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching players: {str(e)}")

@app.get("/teams", response_model=List[dict])
def get_nba_teams():
    """
    Get all NBA teams for the autocomplete dropdown.
    Returns a list of team names (full names).
    """
    try:
        # Get all teams from NBA API
        teams = pd.DataFrame(get_teams())
        
        # Return just the full names as a list, sorted alphabetically
        teams_list = teams[['full_name', 'id', 'abbreviation']].sort_values('full_name').to_dict(orient='records')

        return teams_list

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching teams: {str(e)}")

@app.get("/team/{team_name}", response_model=TeamResponse)
def get_team_info(team_name: str):
    """
    Get team info by team name.
    """
    try:
        teams = pd.DataFrame(get_teams())
        
        # Find the team
        team_data = teams[teams['full_name'] == team_name]
        
        if team_data.empty:
            raise HTTPException(status_code=404, detail="Team not found")
        
        team_info = team_data.iloc[0]
        return TeamResponse(
            team_id=int(team_info['id']),
            full_name=team_info['full_name'],
            abbreviation=team_info['abbreviation'],
            nickname=team_info['nickname'],
            city=team_info['city'],
            state=team_info['state']
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching team info: {str(e)}")

@app.get("/player/{player_name}", response_model=PlayerResponse)
def get_player_info(player_name: str):
    """
    Get player ID and basic info by player name.
    """
    try:
        players = pd.DataFrame(get_players())
        active_players = players[players['is_active'] == True]
        
        # Find the player
        player_data = active_players[active_players['full_name'] == player_name]
        
        if player_data.empty:
            raise HTTPException(status_code=404, detail="Player not found")
        
        player_info = player_data.iloc[0]
        return PlayerResponse(
            player_id=int(player_info['id']),
            full_name=player_info['full_name'],
            is_active=bool(player_info['is_active'])
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching player info: {str(e)}")

@app.post("/prop-line", response_model=PropLineResponse)
def get_player_prop_line(request: PlayerRequest):
    """
    Get prop lines (average career stats) for a player.
    """
    try:
        # Get player ID
        player_id = get_player_id(request.player_name)
        
        # Get prop line
        prop_line = get_prop_line(player_id)
        
        # Convert to dictionary
        prop_lines_dict = prop_line.iloc[0].to_dict()
        
        return PropLineResponse(
            player_name=request.player_name,
            prop_lines=prop_lines_dict
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting prop line: {str(e)}")

@app.post("/predict", response_model=PredictionResponse)
def predict_player_stats(request: PredictionRequest):
    """
    Predict player stats using machine learning models.
    This endpoint replicates the logic from model_train.py __main__ block.
    """
    try:
        # Get player ID
        player_id = get_player_id(request.player_name)
        
        # Build the dataset (equivalent to the __main__ logic)
        data = build_dataset(request.player_name, request.opponent_team_abv)
        
        # Get prop line
        prop_line = get_prop_line(player_id)
        
        # Train models and get metrics
        metrics_df = train_models(data)
        
        # Predict stats for player versus team
        predictions = predict_stats(data, metrics_df)
        
        # Compare predictions with prop lines
        results = predictions_vs_propline(predictions, prop_line)
        
        # Convert metrics to a simple dict for response
        ml_metrics = {}
        for _, row in metrics_df.iterrows():
            ml_metrics[row['Stat']] = f"{row['Model']} (R2: {row['Mean R2']:.3f})"
        
        # Generate AI summary of model performance
        model_summary = generate_model_summary(metrics_df)
        
        return PredictionResponse(
            player_name=request.player_name,
            opponent_team_abv=request.opponent_team_abv,  # Fixed: was opponent_team
            predictions=predictions,
            vs_prop_line=results,
            ml_metrics=ml_metrics,
            model_summary=model_summary
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error making prediction: {str(e)}")

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "HoopProphet API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)