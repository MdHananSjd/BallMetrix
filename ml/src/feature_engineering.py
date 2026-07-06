import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_synthetic_historical_data():
    """Generates synthetic historical matches for training the predictor."""
    os.makedirs("ml/data/raw", exist_ok=True)
    csv_path = "ml/data/raw/historical_matches.csv"
    
    if os.path.exists(csv_path):
        return
        
    print("Generating synthetic historical matches...")
    # Seeded teams
    teams = [
        (1, "Argentina"), (2, "France"), (3, "Brazil"), (4, "England"),
        (5, "Spain"), (6, "Germany"), (7, "Portugal"), (8, "Netherlands"),
        (9, "USA"), (10, "Mexico"), (11, "Canada"), (12, "Croatia"),
        (13, "Morocco"), (14, "Japan"), (15, "Senegal"), (16, "Italy")
    ]
    
    # Generate ~500 matches over the last 4 years
    np.random.seed(42)
    start_date = datetime(2022, 6, 1)
    
    data = []
    for i in range(500):
        # Pick two random teams
        home_idx = np.random.choice(len(teams))
        away_idx = np.random.choice(len(teams))
        while away_idx == home_idx:
            away_idx = np.random.choice(len(teams))
            
        home_id, home_name = teams[home_idx]
        away_id, away_name = teams[away_idx]
        
        # Determine match date
        match_date = start_date + timedelta(days=np.random.randint(0, 1400))
        
        # Elo influence on goals (higher ID has slight skew for synthetic variability)
        home_strength = 1.5 + (16 - home_id) * 0.05
        away_strength = 1.3 + (16 - away_id) * 0.05
        
        home_score = np.random.poisson(home_strength)
        away_score = np.random.poisson(away_strength)
        
        data.append({
            "match_id": i + 1,
            "competition_id": "WC2026",
            "season": 2022 + (match_date.year - 2022),
            "home_team_id": home_id,
            "away_team_id": away_id,
            "match_date": match_date.strftime("%Y-%m-%d %H:%M:%S"),
            "home_score": home_score,
            "away_score": away_score
        })
        
    df = pd.DataFrame(data)
    df = df.sort_values(by="match_date").reset_index(drop=True)
    df.to_csv(csv_path, index=False)
    print(f"Saved {len(df)} historical matches to {csv_path}")

def calculate_elo_and_features():
    generate_synthetic_historical_data()
    
    df = pd.read_csv("ml/data/raw/historical_matches.csv")
    df["match_date"] = pd.to_datetime(df["match_date"])
    df = df.sort_values(by="match_date").reset_index(drop=True)
    
    # Initialize Elos
    elos = {team_id: 1500.0 for team_id in set(df["home_team_id"]).union(set(df["away_team_id"]))}
    
    # Tracking rolling form (last 5 games results: win=3, draw=1, loss=0)
    team_history = {team_id: [] for team_id in elos}
    
    # Tracking head-to-head outcomes
    h2h = {} # Key: (team_a, team_b), Value: list of outcomes (from team_a perspective: 1=win, 0.5=draw, 0=loss)
    
    K = 32
    rows = []
    
    for idx, row in df.iterrows():
        h_id = row["home_team_id"]
        a_id = row["away_team_id"]
        h_score = row["home_score"]
        a_score = row["away_score"]
        
        h_elo = elos[h_id]
        a_elo = elos[a_id]
        
        # Calculate expected scores
        expected_h = 1 / (1 + 10 ** ((a_elo - h_elo) / 400))
        expected_a = 1 / (1 + 10 ** ((h_elo - a_elo) / 400))
        
        # Actual outcome (home perspective)
        if h_score > a_score:
            actual_h, actual_a = 1.0, 0.0
            points_h, points_a = 3, 0
        elif h_score < a_score:
            actual_h, actual_a = 0.0, 1.0
            points_h, points_a = 0, 3
        else:
            actual_h, actual_a = 0.5, 0.5
            points_h, points_a = 1, 1
            
        # Get rolling form before this match
        form_h = np.mean(team_history[h_id][-5:]) if team_history[h_id] else 1.0 # default form index
        form_a = np.mean(team_history[a_id][-5:]) if team_history[a_id] else 1.0
        
        # Get H2H history before this match
        h2h_key = (min(h_id, a_id), max(h_id, a_id))
        if h2h_key not in h2h:
            h2h[h2h_key] = []
        
        if h_id < a_id:
            h2h_val = np.mean(h2h[h2h_key]) if h2h[h2h_key] else 0.5
        else:
            h2h_val = 1.0 - np.mean(h2h[h2h_key]) if h2h[h2h_key] else 0.5
            
        # Save engineered features for this match state
        rows.append({
            "match_id": row["match_id"],
            "competition_id": row["competition_id"],
            "season": row["season"],
            "home_team_id": h_id,
            "away_team_id": a_id,
            "home_elo": h_elo,
            "away_elo": a_elo,
            "elo_diff": h_elo - a_elo,
            "home_form": form_h,
            "away_form": form_a,
            "form_diff": form_h - form_a,
            "h2h_val": h2h_val,
            "home_score": h_score,
            "away_score": a_score,
            "outcome": "HOME_WIN" if h_score > a_score else ("AWAY_WIN" if h_score < a_score else "DRAW")
        })
        
        # Update ELOs
        elos[h_id] = h_elo + K * (actual_h - expected_h)
        elos[a_id] = a_elo + K * (actual_a - expected_a)
        
        # Update history
        team_history[h_id].append(points_h)
        team_history[a_id].append(points_a)
        
        # Update H2H
        h2h_outcome = 1.0 if h_score > a_score else (0.0 if h_score < a_score else 0.5)
        if h_id < a_id:
            h2h[h2h_key].append(h2h_outcome)
        else:
            h2h[h2h_key].append(1.0 - h2h_outcome)
            
    os.makedirs("ml/data/processed", exist_ok=True)
    feat_df = pd.DataFrame(rows)
    feat_df.to_csv("ml/data/processed/engineered_features.csv", index=False)
    print(f"Engineered features computed and saved to ml/data/processed/engineered_features.csv")

if __name__ == "__main__":
    calculate_elo_and_features()
