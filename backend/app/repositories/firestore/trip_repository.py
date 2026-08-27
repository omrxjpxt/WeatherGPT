from typing import Dict, Optional
from app.repositories.interfaces.trip_repository import TripRepository
from app.models.trip import TripResponse
from app.core.logging import get_logger

logger = get_logger(__name__)

class FirestoreTripRepository(TripRepository):
    def __init__(self, client):
        self.client = client
        # In-memory fallback
        self._memory_store: Dict[str, TripResponse] = {}
        if not self.client:
            logger.warning("TripRepository initialized in MEMORY MODE. Data will be lost on restart.")
            
    async def save_trip_decision(self, response: TripResponse) -> None:
        if self.client:
            # Firestore implementation
            doc_ref = self.client.collection("trip_decisions").document(response.analysis_id)
            await doc_ref.set(response.model_dump(mode="json"))
        else:
            self._memory_store[response.analysis_id] = response
            logger.info("Saved trip decision to memory store", analysis_id=response.analysis_id)
            
    async def get_trip_decision(self, analysis_id: str) -> Optional[TripResponse]:
        if self.client:
            doc_ref = self.client.collection("trip_decisions").document(analysis_id)
            doc = await doc_ref.get()
            if doc.exists:
                return TripResponse.model_validate(doc.to_dict())
            return None
        else:
            return self._memory_store.get(analysis_id)
