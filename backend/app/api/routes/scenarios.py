from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.models.trip import TripRequest
from app.models.scenario import ScenarioResult
from app.services.scenario_service import ScenarioService
from app.api.dependencies import get_scenario_service

router = APIRouter()

class EvaluateScenariosRequest(BaseModel):
    request: TripRequest
    departure_times: List[datetime]

@router.post("/evaluate", response_model=List[ScenarioResult], response_model_by_alias=True)
async def evaluate_scenarios(
    req: EvaluateScenariosRequest,
    service: ScenarioService = Depends(get_scenario_service)
):
    return await service.evaluate_scenarios(req.request, req.departure_times)
