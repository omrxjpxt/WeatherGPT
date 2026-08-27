from abc import ABC, abstractmethod
from typing import Dict, Any

class LLMProvider(ABC):
    @abstractmethod
    async def extract_intent(self, text: str) -> Dict[str, Any]:
        """Extract structured intent from natural language text."""
        pass
    
    @abstractmethod
    async def generate_explanation(self, decision_facts: Dict[str, Any]) -> str:
        """Generate human-readable explanation from structured decision facts."""
        pass
