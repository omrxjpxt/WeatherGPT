from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import Field
import uuid

from app.models.base import WeatherBaseModel
from app.models.enums import TransportMode, TripStatus
from app.models.risk import RiskAssessment
from app.models.route import RouteSegment
from app.models.hazard import Hazard

class Recommendation(WeatherBaseModel):
    headline: str
    body: str
    alternative_action: Optional[str] = None
    suggested_mode: Optional[TransportMode] = None
    suggested_departure_time: Optional[datetime] = None

class ModeOption(WeatherBaseModel):
    mode: TransportMode
    estimated_duration: timedelta
    risk: Optional[RiskAssessment] = None
    distance_km: float
    recommendation: Optional[str] = None
    highlights: List[str]

class DataSource(WeatherBaseModel):
    name: str
    type: str
    last_updated: datetime

class TripRequest(WeatherBaseModel):
    origin: str
    destination: str
    departure_time: datetime
    mode: TransportMode
    arrival_deadline: Optional[datetime] = None

class TripResponse(WeatherBaseModel):
    analysis_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: TripStatus = TripStatus.success
    request: TripRequest
    risk: Optional[RiskAssessment] = None
    route: List[RouteSegment]
    recommendation: Optional[Recommendation] = None
    mode_options: List[ModeOption]
    hazards: List[Hazard]
    sources: List[DataSource]
    estimated_duration: timedelta
    distance_km: float
