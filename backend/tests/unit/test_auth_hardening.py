import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.models.user import UserProfile, SavedRoute


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_protected_endpoints_require_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # GET /api/v1/users/me/profile without auth
        res = await client.get("/api/v1/users/me/profile")
        assert res.status_code == 401
        assert "Missing Authorization header" in res.json()["detail"]

        # GET /api/v1/users/me/saved-routes without auth
        res = await client.get("/api/v1/users/me/saved-routes")
        assert res.status_code == 401

        # GET /api/v1/users/me/trips without auth
        res = await client.get("/api/v1/users/me/trips")
        assert res.status_code == 401

        # GET /api/v1/users/me/conversations without auth
        res = await client.get("/api/v1/users/me/conversations")
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoints_reject_malformed_and_expired_tokens():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Malformed scheme
        res = await client.get("/api/v1/users/me/profile", headers={"Authorization": "Token 12345"})
        assert res.status_code == 401
        assert "must be Bearer" in res.json()["detail"]

        # Expired token
        res = await client.get("/api/v1/users/me/profile", headers={"Authorization": "Bearer expired-token"})
        assert res.status_code == 401
        assert "expired" in res.json()["detail"].lower()

        # Malformed token
        res = await client.get("/api/v1/users/me/profile", headers={"Authorization": "Bearer malformed-token"})
        assert res.status_code == 401
        assert "malformed" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_public_endpoints_allow_guest_users():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # POST /api/v1/trips/analyze without auth header
        payload = {
            "origin": "Noida Sector 62",
            "destination": "Gurgaon Cyber Hub",
            "departureTime": "2026-08-27T08:00:00Z",
            "mode": "bike"
        }
        res = await client.post("/api/v1/trips/analyze", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "analysisId" in data
        assert "status" in data

        # POST /api/v1/assistant/chat without auth header
        chat_payload = {
            "message": "Plan a commute from Noida Sector 62 to Gurgaon Cyber Hub by bike"
        }
        res = await client.post("/api/v1/assistant/chat", json=chat_payload)
        assert res.status_code == 200
        chat_data = res.json()
        assert "message" in chat_data
        assert "conversationId" in chat_data


@pytest.mark.asyncio
async def test_uid_spoofing_prevention_on_profile_update():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": "Bearer mock-user-alice"}
        
        # Attacker tries to submit a profile update with bob's UID in body
        spoofed_payload = {
            "uid": "victim-bob-uid",
            "email": "alice@example.com",
            "displayName": "Alice In Wonderland",
            "homeAddress": "Noida Sector 62",
            "defaultMode": "bike"
        }
        res = await client.put("/api/v1/users/me/profile", json=spoofed_payload, headers=headers)
        assert res.status_code == 200
        updated = res.json()
        # Verified token identity MUST overwrite spoofed body UID
        assert updated["uid"] == "mock-user-alice"


@pytest.mark.asyncio
async def test_cross_user_isolation_between_accounts():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        alice_headers = {"Authorization": "Bearer mock-user-alice"}
        bob_headers = {"Authorization": "Bearer mock-user-bob"}

        # Alice saves a route
        route_payload = {
            "id": "alice-route-1",
            "name": "Alice's Daily Commute",
            "originId": "Noida Sector 62",
            "destinationId": "Connaught Place"
        }
        res = await client.post("/api/v1/users/me/saved-routes", json=route_payload, headers=alice_headers)
        assert res.status_code == 200

        # Alice sees her route
        alice_routes = (await client.get("/api/v1/users/me/saved-routes", headers=alice_headers)).json()
        assert any(r["id"] == "alice-route-1" for r in alice_routes)

        # Bob CANNOT see Alice's route
        bob_routes = (await client.get("/api/v1/users/me/saved-routes", headers=bob_headers)).json()
        assert not any(r["id"] == "alice-route-1" for r in bob_routes)

        # Bob attempts to delete Alice's route
        await client.delete("/api/v1/users/me/saved-routes/alice-route-1", headers=bob_headers)

        # Alice's route remains intact
        alice_routes_after = (await client.get("/api/v1/users/me/saved-routes", headers=alice_headers)).json()
        assert any(r["id"] == "alice-route-1" for r in alice_routes_after)
