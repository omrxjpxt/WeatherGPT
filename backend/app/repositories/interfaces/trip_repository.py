from abc import ABC, abstractmethod
from typing import List
from app.models.trip import TripResponse
from app.models.user import TripHistorySummary

class TripRepository(ABC):
    @abstractmethod
    async def save_trip_decision(self, uid: str, response: TripResponse) -> None:
        """Persist a trip decision for audit/history under a user."""
        pass
    
    @abstractmethod
    async def get_trip_decision(self, uid: str, analysis_id: str) -> TripResponse | None:
        """Retrieve a past trip decision for a user."""
        pass

    @abstractmethod
    async def get_trip_history(self, uid: str, limit: int = 20) -> List[TripHistorySummary]:
        """Retrieve recent trip decisions summary."""
        pass
