from abc import ABC, abstractmethod
from typing import List
from app.decision_engine.normalized_models import NormalizedAlert

class AlertProvider(ABC):
    @abstractmethod
    async def get_active_alerts(self, lat: float, lng: float) -> List[NormalizedAlert]:
        """Fetch active alerts for a location."""
        pass
