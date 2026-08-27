import asyncio
from typing import Dict, Any
from app.providers.llm.base import LLMProvider

class MockLLMProvider(LLMProvider):
    async def extract_intent(self, text: str) -> Dict[str, Any]:
        await asyncio.sleep(0.2)
        # In a real implementation, this parses the text.
        # Mock behavior returns a structured intent.
        return {
            "origin": "Noida Sector 62",
            "destination": "Gurgaon Cyber Hub",
            "departure_time": None, # leave to caller to set default
            "mode": "bike"
        }
    
    async def generate_explanation(self, decision_facts: Dict[str, Any]) -> str:
        await asyncio.sleep(0.2)
        return "Based on your route and expected weather conditions, there is a high risk of heavy rainfall and waterlogging."
