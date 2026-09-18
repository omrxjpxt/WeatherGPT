from typing import Optional, List
from datetime import datetime
from enum import Enum
from pydantic import Field

from app.models.base import WeatherBaseModel
from app.models.enums import TransportMode, TripStatus, RiskLevel
from app.models.trip import TripRequest, TripResponse


class UserIntentEnum(str, Enum):
    trip_decision = "trip_decision"
    weather_question = "weather_question"
    route_comparison = "route_comparison"
    what_if = "what_if"
    alert_question = "alert_question"
    general_weather = "general_weather"


class ExtractedIntent(WeatherBaseModel):
    origin: Optional[str] = None
    destination: Optional[str] = None
    departure_time: Optional[datetime] = None
    arrival_deadline: Optional[datetime] = None
    mode: Optional[TransportMode] = None
    trip_date: Optional[str] = None
    user_intent: UserIntentEnum = UserIntentEnum.trip_decision
    weather_concern: Optional[str] = None
    scenario_modifiers: List[str] = Field(default_factory=list)
    raw_query: str = ""


class DecisionFacts(WeatherBaseModel):
    status: TripStatus
    origin: str
    destination: str
    mode: TransportMode
    departure_time: datetime
    arrival_deadline: Optional[datetime] = None
    selected_route_summary: Optional[str] = None
    selected_route_id: Optional[str] = None
    distance_km: Optional[float] = None
    static_duration_minutes: Optional[int] = None
    traffic_aware_duration_minutes: Optional[int] = None
    traffic_delay_minutes: Optional[int] = None
    traffic_status: Optional[str] = None
    traffic_condition: Optional[str] = None
    risk_score: Optional[int] = None
    risk_level: Optional[RiskLevel] = None
    risk_factors: List[str] = Field(default_factory=list)
    recommendation_headline: Optional[str] = None
    recommendation_body: Optional[str] = None
    active_alerts: List[str] = Field(default_factory=list)
    active_hazards: List[str] = Field(default_factory=list)
    route_alternatives_summaries: List[str] = Field(default_factory=list)
    alternatives_count: int = 0
    is_feasible: bool = True
    feasibility_reason: Optional[str] = None
    weather_condition: Optional[str] = None
    weather_temperature_c: Optional[float] = None
    weather_precipitation_mm: Optional[float] = None
    provenance_sources: List[str] = Field(default_factory=list)


class AssistantParseRequest(WeatherBaseModel):
    query: str
    reference_time: Optional[datetime] = None


class AssistantParseResponse(WeatherBaseModel):
    intent: ExtractedIntent
    is_complete: bool
    missing_fields: List[str] = Field(default_factory=list)
    clarification_prompt: Optional[str] = None


class AssistantChatRequest(WeatherBaseModel):
    message: str
    context_origin: Optional[str] = None
    context_destination: Optional[str] = None
    context_mode: Optional[TransportMode] = None
    context_time: Optional[datetime] = None


class AssistantChatResponse(WeatherBaseModel):
    message: str
    intent: ExtractedIntent
    trip_request: Optional[TripRequest] = None
    trip_response: Optional[TripResponse] = None
    status: str  # "success", "need_clarification", "degraded", "error", "info"
    clarification_prompt: Optional[str] = None
    provenance: str = "demo/mock"
    grounding_fallback_used: bool = False
