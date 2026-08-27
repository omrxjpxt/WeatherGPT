from typing import List
from abc import ABC, abstractmethod
from app.decision_engine.normalized_models import NormalizedHazard

class HazardRepository(ABC):
    @abstractmethod
    async def get_hazards_in_region(self, min_lat: float, min_lng: float, max_lat: float, max_lng: float) -> List[NormalizedHazard]:
        pass
