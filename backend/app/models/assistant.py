from typing import Optional
from datetime import datetime
from app.models.base import WeatherBaseModel
from app.models.enums import TransportMode

class AssistantParseRequest(WeatherBaseModel):
    query: str

class ExtractedIntent(WeatherBaseModel):
    origin: Optional[str] = None
    destination: Optional[str] = None
    departure_time: Optional[datetime] = None
    mode: Optional[TransportMode] = None

class AssistantParseResponse(WeatherBaseModel):
    intent: ExtractedIntent
    is_complete: bool
    missing_fields: list[str]
    clarification_prompt: Optional[str] = None
