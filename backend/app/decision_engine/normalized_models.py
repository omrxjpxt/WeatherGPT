from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel

from app.models.enums import TransportMode, HazardType, HazardSourceClass, AlertSeverity, AlertSourceClass

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
    radius_meters: float
    base_severity: int # 0-100 historical susceptibility
    source_name: str
    source_class: HazardSourceClass
    source_url: Optional[str] = None
    source_reference: Optional[str] = None
    reported_timestamp: Optional[datetime] = None
    
    # Optional weather triggers
    trigger_precipitation_mm: Optional[float] = None
    trigger_condition: Optional[str] = None

class HazardRelevanceResult(BaseModel):
    hazard_id: str
    spatially_relevant: bool = False
    weather_triggered: bool = False
    temporally_relevant: bool = False
    currently_relevant: bool = False
    relevance_reason: Optional[str] = None
    contribution_score: float = 0.0

class TripHazard(BaseModel):
    hazard: NormalizedHazard
    relevance: HazardRelevanceResult

class NormalizedAlert(BaseModel):
    id: str
    source_name: str
    source_class: AlertSourceClass
    severity: AlertSeverity
    affected_areas_polygon: List[List[float]] # Mock simple representation of area
    issued_at: datetime
    expires_at: Optional[datetime]
    action: Optional[str] = None
    source_url: Optional[str] = None
    is_override_eligible: bool = False

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
    agreement_status: str = "high"
