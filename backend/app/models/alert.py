from datetime import datetime
from typing import List, Optional
from app.models.base import WeatherBaseModel
from app.models.enums import AlertSeverity

class OfficialAlert(WeatherBaseModel):
    id: str
    title: str
    description: str
    severity: AlertSeverity
    issued_by: str
    issued_at: datetime
    expires_at: Optional[datetime] = None
    affected_areas: List[str]
    action_required: Optional[str] = None
    source: Optional[str] = None
