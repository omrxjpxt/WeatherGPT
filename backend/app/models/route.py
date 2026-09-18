from datetime import timedelta, datetime
from typing import Optional, List
from pydantic import Field

from app.models.base import WeatherBaseModel
from app.models.enums import RiskLevel
from app.models.weather import WeatherPoint
from app.models.traffic import TrafficSnapshot
from app.models.hazard import Hazard

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

class RouteEvaluation(WeatherBaseModel):
    route_id: str
    risk_score: int
    risk_level: RiskLevel
    static_duration: timedelta
    traffic_aware_duration: timedelta
    traffic_delay_seconds: float
    exposure_score: float
    bottleneck_score: int
    hazard_count: int
    is_feasible: bool
    feasibility_reason: Optional[str] = None
    recommendation_headline: str
    recommendation_body: str
    suggested_mode: Optional[str] = None
    suggested_departure_time: Optional[datetime] = None
    is_selected: bool = False
    selection_reason: Optional[str] = None
    provenance: str

from app.models.risk import RiskAssessment

class EvaluatedRoute(WeatherBaseModel):
    route_id: str
    summary: str
    distance_km: float
    static_duration: timedelta
    polyline: Optional[str] = None
    segments: List[RouteSegment]
    traffic: Optional[TrafficSnapshot] = None
    evaluation: RouteEvaluation
    hazards: List[Hazard] = Field(default_factory=list)
    source_name: str
    provenance: str
    risk: Optional[RiskAssessment] = None
