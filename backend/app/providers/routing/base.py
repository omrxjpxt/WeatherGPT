from abc import ABC, abstractmethod
from typing import List
from app.models.enums import TransportMode, RouteStatus
from app.decision_engine.normalized_models import NormalizedRoute

class RoutingProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the routing provider."""
        pass
        
    @property
    @abstractmethod
    def route_status(self) -> RouteStatus:
        """Status of the last provided route (live, cached, mock, unavailable)."""
        pass

    @abstractmethod
    async def get_route(self, origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float, mode: TransportMode) -> List[NormalizedRoute]:
        """Get route(s) between coordinates for mode."""
        pass
