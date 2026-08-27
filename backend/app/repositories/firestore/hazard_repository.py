from typing import List, Dict
from app.repositories.interfaces.hazard_repository import HazardRepository
from app.models.hazard import Hazard
from app.core.logging import get_logger

logger = get_logger(__name__)

class FirestoreHazardRepository(HazardRepository):
    def __init__(self, client):
        self.client = client
        self._memory_store: Dict[str, Hazard] = {}
        if not self.client:
            logger.warning("HazardRepository initialized in MEMORY MODE.")
            
    async def save_hazard(self, hazard: Hazard) -> None:
        if self.client:
            doc_ref = self.client.collection("hazards").document(hazard.id)
            await doc_ref.set(hazard.model_dump(mode="json"))
        else:
            self._memory_store[hazard.id] = hazard
            
    async def get_nearby_hazards(self, lat: float, lng: float, radius_km: float) -> List[Hazard]:
        if self.client:
            docs = await self.client.collection("hazards").get()
            return [Hazard.model_validate(doc.to_dict()) for doc in docs]
        else:
            return list(self._memory_store.values())
