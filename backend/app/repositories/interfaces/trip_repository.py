from abc import ABC, abstractmethod
from app.models.trip import TripResponse

class TripRepository(ABC):
    @abstractmethod
    async def save_trip_decision(self, response: TripResponse) -> None:
        """Persist a trip decision for audit/history."""
        pass
    
    @abstractmethod
    async def get_trip_decision(self, analysis_id: str) -> TripResponse | None:
        """Retrieve a past trip decision."""
        pass
