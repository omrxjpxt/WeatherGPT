from abc import ABC, abstractmethod
from typing import List
from app.decision_engine.normalized_models import NormalizedAlert

class AlertProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the alert provider."""
        pass
        
    @property
    @abstractmethod
    def provider_class(self) -> str:
        """Class of the alert provider (e.g. authoritative, secondary, demo)."""
        pass

    @abstractmethod
    async def get_active_alerts(self, lat: float, lng: float) -> List[NormalizedAlert]:
        """Fetch active alerts for a location."""
        pass
