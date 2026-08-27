from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel

from app.models.enums import TransportMode, HazardType, AlertSeverity

class NormalizedWeatherPoint(BaseModel):
    time: datetime
    temperature: float
    precipitation_mm: float
    humidity: int
    wind_speed: float
    wind_gusts: float
    visibility: float # meters
    condition: str
    is_extreme_heat: bool
    is_poor_visibility: bool

class NormalizedRouteSegment(BaseModel):
    start_lat: float
    start_lng: float
    end_lat: float
    end_lng: float
    distance_km: float
    estimated_duration: timedelta
    # Base traffic coefficient independent of weather
    traffic_congestion_factor: float = 1.0

class NormalizedRoute(BaseModel):
    segments: List[NormalizedRouteSegment]
    total_distance_km: float
    total_duration: timedelta

class NormalizedHazard(BaseModel):
    id: str
    type: HazardType
    lat: float
    lng: float
    severity_score: int # 0-100

class NormalizedAlert(BaseModel):
    id: str
    severity: AlertSeverity
    affected_areas_polygon: List[List[float]] # Mock simple representation of area
    issued_at: datetime
    expires_at: Optional[datetime]
    requires_override: bool

class TripContext(BaseModel):
    origin: str
    destination: str
    departure_time: datetime
    mode: TransportMode
    route: NormalizedRoute
    weather_timeline: List[NormalizedWeatherPoint]
    hazards: List[NormalizedHazard]
    alerts: List[NormalizedAlert]
    arrival_deadline: Optional[datetime] = None
