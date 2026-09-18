import os
import json
from typing import Dict, Any, Optional
from datetime import datetime

from app.core.config import settings
from app.providers.llm.base import LLMProvider
from app.providers.routing.errors import ConfigurationError


class GeminiLLMProvider(LLMProvider):
    """
    Google Gemini LLM Provider adapter.
    Implements structured intent extraction and grounded explanation generation.
    Cleanly separates provider SDK interactions from domain services.
    """

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or settings.llm_api_key or os.environ.get("GEMINI_API_KEY")
        if not self._api_key:
            raise ConfigurationError("GEMINI_API_KEY is not configured in the environment.")

    @property
    def provider_name(self) -> str:
        return "Google Gemini LLM"

    @property
    def provenance(self) -> str:
        return "gemini/live"

    async def extract_intent(self, text: str, reference_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Extract structured intent using Gemini API with structured JSON output.
        """
        try:
            import google.generativeai as genai
            genai.configure(api_key=self._api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            prompt = (
                f"You are a trip assistant intent parser. Extract structured trip information from this user text: '{text}'.\n"
                "Return ONLY a valid JSON object matching this schema:\n"
                "{\n"
                '  "origin": string or null,\n'
                '  "destination": string or null,\n'
                '  "departure_time": ISO-8601 string or null,\n'
                '  "arrival_deadline": ISO-8601 string or null,\n'
                '  "mode": "bike" | "car" | "metro" | "walk" | null,\n'
                '  "trip_date": string or null,\n'
                '  "user_intent": "trip_decision" | "weather_question" | "route_comparison" | "what_if" | "alert_question" | "general_weather",\n'
                '  "weather_concern": string or null,\n'
                '  "scenario_modifiers": list of strings,\n'
                '  "raw_query": string\n'
                "}\n"
                "Do not hallucinate or invent missing fields. If a field is not specified, return null."
            )
            response = await model.generate_content_async(prompt)
            return json.loads(response.text)
        except Exception as e:
            raise RuntimeError(f"Gemini intent extraction failed: {str(e)}")

    async def generate_explanation(self, decision_facts: Dict[str, Any]) -> str:
        """
        Generate grounded explanation using Gemini API, strictly adhering to decision facts.
        """
        try:
            import google.generativeai as genai
            genai.configure(api_key=self._api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")

            system_instruction = (
                "You are WeatherGPT's natural language communicator. Your task is to explain trip decisions to travelers.\n"
                "CRITICAL GROUNDING RULES:\n"
                "1. You MUST ONLY use the facts provided in the JSON input.\n"
                "2. Do NOT invent temperatures, precipitation amounts, or traffic delays not listed in the facts.\n"
                "3. Do NOT invent routes, road closures, or alerts.\n"
                "4. If status is 'routing_unavailable', you must state that route navigation data is currently unavailable.\n"
                "5. Never tell the user a trip is safe if routing or weather is unavailable.\n"
                "Be concise, friendly, and transparent about data limitations."
            )
            prompt = f"{system_instruction}\n\nDecision Facts:\n{json.dumps(decision_facts, default=str)}"
            response = await model.generate_content_async(prompt)
            return response.text.strip()
        except Exception as e:
            raise RuntimeError(f"Gemini explanation generation failed: {str(e)}")
