from fastapi import APIRouter, Depends
from typing import List

from app.decision_engine.normalized_models import NormalizedHazard
from app.repositories.mock_hazard_repository import MockHazardRepository
from app.api.dependencies import get_hazard_repository

router = APIRouter()

@router.get("/", response_model=List[NormalizedHazard])
async def get_hazards(
    min_lat: float = 8.0,
    min_lng: float = 68.0,
    max_lat: float = 37.0,
    max_lng: float = 97.0,
    hazard_repo: MockHazardRepository = Depends(get_hazard_repository),
):
    """
    Returns hazards within a bounding box. 
    Defaults to rough bounds of India.
    """
    return await hazard_repo.get_hazards_in_region(min_lat, min_lng, max_lat, max_lng)
