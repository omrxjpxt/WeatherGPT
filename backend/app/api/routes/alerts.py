from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from app.models.alert import OfficialAlert
from app.api.dependencies import get_alert_provider, get_geocoding_provider
from app.providers.alerts.base import AlertProvider
from app.providers.geocoding.base import GeocodingProvider
from app.api.routes.weather import _resolve_coordinates

router = APIRouter()

@router.get("/", response_model=List[OfficialAlert], response_model_by_alias=True)
async def get_alerts(
    lat: Optional[float] = Query(None, description="Latitude for alerts query"), 
    lng: Optional[float] = Query(None, description="Longitude for alerts query"),
    location: Optional[str] = Query(None, description="Location name or address to geocode for alerts query"),
    provider: AlertProvider = Depends(get_alert_provider),
    geocoding_provider: GeocodingProvider = Depends(get_geocoding_provider),
):
    res_lat, res_lng = await _resolve_coordinates(lat, lng, location, geocoding_provider)
    return await provider.get_active_alerts(res_lat, res_lng)

