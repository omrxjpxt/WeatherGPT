from abc import ABC, abstractmethod
from typing import List
from app.models.hazard import Hazard

class HazardRepository(ABC):
    @abstractmethod
    async def save_hazard(self, hazard: Hazard) -> None:
        pass
    
    @abstractmethod
    async def get_nearby_hazards(self, lat: float, lng: float, radius_km: float) -> List[Hazard]:
        pass
