from datetime import datetime, timedelta
from typing import List, Optional, Any
import uuid
from pydantic import BaseModel, Field

from app.models.enums import TransportMode, HazardType, HazardSourceClass, AlertSeverity, AlertSourceClass
from app.models.traffic import TrafficSnapshot

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
    # Phase 20 Intelligence Fields:
    precipitation_probability: Optional[float] = None # 0.0 - 100.0 %
    precipitation_intensity_category: Optional[str] = None # "none" | "light" | "moderate" | "heavy" | "violent"

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
    route_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    summary: str = "Primary Route"
    polyline: Optional[str] = None
    segments: List[NormalizedRouteSegment]
    total_distance_km: float
    total_duration: timedelta
    provider_name: str = "Unknown"
    provenance: str = "unknown"
    traffic: Optional[TrafficSnapshot] = None

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

    # Phase 21 Waterlogging & Underpass Intelligence
    is_underpass: bool = False
    water_depth_threshold_cm: float = 15.0
    impassable_modes: List[str] = Field(default_factory=lambda: ["walk", "bike"])
    chronic: bool = True
    location_name: Optional[str] = None

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
    affected_areas_polygon: List[List[float]] = Field(default_factory=list)
    issued_at: datetime
    expires_at: Optional[datetime] = None
    action: Optional[str] = None
    source_url: Optional[str] = None
    is_override_eligible: bool = False

    # Phase 21 Official Alert Metadata
    headline: Optional[str] = None
    event: Optional[str] = None
    urgency: Optional[str] = None
    certainty: Optional[str] = None
    affected_districts: List[str] = Field(default_factory=list)

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
    traffic: Optional[TrafficSnapshot] = None
    # Phase 20 Intelligence Fields:
    air_quality_timeline: Optional[List[Any]] = None
    geocoding_provenance: Optional[dict[str, str]] = None
