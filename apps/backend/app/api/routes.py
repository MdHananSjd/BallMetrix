from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Competition, Team, Match, CompetitionTeam, ModelVersion, ModelMetrics
from app.services.api_client import api_client
from app.services.prediction_service import prediction_service
from datetime import datetime

router = APIRouter()

@router.get("/competitions")
def get_competitions(db: Session = Depends(get_db)):
    comps = db.query(Competition).all()
    return [{"id": c.id, "name": c.name, "type": c.type, "country": c.country} for c in comps]

@router.get("/teams")
def get_teams(competition_id: str = None, db: Session = Depends(get_db)):
    if competition_id:
        teams = db.query(Team).join(CompetitionTeam).filter(CompetitionTeam.competition_id == competition_id).all()
    else:
        teams = db.query(Team).all()
    return [{"id": t.id, "name": t.name, "code": t.code, "country": t.country, "logo_url": t.logo_url} for t in teams]

@router.get("/matches")
def get_matches(competition_id: str = "WC2026", season: int = 2026, db: Session = Depends(get_db)):
    # Verify competition exists in DB
    comp = db.query(Competition).filter(Competition.id == competition_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Competition not found")

    # Fetch latest fixtures from external API client (which handles caching)
    raw_fixtures = api_client.get_matches(competition_id, season)
    
    matches_list = []
    for f in raw_fixtures:
        fixture_id = f["fixture"]["id"]
        home_t = f["teams"]["home"]
        away_t = f["teams"]["away"]
        venue = f["fixture"]["venue"] or {}
        
        # Verify or seed home/away teams in database if not present
        for t_side in [home_t, away_t]:
            team_id = t_side["id"]
            existing = db.query(Team).filter(Team.id == team_id).first()
            if not existing:
                team = Team(
                    id=team_id,
                    name=t_side["name"],
                    logo_url=t_side["logo"],
                    code=t_side.get("code"),
                    country=t_side.get("country")
                )
                db.add(team)
                db.commit()
                
                # Link to competition
                ct = CompetitionTeam(competition_id=competition_id, team_id=team_id, season=season)
                db.add(ct)
                db.commit()

        # Check if match exists in DB, otherwise save it
        match_record = db.query(Match).filter(Match.id == fixture_id).first()
        match_date = datetime.fromisoformat(f["fixture"]["date"].replace("Z", "+00:00"))
        
        status_raw = f["fixture"]["status"]["short"]
        status = "Scheduled"
        if status_raw in ["FT", "AET", "PEN"]:
            status = "Finished"
        elif status_raw in ["1H", "2H", "HT", "ET", "P"]:
            status = "In_Play"

        goals = f.get("goals", {})
        home_score = goals.get("home")
        away_score = goals.get("away")

        if not match_record:
            match_record = Match(
                id=fixture_id,
                competition_id=competition_id,
                season=season,
                home_team_id=home_t["id"],
                away_team_id=away_t["id"],
                match_date=match_date,
                stage=f["league"]["round"],
                status=status,
                home_score=home_score,
                away_score=away_score
            )
            db.add(match_record)
            db.commit()
        else:
            # Update score and status if changed
            match_record.status = status
            match_record.home_score = home_score
            match_record.away_score = away_score
            db.commit()

        matches_list.append({
            "match_id": fixture_id,
            "home_team": {
                "id": home_t["id"],
                "name": home_t["name"],
                "logo_url": home_t["logo"]
            },
            "away_team": {
                "id": away_t["id"],
                "name": away_t["name"],
                "logo_url": away_t["logo"]
            },
            "match_date": match_date.isoformat(),
            "stage": f["league"]["round"],
            "status": status,
            "venue_city": venue.get("city", "Unknown City"),
            "score": f"{home_score}-{away_score}" if home_score is not None else None
        })

    return matches_list

@router.get("/predict")
def get_prediction(
    match_id: int, 
    home_id: int, 
    away_id: int, 
    venue_city: str = None, 
    db: Session = Depends(get_db)
):
    try:
        results = prediction_service.predict_match(db, match_id, home_id, away_id, venue_city)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

@router.get("/performance")
def get_performance(db: Session = Depends(get_db)):
    models = db.query(ModelVersion).order_by(ModelVersion.created_at.desc()).all()
    results = []
    for m in models:
        metrics = db.query(ModelMetrics).filter(ModelMetrics.model_version_id == m.id).first()
        results.append({
            "version": m.version_string,
            "run_id": m.run_id,
            "status": m.status,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "metrics": {
                "accuracy": metrics.test_accuracy if metrics else 0.0,
                "log_loss": metrics.test_log_loss if metrics else 0.0,
                "brier_score": metrics.test_brier_score if metrics else 0.0
            }
        })
    return results
