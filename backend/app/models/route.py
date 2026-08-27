from typing import Optional, List
from app.models.base import WeatherBaseModel
from app.models.enums import RiskLevel
from app.models.weather import WeatherPoint

class RouteSegment(WeatherBaseModel):
    start_lat: float
    start_lng: float
    end_lat: float
    end_lng: float
    risk_level: RiskLevel
    description: Optional[str] = None
    weather: Optional[WeatherPoint] = None

class Route(WeatherBaseModel):
    segments: List[RouteSegment]
