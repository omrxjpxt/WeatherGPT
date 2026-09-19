import pytest
import asyncio
from datetime import datetime, timezone
from app.services.trip_service import TripService
from app.services.assistant_service import AssistantService
from app.models.trip import TripRequest
from app.models.assistant import AssistantChatRequest
from app.models.enums import TransportMode, TripStatus
from app.providers.weather.mock import MockWeatherProvider
from app.providers.routing.mock import MockRoutingProvider
from app.providers.alerts.mock import MockAlertProvider
from app.providers.traffic.mock import MockTrafficProvider
from app.providers.llm.mock import MockLLMProvider
from app.repositories.interfaces.trip_repository import TripRepository
from app.repositories.interfaces.conversation_repository import ConversationRepository


class FailingTripRepository(TripRepository):
    """Simulates a database outage or timeout during save operations."""
    async def save_trip_decision(self, uid: str, response):
        raise ConnectionError("Simulated Firestore timeout / connection failure")

    async def get_trip_decision(self, uid: str, analysis_id: str):
        return None

    async def get_trip_history(self, uid: str, limit: int = 20):
        return []


class FailingConversationRepository(ConversationRepository):
    """Simulates a database failure during message persistence."""
    async def save_message(self, uid: str, conversation_id: str, request, response):
        raise TimeoutError("Simulated Firestore write timeout")

    async def get_conversations(self, uid: str):
        return []

    async def delete_conversation(self, uid: str, conversation_id: str):
        pass


@pytest.fixture
def trip_service_with_failing_db():
    return TripService(
        weather_provider=MockWeatherProvider(),
        routing_provider=MockRoutingProvider(),
        alert_provider=MockAlertProvider(),
        traffic_provider=MockTrafficProvider(),
        trip_repository=FailingTripRepository()
    )


@pytest.fixture
def assistant_service_with_failing_db(trip_service_with_failing_db):
    return AssistantService(
        llm_provider=MockLLMProvider(),
        trip_service=trip_service_with_failing_db,
        conversation_repository=FailingConversationRepository()
    )


@pytest.mark.asyncio
async def test_trip_analysis_succeeds_even_when_database_fails(trip_service_with_failing_db):
    req = TripRequest(
        origin="Noida Sector 62",
        destination="Gurgaon Cyber Hub",
        departure_time=datetime(2026, 8, 27, 8, 0, tzinfo=timezone.utc),
        mode=TransportMode.car
    )

    # Invoke with an authenticated user UID
    res = await trip_service_with_failing_db.analyze_trip(req, uid="authenticated-user-123")

    # Give any background tasks a moment to execute their safe error handling
    await asyncio.sleep(0.05)

    # Invariant: DB failure MUST NOT alter or block the authoritative decision
    assert res is not None
    assert res.status == TripStatus.success
    assert res.risk is not None
    assert 0 <= res.risk.overall_score <= 100
    assert res.recommendation is not None
    assert len(res.routes) > 0
    assert any(r.evaluation.is_selected for r in res.routes)


@pytest.mark.asyncio
async def test_assistant_chat_succeeds_even_when_conversation_database_fails(assistant_service_with_failing_db):
    chat_req = AssistantChatRequest(
        message="I need to go from Noida Sector 62 to Gurgaon Cyber Hub by bike at 8 AM",
        conversation_id="conv-session-123"
    )

    res = await assistant_service_with_failing_db.chat(
        chat_req,
        uid="authenticated-user-123",
        conversation_id="conv-session-123"
    )

    await asyncio.sleep(0.05)

    # Invariant: Message failure MUST NOT crash the conversation response
    assert res is not None
    assert res.status == "success"
    assert res.message is not None
    assert len(res.message) > 0
    assert res.conversation_id == "conv-session-123"
    assert res.trip_response is not None
    assert res.trip_response.status == TripStatus.success
