from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    project_name: str = "WeatherGPT Backend"
    version: str = "0.1.0"
    environment: str = "development"
    port: int = 8000
    log_level: str = "INFO"

    # External APIs
    weather_provider: str = "open-meteo" # "open-meteo" or "mock"
    routing_provider: str = "google" # "google" or "mock"
    weather_api_key: Optional[str] = None
    traffic_api_key: Optional[str] = None
    llm_api_key: Optional[str] = None
    google_maps_api_key: Optional[str] = None

    # Firestore
    firestore_project_id: Optional[str] = None

    # We want to load from .env file if available
    # Feature Flags
    demo_mode: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
