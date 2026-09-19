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
    geocoding_provider: str = "auto" # "auto", "google", "nominatim", "open-meteo", "gazetteer", "mock"
    air_quality_provider: str = "open-meteo" # "open-meteo", "mock", "disabled"
    air_quality_enabled: bool = True
    google_traffic_aware: bool = True
    nominatim_user_agent: str = "WeatherGPT-Navigation/1.0 (https://github.com/weathergpt)"
    weather_api_key: Optional[str] = None
    traffic_api_key: Optional[str] = None
    llm_api_key: Optional[str] = None    # Provider Credentials
    google_maps_api_key: Optional[str] = None
    weatherapi_api_key: Optional[str] = None

    # Firestore
    firestore_project_id: Optional[str] = None

    # We want to load from .env file if available
    # Feature Flags
    demo_mode: bool = False

    # CORS Configuration
    cors_origins: list[str] = [
        "http://localhost:8000",
        "http://localhost:3000",
        "http://127.0.0.1:8000",
        "http://10.0.2.2:8000",
    ]

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute_anonymous: int = 30
    rate_limit_per_minute_authenticated: int = 120

    # Source Comparison Thresholds
    temperature_diff_threshold_c: float = 5.0
    precipitation_diff_threshold_mm: float = 5.0
    wind_diff_threshold_kmh: float = 15.0
    visibility_diff_threshold_m: float = 2000.0
    
    # Hazard Influence Factor (Engineering Assumption)
    hazard_influence_factor: float = 0.5

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def is_testing(self) -> bool:
        return self.environment.lower() == "test"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
