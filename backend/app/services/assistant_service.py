from app.providers.llm.base import LLMProvider
from app.models.assistant import AssistantParseRequest, AssistantParseResponse, ExtractedIntent

class AssistantService:
    def __init__(self, llm_provider: LLMProvider):
        self.provider = llm_provider
        
    async def parse_intent(self, request: AssistantParseRequest) -> AssistantParseResponse:
        result = await self.provider.extract_intent(request.query)
        
        intent = ExtractedIntent(**result)
        
        # Check completeness
        missing_fields = []
        if not intent.origin: missing_fields.append("origin")
        if not intent.destination: missing_fields.append("destination")
        
        return AssistantParseResponse(
            intent=intent,
            is_complete=len(missing_fields) == 0,
            missing_fields=missing_fields,
            clarification_prompt="Where are you going?" if not intent.destination else None
        )
