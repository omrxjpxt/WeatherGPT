from abc import ABC, abstractmethod
from typing import List
from app.decision_engine.normalized_models import NormalizedRouteSegment

class TrafficProvider(ABC):
    @abstractmethod
    async def get_traffic_factors(self, segments: List[NormalizedRouteSegment]) -> List[float]:
        """Returns traffic congestion factor for each segment (1.0 = normal, >1.0 = congested)."""
        pass
