from fastapi import APIRouter, Depends
from app.models.assistant import (
    AssistantParseRequest,
    AssistantParseResponse,
    AssistantChatRequest,
    AssistantChatResponse,
)
from app.services.assistant_service import AssistantService
from app.api.dependencies import get_assistant_service

router = APIRouter()


@router.post("/parse", response_model=AssistantParseResponse, response_model_by_alias=True)
async def parse_intent(request: AssistantParseRequest, service: AssistantService = Depends(get_assistant_service)):
    return await service.parse_intent(request)


@router.post("/chat", response_model=AssistantChatResponse, response_model_by_alias=True)
async def chat(request: AssistantChatRequest, service: AssistantService = Depends(get_assistant_service)):
    return await service.chat(request)
