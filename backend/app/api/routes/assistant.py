from fastapi import APIRouter, Depends
from app.models.assistant import (
    AssistantParseRequest,
    AssistantParseResponse,
    AssistantChatRequest,
    AssistantChatResponse,
)
from app.services.assistant_service import AssistantService
from app.api.dependencies import get_assistant_service
from app.api.auth import get_current_user
import uuid

router = APIRouter()

@router.post("/parse", response_model=AssistantParseResponse, response_model_by_alias=True)
async def parse_intent(request: AssistantParseRequest, service: AssistantService = Depends(get_assistant_service)):
    return await service.parse_intent(request)

@router.post("/chat", response_model=AssistantChatResponse, response_model_by_alias=True)
async def chat(
    request: AssistantChatRequest, 
    service: AssistantService = Depends(get_assistant_service),
    current_user: dict | None = Depends(get_current_user)
):
    uid = current_user.get("uid") if current_user else None
    conversation_id = request.conversation_id or str(uuid.uuid4())
    return await service.chat(request, uid=uid, conversation_id=conversation_id)
