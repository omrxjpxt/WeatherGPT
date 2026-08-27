import asyncio
from typing import List
from datetime import datetime, timedelta
from app.providers.weather.base import WeatherProvider
from app.decision_engine.normalized_models import NormalizedWeatherPoint

class MockWeatherProvider(WeatherProvider):
    async def get_forecast(self, lat: float, lng: float, start_time: datetime, hours: int) -> List[NormalizedWeatherPoint]:
        await asyncio.sleep(0.1) # Simulate network delay
        
        forecast = []
        for i in range(hours):
            time = start_time + timedelta(hours=i)
            # Simulate a rainy window between 8 AM and 10 AM local time
            is_rainy_window = 8 <= time.hour <= 10
            
            # Simple mock data matching Flutter's mock
            temp = 27.0 if is_rainy_window else 31.0 + (i % 3)
            precip = 28.0 + (i * 2) if is_rainy_window else 0.0
            humidity = 92 if is_rainy_window else 70
            wind = 22.0 if is_rainy_window else 10.0
            
            forecast.append(NormalizedWeatherPoint(
                time=time,
                temperature=temp,
                precipitation=precip,
                humidity=humidity,
                wind_speed=wind,
                condition="Heavy Rain" if is_rainy_window else "Partly Cloudy",
                is_extreme_heat=temp > 40.0,
                is_poor_visibility=is_rainy_window, # visibility drops in heavy rain
            ))
            
        return forecast
