from typing import List
from datetime import datetime
import structlog

from app.providers.weather.base import WeatherProvider
from app.decision_engine.normalized_models import NormalizedWeatherPoint

logger = structlog.get_logger(__name__)

class FallbackWeatherProvider(WeatherProvider):
    """
    Wraps a primary weather provider and falls back to a secondary provider if the primary fails.
    """
    def __init__(self, primary: WeatherProvider, secondary: WeatherProvider):
        self.primary = primary
        self.secondary = secondary
        self._active_provider_name = primary.provider_name

    @property
    def provider_name(self) -> str:
        return self._active_provider_name

    async def get_forecast(self, lat: float, lng: float, start_time: datetime, hours: int) -> List[NormalizedWeatherPoint]:
        try:
            forecast = await self.primary.get_forecast(lat, lng, start_time, hours)
            self._active_provider_name = self.primary.provider_name
            return forecast
        except Exception as e:
            logger.error(
                "weather_provider_fallback",
                primary=self.primary.provider_name,
                secondary=self.secondary.provider_name,
                error=str(e)
            )
            self._active_provider_name = self.secondary.provider_name
            return await self.secondary.get_forecast(lat, lng, start_time, hours)
