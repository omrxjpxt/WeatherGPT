import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.api.dependencies import (
    get_trip_service,
    get_assistant_service,
    trip_repository,
    hazard_repository,
    conversation_repository
)
from app.services.trip_service import TripService
from app.services.assistant_service import AssistantService
from app.providers.weather.mock import MockWeatherProvider
from app.providers.routing.mock import MockRoutingProvider
from app.providers.alerts.mock import MockAlertProvider
from app.providers.traffic.mock import MockTrafficProvider
from app.providers.llm.mock import MockLLMProvider
import asyncio


@pytest.fixture(autouse=True)
def override_e2e_services():
    mock_trip_service = TripService(
        weather_provider=MockWeatherProvider(),
        routing_provider=MockRoutingProvider(),
        alert_provider=MockAlertProvider(),
        traffic_provider=MockTrafficProvider(),
        trip_repository=trip_repository,
        hazard_repository=hazard_repository
    )
    mock_assistant_service = AssistantService(
        llm_provider=MockLLMProvider(),
        trip_service=mock_trip_service,
        conversation_repository=conversation_repository
    )
    app.dependency_overrides[get_trip_service] = lambda: mock_trip_service
    app.dependency_overrides[get_assistant_service] = lambda: mock_assistant_service
    yield
    app.dependency_overrides.pop(get_trip_service, None)
    app.dependency_overrides.pop(get_assistant_service, None)


@pytest.mark.asyncio
async def test_e2e_guest_trip_pipeline():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "origin": "Noida Sector 62",
            "destination": "Gurgaon Cyber Hub",
            "departureTime": "2026-08-27T08:00:00Z",
            "mode": "car"
        }
        res = await client.post("/api/v1/trips/analyze", json=payload)
        assert res.status_code == 200
        trip = res.json()
        assert trip["status"] == "success"
        assert trip["risk"]["overallScore"] is not None
        assert len(trip["routes"]) > 0
        # Verification that selected route exists
        selected = [r for r in trip["routes"] if r["evaluation"]["isSelected"]]
        assert len(selected) == 1
        assert "estimatedDuration" in trip


@pytest.mark.asyncio
async def test_e2e_authenticated_trip_and_audit_history_pipeline():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": "Bearer mock-user-e2e-traveler"}
        payload = {
            "origin": "Noida Sector 62",
            "destination": "Gurgaon Cyber Hub",
            "departureTime": "2026-08-27T08:00:00Z",
            "mode": "bike"
        }
        res = await client.post("/api/v1/trips/analyze", json=payload, headers=headers)
        assert res.status_code == 200
        trip = res.json()
        analysis_id = trip["analysisId"]

        # Give background fire-and-forget task a moment
        await asyncio.sleep(0.05)

        # Retrieve user's trip history
        history_res = await client.get("/api/v1/users/me/trips", headers=headers)
        assert history_res.status_code == 200
        history = history_res.json()
        assert any(item["analysisId"] == analysis_id for item in history)

        # Retrieve specific trip snapshot
        detail_res = await client.get(f"/api/v1/users/me/trips/{analysis_id}", headers=headers)
        assert detail_res.status_code == 200
        snapshot = detail_res.json()
        assert snapshot["analysisId"] == analysis_id
        assert snapshot["request"]["mode"] == "bike"


@pytest.mark.asyncio
async def test_e2e_assistant_conversation_continuity_pipeline():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": "Bearer mock-user-assistant-commuter"}

        # Turn 1: Initial user query without conversationId
        turn1_payload = {
            "message": "Plan travel from Noida Sector 62 to Gurgaon Cyber Hub by bike at 8 AM"
        }
        res1 = await client.post("/api/v1/assistant/chat", json=turn1_payload, headers=headers)
        assert res1.status_code == 200
        data1 = res1.json()
        conv_id = data1["conversationId"]
        assert conv_id is not None
        assert len(conv_id) > 0

        await asyncio.sleep(0.05)

        # Check that conversation was saved
        convs_res = await client.get("/api/v1/users/me/conversations", headers=headers)
        assert convs_res.status_code == 200
        convs = convs_res.json()
        assert any(c["id"] == conv_id for c in convs)

        # Turn 2: Follow-up query passing the same conversationId
        turn2_payload = {
            "message": "What is the traffic situation on that route?",
            "conversationId": conv_id,
            "contextOrigin": "Noida Sector 62",
            "contextDestination": "Gurgaon Cyber Hub"
        }
        res2 = await client.post("/api/v1/assistant/chat", json=turn2_payload, headers=headers)
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["conversationId"] == conv_id


@pytest.mark.asyncio
async def test_e2e_saved_route_to_trip_analysis_cycle():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": "Bearer mock-user-saved-route-commuter"}

        # 1. Create a saved route bookmark
        route_payload = {
            "id": "commute-daily-1",
            "name": "Daily Commute to Cyber City",
            "originId": "Noida Sector 62",
            "destinationId": "Gurgaon Cyber Hub"
        }
        save_res = await client.post("/api/v1/users/me/saved-routes", json=route_payload, headers=headers)
        assert save_res.status_code == 200

        # 2. Verify it appears in saved routes
        get_res = await client.get("/api/v1/users/me/saved-routes", headers=headers)
        assert get_res.status_code == 200
        routes = get_res.json()
        matched = next((r for r in routes if r["id"] == "commute-daily-1"), None)
        assert matched is not None

        # 3. Simulate tap-to-analyze by constructing TripRequest from saved route
        trip_payload = {
            "origin": matched["originId"],
            "destination": matched["destinationId"],
            "departureTime": "2026-08-27T08:30:00Z",
            "mode": "car"
        }
        analyze_res = await client.post("/api/v1/trips/analyze", json=trip_payload, headers=headers)
        assert analyze_res.status_code == 200
        trip_data = analyze_res.json()
        assert trip_data["status"] == "success"
        assert trip_data["request"]["origin"] == "Noida Sector 62"

        # 4. Clean up by deleting the saved route
        del_res = await client.delete("/api/v1/users/me/saved-routes/commute-daily-1", headers=headers)
        assert del_res.status_code == 200

        # 5. Verify deletion
        routes_after = (await client.get("/api/v1/users/me/saved-routes", headers=headers)).json()
        assert not any(r["id"] == "commute-daily-1" for r in routes_after)
