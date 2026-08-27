from typing import List
from fastapi import APIRouter, Depends
from app.models.alert import OfficialAlert
from app.api.dependencies import get_alert_provider
from app.providers.alerts.base import AlertProvider

router = APIRouter()

@router.get("/", response_model=List[OfficialAlert], response_model_by_alias=True)
async def get_alerts(
    lat: float, 
    lng: float,
    provider: AlertProvider = Depends(get_alert_provider)
):
    return await provider.get_active_alerts(lat, lng)
