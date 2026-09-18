from abc import ABC, abstractmethod
from typing import List, Optional
from app.models.user import ConversationSummary
from app.models.assistant import AssistantChatResponse, AssistantChatRequest

class ConversationRepository(ABC):
    @abstractmethod
    async def get_conversations(self, uid: str) -> List[ConversationSummary]:
        """Retrieve a list of past conversations for a user."""
        pass

    @abstractmethod
    async def save_message(self, uid: str, conversation_id: str, request: AssistantChatRequest, response: AssistantChatResponse) -> None:
        """Save a new message interaction in a conversation."""
        pass
    
    @abstractmethod
    async def delete_conversation(self, uid: str, conversation_id: str) -> None:
        """Delete an entire conversation."""
        pass
