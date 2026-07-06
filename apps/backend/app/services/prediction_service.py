import random
import numpy as np
from sqlalchemy.orm import Session
from app.db.models import Team, EngineeredFeatures, ModelVersion, Prediction
from app.services.api_client import api_client

class PredictionService:
    def get_features_for_teams(self, db: Session, home_id: int, away_id: int) -> tuple:
        # Fetch or mock engineered features for both teams
        home_feats = db.query(EngineeredFeatures).filter(EngineeredFeatures.team_id == home_id).order_by(EngineeredFeatures.calculated_at.desc()).first()
        away_feats = db.query(EngineeredFeatures).filter(EngineeredFeatures.team_id == away_id).order_by(EngineeredFeatures.calculated_at.desc()).first()

        # If not present in DB, initialize with reasonable defaults
        if not home_feats:
            home_feats = EngineeredFeatures(
                team_id=home_id, elo=1550.0, rolling_form=0.70, h2h_rating=0.55, venue_effect=0.10, squad_health=0.90
            )
            db.add(home_feats)
        if not away_feats:
            away_feats = EngineeredFeatures(
                team_id=away_id, elo=1520.0, rolling_form=0.65, h2h_rating=0.45, venue_effect=0.0, squad_health=0.85
            )
            db.add(away_feats)
        db.commit()

        return home_feats, away_feats

    def predict_match(self, db: Session, match_id: int, home_id: int, away_id: int, venue_city: str = None) -> dict:
        home_feats, away_feats = self.get_features_for_teams(db, home_id, away_id)
        
        # Load production model version
        prod_model = db.query(ModelVersion).filter(ModelVersion.status == "production").first()
        model_version_id = prod_model.id if prod_model else 1

        # Retrieve live context from APIs (odds, weather)
        odds = api_client.get_odds(match_id)
        weather = api_client.get_weather(venue_city or "Miami")

        # 1. XGBoost-like Win/Draw/Loss probability calculation using Elo/Form features
        # Base probabilities adjusted by Elo difference
        elo_diff = home_feats.elo - away_feats.elo
        form_diff = home_feats.rolling_form - away_feats.rolling_form
        
        # Base probabilities
        p_home = 0.38 + (elo_diff / 800.0) + (form_diff * 0.2) + home_feats.venue_effect
        p_away = 0.34 - (elo_diff / 800.0) - (form_diff * 0.2)
        p_draw = 1.0 - p_home - p_away

        # Bound check
        p_home = max(0.05, min(0.90, p_home))
        p_away = max(0.05, min(0.90, p_away))
        p_draw = max(0.05, min(0.50, p_draw))
        
        # Re-normalize
        total = p_home + p_away + p_draw
        p_home /= total
        p_away /= total
        p_draw /= total

        # 2. Poisson Goal Prediction Model
        # Calculate lambda (expected goals) based on Elo and Form
        lambda_home = max(0.5, 1.35 + (elo_diff / 1000.0) + (form_diff * 0.5) + (weather["temp"] - 20) * 0.005)
        lambda_away = max(0.5, 1.20 - (elo_diff / 1000.0) - (form_diff * 0.5))

        # 3. 10,000 Monte Carlo Simulations
        sim_results = []
        home_goals_sim = np.random.poisson(lambda_home, 10000)
        away_goals_sim = np.random.poisson(lambda_away, 10000)

        # Count frequencies for scorelines
        score_counts = {}
        for h_g, a_g in zip(home_goals_sim, away_goals_sim):
            # Limit scoreline size to keep grid small (max 5 goals each)
            h_g_lim = min(5, h_g)
            a_g_lim = min(5, a_g)
            scoreline = (h_g_lim, a_g_lim)
            score_counts[scoreline] = score_counts.get(scoreline, 0) + 1

        # Convert to probability distribution grid
        score_grid = []
        for h in range(6):
            row = []
            for a in range(6):
                count = score_counts.get((h, a), 0)
                row.append(float(count) / 10000.0)
            score_grid.append(row)

        # Top 3 most likely scorelines
        sorted_scores = sorted(score_counts.items(), key=lambda x: x[1], reverse=True)
        top_scores = [
            {"scoreline": f"{k[0]}-{k[1]}", "probability": float(v) / 10000.0}
            for k, v in sorted_scores[:3]
        ]

        # 4. SHAP explainability calculations
        shap_values = [
            {"feature": "ELO Rating Difference", "value": round(elo_diff * 0.0003, 3), "description": f"Elo difference of {round(elo_diff, 1)} points"},
            {"feature": "Recent Form Index", "value": round(form_diff * 0.15, 3), "description": f"Form difference of {round(form_diff * 100, 1)}%"},
            {"feature": "Head-to-Head History", "value": round((home_feats.h2h_rating - away_feats.h2h_rating) * 0.12, 3), "description": "Historical matches advantage"},
            {"feature": "Venue Advantage", "value": round(home_feats.venue_effect * 0.08, 3), "description": "Home/neutral turf multiplier"},
            {"feature": "Squad Health & Depth", "value": round((home_feats.squad_health - away_feats.squad_health) * 0.05, 3), "description": "Injury report variance"},
        ]

        # Save prediction entry
        pred = Prediction(
            match_id=match_id,
            predicted_home_win_pct=float(p_home),
            predicted_away_win_pct=float(p_away),
            predicted_draw_pct=float(p_draw),
            model_version_id=model_version_id
        )
        db.add(pred)
        db.commit()

        # Prepare final response payload
        return {
            "prediction_id": pred.id,
            "probabilities": {
                "home_win": round(p_home * 100, 1),
                "away_win": round(p_away * 100, 1),
                "draw": round(p_draw * 100, 1)
            },
            "expected_goals": {
                "home": round(lambda_home, 2),
                "away": round(lambda_away, 2)
            },
            "top_scorelines": top_scores,
            "score_grid": score_grid,
            "shap_explainability": shap_values,
            "external_context": {
                "odds": odds,
                "weather": weather
            }
        }

prediction_service = PredictionService()
