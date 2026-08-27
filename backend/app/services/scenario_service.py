from typing import List
from datetime import datetime

from app.models.trip import TripRequest
from app.models.scenario import ScenarioResult
from app.decision_engine.engine import DecisionEngine
from app.decision_engine.normalized_models import TripContext
from app.services.trip_service import TripService

class ScenarioService:
    def __init__(self, trip_service: TripService):
        self.trip_service = trip_service
        
    async def evaluate_scenarios(self, request: TripRequest, departure_times: List[datetime]) -> List[ScenarioResult]:
        results = []
        for time in departure_times:
            # We would typically cache route/weather fetches here.
            # Using TripService for MVP mock
            req_copy = request.copy(update={"departure_time": time})
            response = await self.trip_service.analyze_trip(req_copy)
            
            results.append(ScenarioResult(
                departure_time=time,
                risk=response.risk,
                estimated_duration=response.estimated_duration,
                recommendation=response.recommendation.body,
                changed_factors=[] # Simplified for MVP
            ))
            
        # The frontend expects them in order of request, ranker could be used if asking for "best"
        return results
