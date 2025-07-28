# Model imports
import pandas as pd
from sklearn.linear_model import LinearRegression
from xgboost import XGBRegressor

# Cross-validation imports
from sklearn.model_selection import RepeatedKFold
from sklearn.model_selection import cross_val_score

# Data preprocessing imports
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

# Setting up K-Folds
rkf = RepeatedKFold(n_splits=10, n_repeats=10, random_state=101) 

# Setting up pipelines for Linear Regression and XGBoost
pipeline_lr = Pipeline([
    ('scaler', StandardScaler()),
    ('model', LinearRegression())])

pipeline_xgb = Pipeline([
    ('scaler', StandardScaler()),
    ('model', XGBRegressor(n_estimators=200, learning_rate=0.01, max_depth=3, random_state=101))])

# Function to load dataset
def load_data(file_path):
    """
    Load dataset from a CSV file.
    
    Parameters:
    file_path (str): Path to the CSV file.
    
    Returns:
    pd.DataFrame: Loaded dataset.
    """
    data = pd.read_csv(file_path)
    print(f"Data loaded from {file_path} with shape {data.shape}")
    return data

data = load_data('../data/dataset.csv')
data.set_index("Game_ID", inplace=True)

prop_line = load_data('../data/avg_career_stats.csv')

def train_models(data):
    # Create a dataframe to hold the best model metrics for each stat
    metrics = []

    print("Training models and evaluating performance...")

    for stat in ['PTS', 'REB', 'AST', 'FG3M', 'STL', 'BLK', 'TRIPLE_DOUBLE', 'DOUBLE_DOUBLE']:
        X_stat = data.drop(columns=[stat])
        y_stat = data[stat]
        
        # Linear Regression CV
        cv_results_lr = cross_val_score(pipeline_lr, X_stat, y_stat, cv=rkf, scoring='r2')
        mean_lr = cv_results_lr.mean()
        std_lr = cv_results_lr.std()
        
        # XGBoost CV
        cv_results_xgb = cross_val_score(pipeline_xgb, X_stat, y_stat, cv=rkf, scoring='r2')
        mean_xgb = cv_results_xgb.mean()
        std_xgb = cv_results_xgb.std()
        
        # Select best model
        if mean_lr > mean_xgb:
            best_model = 'Linear Regression'
            best_r2 = mean_lr
            best_std = std_lr
        else:
            best_model = 'XGBoost'
            best_r2 = mean_xgb
            best_std = std_xgb

        # If best R2 is negative, note in metrics and use mean for prediction
        if best_r2 < 0:
            metrics.append({
                'Stat': stat,
                'Model': 'Mean Prediction',
                'Mean R2': best_r2,
                'Std R2': best_std
            })
        else:
            metrics.append({
                'Stat': stat,
                'Model': best_model,
                'Mean R2': best_r2,
                'Std R2': best_std
            })

    # Convert metrics list to DataFrame
    metrics_df = pd.DataFrame(metrics)

    return metrics_df

def predict_stats(data, metrics_df):
    """
    Predict player stats using the trained models.
    
    Parameters:
    data (pd.DataFrame): DataFrame containing player game logs.
    prop_line (pd.DataFrame): DataFrame containing average career stats.
    
    Returns:
    pd.DataFrame: DataFrame with predicted stats.
    """
    # Predict each stat for the next game
    print("Predicting stats...")
    predictions = {}
    for stat in ['PTS', 'REB', 'AST', 'FG3M', 'STL', 'BLK', 'TRIPLE_DOUBLE', 'DOUBLE_DOUBLE']:
        pred_features = data.drop(columns=[stat])
        model_name = metrics_df[metrics_df['Stat'] == stat]['Model'].values[0]
        if model_name == 'Mean Prediction':
            predictions[stat] = data[stat].mean()
        elif model_name == 'Linear Regression':
            model = pipeline_lr.fit(data.drop(columns=[stat]), data[stat])
            predictions[stat] = model.predict(pred_features.tail(1))[0]
        else:
            model = pipeline_xgb.fit(data.drop(columns=[stat]), data[stat])
            predictions[stat] = model.predict(pred_features.tail(1))[0]

    return predictions

def predictions_vs_propline(predictions, prop_line):
    """
    Compare predictions with prop lines.
    Parameters:
    predictions (dict): Dictionary of predicted stats.
    prop_line (pd.DataFrame): DataFrame containing average career stats.
    Returns:
    results (dict): Dictionary with comparison results.
    """
    print("Comparing predictions with prop line...")
    prop_line = prop_line.apply(lambda x: round(x * 2) / 2)
    results = {}
    for stat in predictions:
        if stat in prop_line.columns:
            prop_val = prop_line[stat].values[0]
            pred_val = predictions[stat]
            if pred_val < prop_val:
                results[stat] = f"UNDER ({pred_val:.2f}) vs Prop Line ({prop_val})"
            else:
                results[stat] = f"OVER ({pred_val:.2f}) vs Prop Line ({prop_val})"
        elif stat in ['TRIPLE_DOUBLE', 'DOUBLE_DOUBLE']:
            pred_val = predictions[stat]
            if pred_val < 0.5:
                results[stat] = f"UNDER ({pred_val:.2f})"
            else:
                results[stat] = f"OVER ({pred_val:.2f})"
    return results

if __name__ == "__main__":
    # Load the data
    data = load_data('../data/dataset.csv')
    data.set_index("Game_ID", inplace=True)
    prop_line = load_data('../data/avg_career_stats.csv')

    # Train models and get metrics
    metrics_df = train_models(data)

    # Predict stats for player versus team
    predictions = predict_stats(data, metrics_df)

    # Compare predictions with prop lines
    results = predictions_vs_propline(predictions, prop_line)

    print("Predictions vs Prop Lines:")
    for stat, result in results.items():
        print(f"  {stat}: {result}")
