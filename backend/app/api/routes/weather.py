from typing import List
from fastapi import APIRouter
from app.models.weather import WeatherPoint

router = APIRouter()

@router.get("/current", response_model=WeatherPoint, response_model_by_alias=True)
async def get_current_weather(lat: float, lng: float):
    # Dummy implementation for MVP mock
    from datetime import datetime, timezone
    return WeatherPoint(
        time=datetime.now(timezone.utc),
        temperature=31.0,
        precipitation=0.0,
        humidity=78,
        wind_speed=12.0,
        condition="Partly Cloudy",
        icon="⛅"
    )

@router.get("/forecast", response_model=List[WeatherPoint], response_model_by_alias=True)
async def get_forecast(lat: float, lng: float):
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    return [
        WeatherPoint(
            time=now + timedelta(hours=i),
            temperature=31.0,
            precipitation=0.0,
            humidity=78,
            wind_speed=12.0,
            condition="Partly Cloudy",
            icon="⛅"
        ) for i in range(12)
    ]
