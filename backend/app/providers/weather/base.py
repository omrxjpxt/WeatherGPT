from abc import ABC, abstractmethod
from typing import List
from datetime import datetime
from app.decision_engine.normalized_models import NormalizedWeatherPoint

class WeatherProvider(ABC):
    @abstractmethod
    async def get_forecast(self, lat: float, lng: float, start_time: datetime, hours: int) -> List[NormalizedWeatherPoint]:
        """Fetch weather forecast for a location."""
        pass
