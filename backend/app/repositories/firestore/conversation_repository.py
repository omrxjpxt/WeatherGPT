from typing import List, Optional, Dict
from datetime import datetime, timezone
import uuid
from app.repositories.interfaces.conversation_repository import ConversationRepository
from app.models.user import ConversationSummary
from app.models.assistant import AssistantChatResponse, AssistantChatRequest
from app.core.logging import get_logger

logger = get_logger(__name__)

class FirestoreConversationRepository(ConversationRepository):
    def __init__(self, client):
        self.client = client
        # In-memory fallback: dict of uid -> dict of conv_id -> ConversationSummary
        self._memory_summaries: Dict[str, Dict[str, ConversationSummary]] = {}
        # We don't implement full message in-memory fallback for prototype since it's fire-and-forget
        if not self.client:
            logger.warning("ConversationRepository initialized in MEMORY MODE.")

    async def get_conversations(self, uid: str) -> List[ConversationSummary]:
        if self.client:
            docs = await self.client.collection("users").document(uid).collection("conversations").order_by("updatedAt", direction="DESCENDING").get()
            return [ConversationSummary.model_validate(doc.to_dict()) for doc in docs]
        else:
            convs = self._memory_summaries.get(uid, {})
            return list(convs.values())

    async def save_message(self, uid: str, conversation_id: str, request: AssistantChatRequest, response: AssistantChatResponse) -> None:
        if self.client:
            now = datetime.now(timezone.utc)
            # Create or update conversation summary
            conv_ref = self.client.collection("users").document(uid).collection("conversations").document(conversation_id)
            
            trip_id = response.trip_response.analysis_id if response.trip_response else ""
            
            # Use set with merge=True to act as upsert
            await conv_ref.set({
                "id": conversation_id,
                "uid": uid,
                "title": request.message[:50] + ("..." if len(request.message) > 50 else ""),
                "trip_id": trip_id,
                "updatedAt": now
            }, merge=True)
            
            # Append user message
            user_msg_id = str(uuid.uuid4())
            await conv_ref.collection("messages").document(user_msg_id).set({
                "id": user_msg_id,
                "sender": "user",
                "content": request.message,
                "createdAt": now
            })
            
            # Append assistant response
            ast_msg_id = str(uuid.uuid4())
            await conv_ref.collection("messages").document(ast_msg_id).set({
                "id": ast_msg_id,
                "sender": "assistant",
                "content": response.message,
                "tripAnalysisId": trip_id,
                "status": response.status,
                "provenance": response.provenance,
                "createdAt": now
            })
        else:
            if uid not in self._memory_summaries:
                self._memory_summaries[uid] = {}
            if conversation_id not in self._memory_summaries[uid]:
                self._memory_summaries[uid][conversation_id] = ConversationSummary(
                    id=conversation_id,
                    trip_id=response.trip_response.analysis_id if response.trip_response else "",
                    title=request.message[:50],
                    created_at=datetime.now(timezone.utc)
                )

    async def delete_conversation(self, uid: str, conversation_id: str) -> None:
        if self.client:
            await self.client.collection("users").document(uid).collection("conversations").document(conversation_id).delete()
            # Note: in a real production environment, you'd need a recursive delete for subcollections
        else:
            if uid in self._memory_summaries and conversation_id in self._memory_summaries[uid]:
                del self._memory_summaries[uid][conversation_id]
