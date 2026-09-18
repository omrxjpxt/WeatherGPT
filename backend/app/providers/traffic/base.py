from abc import ABC, abstractmethod
from datetime import datetime
from app.models.enums import TransportMode, TrafficStatus
from app.models.traffic import TrafficSnapshot
from app.decision_engine.normalized_models import NormalizedRoute

class TrafficProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the traffic provider."""
        pass

    @property
    @abstractmethod
    def traffic_status(self) -> TrafficStatus:
        """Current operational status of the traffic provider."""
        pass

    @abstractmethod
    async def get_traffic_for_route(
        self,
        route: NormalizedRoute,
        departure_time: datetime,
        mode: TransportMode
    ) -> TrafficSnapshot:
        """
        Retrieves normalized traffic data for a given route, departure time, and mode.
        If traffic is unavailable, returns a TrafficSnapshot with status=TrafficStatus.unavailable.
        """
        pass
