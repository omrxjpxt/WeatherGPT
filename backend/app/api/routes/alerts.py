from typing import List
from fastapi import APIRouter
from app.models.alert import OfficialAlert

router = APIRouter()

@router.get("/", response_model=List[OfficialAlert], response_model_by_alias=True)
async def get_alerts(lat: float, lng: float):
    # Dummy mock
    return []
