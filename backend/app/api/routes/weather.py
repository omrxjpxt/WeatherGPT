from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from datetime import datetime, timezone
import logging

from app.models.weather import WeatherPoint
from app.decision_engine.normalized_models import NormalizedWeatherPoint
from app.api.dependencies import get_weather_provider, get_geocoding_provider
from app.providers.weather.base import WeatherProvider
from app.providers.geocoding.base import GeocodingProvider, GeocodingResolutionError, parse_coordinate_query

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


async def _resolve_coordinates(
    lat: Optional[float],
    lng: Optional[float],
    location: Optional[str],
    geocoding_provider: GeocodingProvider,
) -> tuple[float, float]:
    if lat is not None and lng is not None:
        return lat, lng

    if not location or not location.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either 'location' or both 'lat' and 'lng'.",
        )

    loc_str = location.strip()
    coord_res = parse_coordinate_query(loc_str)
    if coord_res:
        return coord_res.lat, coord_res.lng

    geo_res = await geocoding_provider.geocode(loc_str)
    if not geo_res:
        raise GeocodingResolutionError(
            message=f"Could not resolve location '{loc_str}' with sufficient confidence. Please specify a more detailed landmark, sector, or city.",
            query=loc_str,
            status="unresolved_location",
        )

    conf_score = geo_res.confidence if isinstance(geo_res.confidence, (int, float)) else getattr(geo_res.confidence, "score", 1.0)
    if conf_score < 0.50:
        raise GeocodingResolutionError(
            message=f"Location '{loc_str}' resolved with insufficient confidence ({conf_score:.2f}).",
            query=loc_str,
            status="low_confidence_location",
        )

    return geo_res.lat, geo_res.lng


@router.get("/current", response_model=WeatherPoint, response_model_by_alias=True)
async def get_current_weather(
    lat: Optional[float] = Query(None, description="Latitude"), 
    lng: Optional[float] = Query(None, description="Longitude"),
    location: Optional[str] = Query(None, description="Location text query"),
    provider: WeatherProvider = Depends(get_weather_provider),
    geocoder: GeocodingProvider = Depends(get_geocoding_provider),
):
    target_lat, target_lng = await _resolve_coordinates(lat, lng, location, geocoder)
    now = datetime.now(timezone.utc)
    try:
        forecast = await provider.get_forecast(target_lat, target_lng, now, 1)
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
    lat: Optional[float] = Query(None, description="Latitude"), 
    lng: Optional[float] = Query(None, description="Longitude"),
    location: Optional[str] = Query(None, description="Location text query"),
    hours: int = Query(24, description="Forecast hours"),
    provider: WeatherProvider = Depends(get_weather_provider),
    geocoder: GeocodingProvider = Depends(get_geocoding_provider),
):
    target_lat, target_lng = await _resolve_coordinates(lat, lng, location, geocoder)
    now = datetime.now(timezone.utc)
    try:
        forecast = await provider.get_forecast(target_lat, target_lng, now, hours)
    except Exception as e:
        logger.error(f"Weather provider error on /forecast: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Weather service is currently unavailable",
        )

    if forecast and len(forecast) > 0:
        return [_to_weather_point(p) for p in forecast]

    return []
