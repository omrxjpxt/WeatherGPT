from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime


class LLMProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the LLM provider for provenance tracking."""
        pass

    @property
    @abstractmethod
    def provenance(self) -> str:
        """Provenance string (e.g. 'demo/mock', 'gemini/live')."""
        pass

    @abstractmethod
    async def extract_intent(self, text: str, reference_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Extract structured intent dictionary from natural language text.
        Returns dictionary containing candidate fields (origin, destination, departure_time, mode, etc.).
        Unmentioned fields must be set to None.
        """
        pass

    @abstractmethod
    async def generate_explanation(self, decision_facts: Dict[str, Any]) -> str:
        """
        Generate human-readable natural language explanation strictly grounded
        in the provided DecisionFacts dictionary.
        """
        pass
