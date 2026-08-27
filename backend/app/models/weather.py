from datetime import datetime
from typing import List, Optional
from app.models.base import WeatherBaseModel

class WeatherPoint(WeatherBaseModel):
    time: datetime
    temperature: float # Celsius
    precipitation_mm: float # mm accumulation (previous hour)
    humidity: int # percentage
    wind_speed: float # km/h
    wind_gusts: float # km/h
    visibility: float # meters
    condition: str
    icon: str

class WeatherSnapshot(WeatherBaseModel):
    current: WeatherPoint
    forecast: List[WeatherPoint]

class WeatherTimeline(WeatherBaseModel):
    points: List[WeatherPoint]
