from abc import ABC, abstractmethod
from typing import List
from app.models.alert import OfficialAlert

class AlertRepository(ABC):
    @abstractmethod
    async def save_alert(self, alert: OfficialAlert) -> None:
        pass
    
    @abstractmethod
    async def get_active_alerts(self, location: str) -> List[OfficialAlert]:
        pass
