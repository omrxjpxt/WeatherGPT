from typing import List, Dict
from app.repositories.interfaces.alert_repository import AlertRepository
from app.models.alert import OfficialAlert
from app.core.logging import get_logger

logger = get_logger(__name__)

class FirestoreAlertRepository(AlertRepository):
    def __init__(self, client):
        self.client = client
        self._memory_store: Dict[str, OfficialAlert] = {}
        if not self.client:
            logger.warning("AlertRepository initialized in MEMORY MODE.")
            
    async def save_alert(self, alert: OfficialAlert) -> None:
        if self.client:
            doc_ref = self.client.collection("alerts").document(alert.id)
            await doc_ref.set(alert.model_dump(mode="json"))
        else:
            self._memory_store[alert.id] = alert
            
    async def get_active_alerts(self, location: str) -> List[OfficialAlert]:
        if self.client:
            # Note: actual geo-queries in Firestore require Geohashes.
            # Simplified for MVP.
            docs = await self.client.collection("alerts").get()
            return [OfficialAlert.model_validate(doc.to_dict()) for doc in docs]
        else:
            return list(self._memory_store.values())
