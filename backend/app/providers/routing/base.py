from abc import ABC, abstractmethod
from typing import List
from app.models.enums import TransportMode
from app.decision_engine.normalized_models import NormalizedRoute

class RoutingProvider(ABC):
    @abstractmethod
    async def get_route(self, origin: str, destination: str, mode: TransportMode) -> NormalizedRoute:
        """Get best route between origin and destination for mode."""
        pass
