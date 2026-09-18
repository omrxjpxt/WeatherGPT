import pytest
from datetime import datetime, timezone, timedelta

from app.models.assistant import (
    AssistantChatRequest,
    AssistantParseRequest,
    UserIntentEnum,
)
from app.models.enums import TransportMode, TripStatus, RiskLevel
from app.services.assistant_service import AssistantService
from app.services.trip_service import TripService
from app.providers.llm.mock import MockLLMProvider
from app.providers.weather.open_meteo import OpenMeteoWeatherProvider
from app.providers.routing.mock import MockRoutingProvider
from app.providers.routing.base import RoutingProvider
from app.providers.routing.errors import ConfigurationError
from app.providers.traffic.mock import MockTrafficProvider
from app.providers.alerts.mock import MockAlertProvider
from app.repositories.mock_hazard_repository import MockHazardRepository


class OfflineRoutingProvider(RoutingProvider):
    @property
    def provider_name(self) -> str:
        return "Offline Routing"

    @property
    def route_status(self):
        from app.models.enums import RouteStatus
        return RouteStatus.unavailable

    async def get_route(self, o_lat, o_lng, d_lat, d_lng, mode):
        raise ConfigurationError("Routing offline")


@pytest.mark.asyncio
async def test_assistant_e2e_successful_hinglish_trip_query():
    """
    End-to-End Controlled Test:
    Hinglish user query: 'Kal 8 baje Noida se Gurgaon bike se jaana hai, baarish ho rahi ho to jaaun?'
    -> Intent Extraction (origin: Noida Sector 62, dest: Gurgaon Cyber Hub, mode: bike, concern: rain)
    -> Validated TripRequest
    -> Authoritative TripService (live Open-Meteo + Mock routing)
    -> DecisionFacts
    -> Grounded LLM Explanation
    -> GroundingValidator
    -> AssistantChatResponse
    """
    trip_service = TripService(
        weather_provider=OpenMeteoWeatherProvider(),
        routing_provider=MockRoutingProvider(route_count=2),
        alert_provider=MockAlertProvider(),
        traffic_provider=MockTrafficProvider(),
        hazard_repository=MockHazardRepository()
    )
    llm_provider = MockLLMProvider()
    service = AssistantService(llm_provider=llm_provider, trip_service=trip_service)

    user_query = "Kal 8 baje Noida se Gurgaon bike se jaana hai, baarish ho rahi ho to jaaun?"
    req = AssistantChatRequest(message=user_query)

    response = await service.chat(req)

    # 1. State assertions
    assert response.status == "success"
    assert response.grounding_fallback_used is False
    assert response.provenance == "demo/mock"

    # 2. Intent assertions
    assert response.intent.origin == "Noida Sector 62"
    assert response.intent.destination == "Gurgaon Cyber Hub"
    assert response.intent.mode == TransportMode.bike
    assert response.intent.weather_concern == "rain"
    assert response.intent.user_intent == UserIntentEnum.trip_decision

    # 3. TripRequest & TripResponse assertions
    assert response.trip_request is not None
    assert response.trip_request.origin == "Noida Sector 62"
    assert response.trip_request.mode == TransportMode.bike
    assert response.trip_response is not None
    assert response.trip_response.status == TripStatus.success
    assert response.trip_response.risk is not None
    assert len(response.trip_response.routes) == 2

    # 4. Grounded Explanation assertions
    assert len(response.message) > 20
    assert "bike" in response.message.lower()
    assert str(response.trip_response.risk.overall_score) in response.message


@pytest.mark.asyncio
async def test_assistant_clarification_without_trip_execution():
    """Incomplete trip query triggers clarification prompt without executing TripService."""
    call_tracker = {"trip_service_called": False}

    class SpyingTripService:
        async def analyze_trip(self, req):
            call_tracker["trip_service_called"] = True
            raise AssertionError("TripService should NOT be called for incomplete intent!")

    service = AssistantService(llm_provider=MockLLMProvider(), trip_service=SpyingTripService())

    # Only origin given
    req = AssistantChatRequest(message="I am in Noida, can I leave?")
    res = await service.chat(req)

    assert res.status == "need_clarification"
    assert res.trip_request is None
    assert res.trip_response is None
    assert res.clarification_prompt is not None
    assert "destination" in res.clarification_prompt.lower() or "travel" in res.clarification_prompt.lower()
    assert call_tracker["trip_service_called"] is False


@pytest.mark.asyncio
async def test_assistant_non_trip_intent_handling():
    """Non-trip queries (weather questions) do not execute TripService and return info status."""
    call_tracker = {"trip_service_called": False}

    class SpyingTripService:
        async def analyze_trip(self, req):
            call_tracker["trip_service_called"] = True
            raise AssertionError("TripService should NOT be called for general weather question!")

    service = AssistantService(llm_provider=MockLLMProvider(), trip_service=SpyingTripService())
    req = AssistantChatRequest(message="What is the weather today?")
    res = await service.chat(req)

    assert res.status == "info"
    assert res.intent.user_intent == UserIntentEnum.weather_question
    assert res.trip_response is None
    assert call_tracker["trip_service_called"] is False
    assert "commute" in res.message.lower() or "route" in res.message.lower()


@pytest.mark.asyncio
async def test_assistant_degraded_routing_grounded_response():
    """When routing fails, explanation transparently acknowledges unavailability without fabricating safety."""
    trip_service = TripService(
        weather_provider=OpenMeteoWeatherProvider(),
        routing_provider=OfflineRoutingProvider(),
        alert_provider=MockAlertProvider(),
        traffic_provider=MockTrafficProvider(),
        hazard_repository=MockHazardRepository()
    )
    service = AssistantService(llm_provider=MockLLMProvider(), trip_service=trip_service)

    req = AssistantChatRequest(message="Noida to Gurgaon by car")
    res = await service.chat(req)

    assert res.status == "degraded"
    assert res.trip_response is not None
    assert res.trip_response.status == TripStatus.routing_unavailable
    # Explanation must state routing unavailability
    assert "routing" in res.message.lower()
    assert "unavailable" in res.message.lower() or "cannot" in res.message.lower()
    assert res.trip_response.risk is None
