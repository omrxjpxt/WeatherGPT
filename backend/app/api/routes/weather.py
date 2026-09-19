from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime, timezone
import logging

from app.models.weather import WeatherPoint
from app.decision_engine.normalized_models import NormalizedWeatherPoint
from app.api.dependencies import get_weather_provider
from app.providers.weather.base import WeatherProvider

logger = logging.getLogger(__name__)

router = APIRouter()


def _to_weather_point(p: NormalizedWeatherPoint) -> WeatherPoint:
    return WeatherPoint(
        time=p.time,
        temperature=p.temperature,
        precipitation_mm=p.precipitation_mm,
        humidity=p.humidity,
        wind_speed=p.wind_speed,
        wind_gusts=p.wind_gusts,
        visibility=p.visibility,
        condition=p.condition,
        icon="🌧️" if p.precipitation_mm > 0 else ("☀️" if "clear" in p.condition.lower() else "⛅"),
    )


@router.get("/current", response_model=WeatherPoint, response_model_by_alias=True)
async def get_current_weather(
    lat: float, 
    lng: float,
    provider: WeatherProvider = Depends(get_weather_provider)
):
    now = datetime.now(timezone.utc)
    try:
        forecast = await provider.get_forecast(lat, lng, now, 1)
    except Exception as e:
        logger.error(f"Weather provider error on /current: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Weather service is currently unavailable",
        )

    if forecast and len(forecast) > 0:
        return _to_weather_point(forecast[0])

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Weather data unavailable for this location",
    )


@router.get("/forecast", response_model=List[WeatherPoint], response_model_by_alias=True)
async def get_forecast(
    lat: float, 
    lng: float,
    hours: int = 24,
    provider: WeatherProvider = Depends(get_weather_provider)
):
    now = datetime.now(timezone.utc)
    try:
        forecast = await provider.get_forecast(lat, lng, now, hours)
    except Exception as e:
        logger.error(f"Weather provider error on /forecast: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Weather service is currently unavailable",
        )

    if forecast and len(forecast) > 0:
        return [_to_weather_point(p) for p in forecast]

    return []
