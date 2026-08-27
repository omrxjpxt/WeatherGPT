from datetime import datetime, timezone, timedelta
from typing import List, Optional
import httpx
import logging

from app.providers.weather.base import WeatherProvider
from app.decision_engine.normalized_models import NormalizedWeatherPoint
from app.providers.weatherapi_client import WeatherApiClient

logger = logging.getLogger(__name__)

class WeatherApiWeatherProvider(WeatherProvider):
    def __init__(self, client: Optional[WeatherApiClient] = None):
        self.client = client or WeatherApiClient()
        
    @property
    def provider_name(self) -> str:
        return "WeatherAPI"
        
    async def get_forecast(self, lat: float, lng: float, start_time: datetime, hours: int) -> List[NormalizedWeatherPoint]:
        try:
            # WeatherAPI provides up to 14 days based on tier, 2 is usually safe for short trips
            days = 2 
            if hours > 24:
                days = (hours // 24) + 1
            
            data = await self.client.fetch_forecast(lat, lng, days=days)
            return self._normalize(data, start_time, hours)
            
        except httpx.HTTPStatusError as e:
            logger.error(f"WeatherAPI HTTP error: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"WeatherAPI fetch failed: {e}")
            raise
            
    def _normalize(self, data: dict, start_time: datetime, hours: int) -> List[NormalizedWeatherPoint]:
        timeline = []
        target_end = start_time + timedelta(hours=hours)
        
        forecast_days = data.get("forecast", {}).get("forecastday", [])
        
        for day in forecast_days:
            for hour_data in day.get("hour", []):
                # time_epoch is UTC
                point_time = datetime.fromtimestamp(hour_data["time_epoch"], tz=timezone.utc)
                
                # We want buckets that cover our travel window + some buffer
                if start_time - timedelta(hours=1) <= point_time <= target_end + timedelta(hours=24):
                    
                    # Normalize condition to string
                    condition = hour_data.get("condition", {}).get("text", "Unknown")
                    
                    # Open-Meteo provides direct visibility. WeatherAPI provides vis_km
                    vis_m = hour_data.get("vis_km", 10.0) * 1000.0
                    
                    timeline.append(NormalizedWeatherPoint(
                        time=point_time,
                        temperature=float(hour_data.get("temp_c", 0.0)),
                        precipitation_mm=float(hour_data.get("precip_mm", 0.0)),
                        humidity=int(hour_data.get("humidity", 0)),
                        wind_speed=float(hour_data.get("wind_kph", 0.0)),
                        wind_gusts=float(hour_data.get("gust_kph", hour_data.get("wind_kph", 0.0))),
                        visibility=vis_m,
                        condition=condition,
                        is_extreme_heat=float(hour_data.get("temp_c", 0.0)) > 45.0,
                        is_poor_visibility=vis_m < 1000.0
                    ))
                    
        return sorted(timeline, key=lambda x: x.time)
