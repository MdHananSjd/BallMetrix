from app.db.database import Base, engine, SessionLocal
from app.db.models import Competition, Team, CompetitionTeam, ModelVersion, ModelMetrics
from datetime import datetime

def seed_database():
    # Create tables
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if competition already exists
        comp = db.query(Competition).filter(Competition.id == "WC2026").first()
        if not comp:
            comp = Competition(
                id="WC2026",
                name="FIFA World Cup 2026",
                type="cup",
                country="International"
            )
            db.add(comp)
            db.commit()

        # Seed teams
        team_data = [
            {"id": 1, "name": "Argentina", "code": "ARG", "country": "Argentina"},
            {"id": 2, "name": "France", "code": "FRA", "country": "France"},
            {"id": 3, "name": "Brazil", "code": "BRA", "country": "Brazil"},
            {"id": 4, "name": "England", "code": "ENG", "country": "England"},
            {"id": 5, "name": "Spain", "code": "ESP", "country": "Spain"},
            {"id": 6, "name": "Germany", "code": "GER", "country": "Germany"},
            {"id": 7, "name": "Portugal", "code": "POR", "country": "Portugal"},
            {"id": 8, "name": "Netherlands", "code": "NED", "country": "Netherlands"},
            {"id": 9, "name": "USA", "code": "USA", "country": "USA"},
            {"id": 10, "name": "Mexico", "code": "MEX", "country": "Mexico"},
            {"id": 11, "name": "Canada", "code": "CAN", "country": "Canada"},
            {"id": 12, "name": "Croatia", "code": "CRO", "country": "Croatia"},
            {"id": 13, "name": "Morocco", "code": "MAR", "country": "Morocco"},
            {"id": 14, "name": "Japan", "code": "JPN", "country": "Japan"},
            {"id": 15, "name": "Senegal", "code": "SEN", "country": "Senegal"},
            {"id": 16, "name": "Italy", "code": "ITA", "country": "Italy"},
        ]

        for t_info in team_data:
            existing_team = db.query(Team).filter(Team.id == t_info["id"]).first()
            if not existing_team:
                team = Team(
                    id=t_info["id"],
                    name=t_info["name"],
                    code=t_info["code"],
                    country=t_info["country"],
                    logo_url=f"https://media.api-sports.io/football/teams/{t_info['id']}.png"
                )
                db.add(team)
                db.commit()

                # Add to competition mapping
                ct = CompetitionTeam(
                    competition_id="WC2026",
                    team_id=t_info["id"],
                    season=2026
                )
                db.add(ct)
                db.commit()

        # Seed a baseline Model Version
        model_ver = db.query(ModelVersion).filter(ModelVersion.version_string == "v1.0.0").first()
        if not model_ver:
            model_ver = ModelVersion(
                version_string="v1.0.0",
                run_id="baseline_run_id",
                status="production"
            )
            db.add(model_ver)
            db.commit()

            metrics = ModelMetrics(
                model_version_id=model_ver.id,
                test_accuracy=0.625,
                test_log_loss=0.884,
                test_brier_score=0.485
            )
            db.add(metrics)
            db.commit()

        print("Database seeded successfully!")
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
