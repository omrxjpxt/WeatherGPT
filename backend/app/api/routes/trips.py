from fastapi import APIRouter, Depends
from app.models.trip import TripRequest, TripResponse
from app.services.trip_service import TripService
from app.api.dependencies import get_trip_service

router = APIRouter()

@router.post("/analyze", response_model=TripResponse, response_model_by_alias=True)
async def analyze_trip(request: TripRequest, service: TripService = Depends(get_trip_service)):
    return await service.analyze_trip(request)
