from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.models.enums import RiskLevel, TransportMode
from app.models.risk import RiskAssessment
from app.models.route import RouteSegment
from app.decision_engine.normalized_models import NormalizedHazard, NormalizedAlert

class SegmentRisk(BaseModel):
    segment_index: int
    risk_score: int
    risk_level: RiskLevel
    # Explanation
    reason: Optional[str] = None

class EngineDecisionResult(BaseModel):
    overall_risk: RiskAssessment
    segment_risks: List[SegmentRisk]
    route_segments_with_weather: List[RouteSegment]
    recommendation_headline: str
    recommendation_body: str
    suggested_mode: Optional[TransportMode] = None
    suggested_time: Optional[datetime] = None
    alert_override_applied: bool = False
    active_override_alert: Optional[NormalizedAlert] = None
    total_duration: timedelta
    total_distance_km: float
