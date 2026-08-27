from typing import List
from fastapi import APIRouter, Depends
from datetime import datetime, timezone
from app.models.weather import WeatherPoint
from app.api.dependencies import get_weather_provider
from app.providers.weather.base import WeatherProvider

router = APIRouter()

@router.get("/current", response_model=WeatherPoint, response_model_by_alias=True)
async def get_current_weather(
    lat: float, 
    lng: float,
    provider: WeatherProvider = Depends(get_weather_provider)
):
    # Pass current time
    now = datetime.now(timezone.utc)
    forecast = await provider.get_forecast(lat, lng, now, 1)
    if forecast and forecast.points:
        return forecast.points[0]
    raise Exception("Weather data unavailable")

@router.get("/forecast", response_model=List[WeatherPoint], response_model_by_alias=True)
async def get_forecast(
    lat: float, 
    lng: float,
    provider: WeatherProvider = Depends(get_weather_provider)
):
    now = datetime.now(timezone.utc)
    forecast = await provider.get_forecast(lat, lng, now, 24)
    if forecast and forecast.points:
        return forecast.points
    return []
