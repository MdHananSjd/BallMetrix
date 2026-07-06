from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base

class Competition(Base):
    __tablename__ = "competitions"

    id = Column(String, primary_key=True)  # e.g., "WC2026", "PL2026"
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # "cup", "league"
    country = Column(String, nullable=False)

    matches = relationship("Match", back_populates="competition")
    competition_teams = relationship("CompetitionTeam", back_populates="competition")


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    logo_url = Column(String, nullable=True)
    code = Column(String, nullable=True)
    country = Column(String, nullable=True)

    competition_teams = relationship("CompetitionTeam", back_populates="team")


class CompetitionTeam(Base):
    __tablename__ = "competition_teams"

    id = Column(Integer, primary_key=True, autoincrement=True)
    competition_id = Column(String, ForeignKey("competitions.id", ondelete="CASCADE"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    season = Column(Integer, nullable=False)

    competition = relationship("Competition", back_populates="competition_teams")
    team = relationship("Team", back_populates="competition_teams")


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True)
    competition_id = Column(String, ForeignKey("competitions.id", ondelete="CASCADE"), nullable=False)
    season = Column(Integer, nullable=False)
    home_team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    away_team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    match_date = Column(DateTime, nullable=False)
    stage = Column(String, nullable=False)  # e.g., "Group Stage", "Round of 16"
    status = Column(String, nullable=False)  # e.g., "Scheduled", "Finished", "In_Play"
    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)

    competition = relationship("Competition", back_populates="matches")
    home_team = relationship("Team", foreign_keys=[home_team_id])
    away_team = relationship("Team", foreign_keys=[away_team_id])
    predictions = relationship("Prediction", back_populates="match")
    team_stats = relationship("TeamStats", back_populates="match")
    player_stats = relationship("PlayerStats", back_populates="match")


class HistoricalMatch(Base):
    __tablename__ = "historical_matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    competition_id = Column(String, ForeignKey("competitions.id", ondelete="CASCADE"), nullable=False)
    season = Column(Integer, nullable=False)
    home_team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    away_team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    match_date = Column(DateTime, nullable=False)
    home_score = Column(Integer, nullable=False)
    away_score = Column(Integer, nullable=False)

    home_team = relationship("Team", foreign_keys=[home_team_id])
    away_team = relationship("Team", foreign_keys=[away_team_id])


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    position = Column(String, nullable=True)

    team = relationship("Team")


class PlayerStats(Base):
    __tablename__ = "player_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(Integer, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    goals = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    rating = Column(Float, nullable=True)
    xG = Column(Float, nullable=True)
    xA = Column(Float, nullable=True)

    match = relationship("Match", back_populates="player_stats")
    player = relationship("Player")


class TeamStats(Base):
    __tablename__ = "team_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(Integer, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    shots = Column(Integer, default=0)
    possession = Column(Float, default=0.0)  # e.g., 55.4
    corners = Column(Integer, default=0)
    fouls = Column(Integer, default=0)
    xG = Column(Float, nullable=True)

    match = relationship("Match", back_populates="team_stats")
    team = relationship("Team")


class EngineeredFeatures(Base):
    __tablename__ = "engineered_features"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    match_id = Column(Integer, ForeignKey("matches.id", ondelete="CASCADE"), nullable=True)
    calculated_at = Column(DateTime, server_default=func.now())
    elo = Column(Float, nullable=False)
    rolling_form = Column(Float, nullable=False)  # Form representation
    h2h_rating = Column(Float, nullable=False)
    venue_effect = Column(Float, nullable=False)
    squad_health = Column(Float, nullable=False)

    team = relationship("Team")
    match = relationship("Match")


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(Integer, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False)
    predicted_home_win_pct = Column(Float, nullable=False)
    predicted_away_win_pct = Column(Float, nullable=False)
    predicted_draw_pct = Column(Float, nullable=False)
    model_version_id = Column(Integer, ForeignKey("model_versions.id"), nullable=False)
    predicted_at = Column(DateTime, server_default=func.now())

    match = relationship("Match", back_populates="predictions")
    model_version = relationship("ModelVersion")
    prediction_result = relationship("PredictionResult", uselist=False, back_populates="prediction")


class PredictionResult(Base):
    __tablename__ = "prediction_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prediction_id = Column(Integer, ForeignKey("predictions.id", ondelete="CASCADE"), nullable=False)
    actual_outcome = Column(String, nullable=False)  # "HOME_WIN", "AWAY_WIN", "DRAW"
    brier_score = Column(Float, nullable=False)
    log_loss = Column(Float, nullable=False)
    was_correct = Column(Boolean, nullable=False)

    prediction = relationship("Prediction", back_populates="prediction_result")


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version_string = Column(String, nullable=False, unique=True)
    run_id = Column(String, nullable=False)  # MLflow run UUID
    status = Column(String, default="candidate")  # "production", "candidate", "deprecated"
    created_at = Column(DateTime, server_default=func.now())

    metrics = relationship("ModelMetrics", back_populates="model_version", uselist=False)


class ModelMetrics(Base):
    __tablename__ = "model_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_version_id = Column(Integer, ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False)
    test_accuracy = Column(Float, nullable=False)
    test_log_loss = Column(Float, nullable=False)
    test_brier_score = Column(Float, nullable=False)

    model_version = relationship("ModelVersion", back_populates="metrics")


class DataSourceLog(Base):
    __tablename__ = "data_source_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    endpoint = Column(String, nullable=False)
    query_params = Column(String, nullable=True)
    status_code = Column(Integer, nullable=False)
    timestamp = Column(DateTime, server_default=func.now())


class CacheMetadata(Base):
    __tablename__ = "cache_metadata"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cache_key = Column(String, nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
