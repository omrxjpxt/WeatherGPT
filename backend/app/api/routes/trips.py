from fastapi import APIRouter, Depends, Request
from app.models.trip import TripRequest, TripResponse
from app.services.trip_service import TripService
from app.api.dependencies import get_trip_service
from app.api.auth import get_optional_current_user

router = APIRouter()

@router.post("/analyze", response_model=TripResponse, response_model_by_alias=True)
async def analyze_trip(
    request: TripRequest, 
    service: TripService = Depends(get_trip_service),
    current_user: dict | None = Depends(get_optional_current_user)
):
    uid = current_user.get("uid") if current_user else None
    return await service.analyze_trip(request, uid=uid)
