from datetime import datetime
from typing import Optional
from app.models.base import WeatherBaseModel
from app.models.enums import HazardType, RiskLevel

class Hazard(WeatherBaseModel):
    id: str
    type: HazardType
    title: str
    description: str
    lat: float
    lng: float
    severity: RiskLevel
    reported_at: Optional[datetime] = None
    source: Optional[str] = None
