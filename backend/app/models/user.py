from datetime import datetime, timezone
from typing import Optional
from pydantic import Field
from app.models.base import WeatherBaseModel

class UserProfile(WeatherBaseModel):
    uid: str
    email: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SavedRoute(WeatherBaseModel):
    id: str
    name: str
    origin_id: str
    destination_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ConversationSummary(WeatherBaseModel):
    id: str
    trip_id: str
    title: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TripHistorySummary(WeatherBaseModel):
    analysis_id: str
    status: str
    origin: str
    destination: str
    mode: str
    risk_level: Optional[str] = None
    recommendation_headline: Optional[str] = None
    created_at: datetime
    is_snapshot: bool = True
