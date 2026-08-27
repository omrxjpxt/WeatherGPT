from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import Field
import uuid

from app.models.base import WeatherBaseModel
from app.models.risk import RiskAssessment, RiskFactor
from app.models.enums import TripStatus

class ScenarioRequest(WeatherBaseModel):
    pass # Currently flutter does not define this formally, but it's used in the API contract for `/scenarios/evaluate`

class ScenarioResult(WeatherBaseModel):
    scenario_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: TripStatus = TripStatus.success
    departure_time: datetime
    risk: Optional[RiskAssessment] = None
    estimated_duration: timedelta
    recommendation: Optional[str] = None
    changed_factors: List[RiskFactor] = []
