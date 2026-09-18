from typing import Dict, Optional, List, Any
from datetime import datetime, timezone
from app.repositories.interfaces.trip_repository import TripRepository
from app.models.trip import TripResponse
from app.models.user import TripHistorySummary
from app.core.logging import get_logger

logger = get_logger(__name__)

class FirestoreTripRepository(TripRepository):
    def __init__(self, client):
        self.client = client
        # In-memory fallback: dict of uid -> dict of analysis_id -> dict {"createdAt": datetime, "response": TripResponse}
        self._memory_store: Dict[str, Dict[str, Dict[str, Any]]] = {}
        if not self.client:
            logger.warning("TripRepository initialized in MEMORY MODE. Data will be lost on restart.")
            
    async def save_trip_decision(self, uid: str, response: TripResponse) -> None:
        # Inject timestamp for sorting history
        data = response.model_dump(mode="json")
        now = datetime.now(timezone.utc)
        data["createdAt"] = now.isoformat()
        
        if self.client:
            # Firestore implementation
            doc_ref = self.client.collection("users").document(uid).collection("trips").document(response.analysis_id)
            await doc_ref.set(data)
        else:
            if uid not in self._memory_store:
                self._memory_store[uid] = {}
            # store wrapped in a dict instead of modifying Pydantic model
            self._memory_store[uid][response.analysis_id] = {
                "createdAt": now,
                "response": response
            }
            logger.info("Saved trip decision to memory store", uid=uid, analysis_id=response.analysis_id)
            
    async def get_trip_decision(self, uid: str, analysis_id: str) -> Optional[TripResponse]:
        if self.client:
            doc_ref = self.client.collection("users").document(uid).collection("trips").document(analysis_id)
            doc = await doc_ref.get()
            if doc.exists:
                return TripResponse.model_validate(doc.to_dict())
            return None
        else:
            record = self._memory_store.get(uid, {}).get(analysis_id)
            if record:
                return record["response"]
            return None

    async def get_trip_history(self, uid: str, limit: int = 20) -> List[TripHistorySummary]:
        history = []
        if self.client:
            docs = await self.client.collection("users").document(uid).collection("trips").order_by("createdAt", direction="DESCENDING").limit(limit).get()
            for doc in docs:
                data = doc.to_dict()
                req = data.get("request", {})
                risk = data.get("risk", {})
                rec = data.get("recommendation", {})
                created_at_str = data.get("createdAt", datetime.now(timezone.utc).isoformat())
                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                history.append(TripHistorySummary(
                    analysis_id=data.get("analysis_id", ""),
                    status=data.get("status", "success"),
                    origin=req.get("origin", "Unknown"),
                    destination=req.get("destination", "Unknown"),
                    mode=req.get("mode", "car"),
                    risk_level=risk.get("level") if risk else None,
                    recommendation_headline=rec.get("headline") if rec else None,
                    created_at=created_at
                ))
        else:
            records = list(self._memory_store.get(uid, {}).values())
            # sort by createdAt
            records.sort(key=lambda x: x["createdAt"], reverse=True)
            for record in records[:limit]:
                trip = record["response"]
                history.append(TripHistorySummary(
                    analysis_id=trip.analysis_id,
                    status=trip.status.value if hasattr(trip.status, "value") else str(trip.status),
                    origin=trip.request.origin,
                    destination=trip.request.destination,
                    mode=trip.request.mode.value if hasattr(trip.request.mode, "value") else str(trip.request.mode),
                    risk_level=(trip.risk.level.value if hasattr(trip.risk.level, "value") else str(trip.risk.level)) if trip.risk else None,
                    recommendation_headline=trip.recommendation.headline if trip.recommendation else None,
                    created_at=record["createdAt"]
                ))
        return history
