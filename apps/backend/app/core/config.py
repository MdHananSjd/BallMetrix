import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ballmetrix"
    )
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    API_FOOTBALL_KEY: str = os.getenv("API_FOOTBALL_KEY", "")
    THE_ODDS_API_KEY: str = os.getenv("THE_ODDS_API_KEY", "")
    OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")

    class Config:
        env_file = ".env"

settings = Settings()
