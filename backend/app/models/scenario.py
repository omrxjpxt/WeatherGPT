from datetime import datetime, timedelta
from typing import List
from pydantic import Field
import uuid

from app.models.base import WeatherBaseModel
from app.models.risk import RiskAssessment, RiskFactor

class ScenarioRequest(WeatherBaseModel):
    pass # Currently flutter does not define this formally, but it's used in the API contract for `/scenarios/evaluate`

class ScenarioResult(WeatherBaseModel):
    scenario_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    departure_time: datetime
    risk: RiskAssessment
    estimated_duration: timedelta
    recommendation: str
    changed_factors: List[RiskFactor]
