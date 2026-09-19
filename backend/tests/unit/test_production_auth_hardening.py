import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings
from app.api.auth import get_authenticated_user


class DummyReq:
    def __init__(self, headers=None):
        self.headers = headers or {}


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_production_mode_strictly_rejects_mock_tokens():
    # Simulate production environment
    original_env = settings.environment
    try:
        settings.environment = "production"
        assert settings.is_production is True

        req_mock = DummyReq(headers={"Authorization": "Bearer mock-user-om"})
        with pytest.raises(Exception) as exc_info:
            await get_authenticated_user(req_mock)

        assert exc_info.value.status_code == 401
        assert "invalid, malformed, or expired" in exc_info.value.detail.lower()

        req_test = DummyReq(headers={"Authorization": "Bearer test-token"})
        with pytest.raises(Exception) as exc_info_test:
            await get_authenticated_user(req_test)

        assert exc_info_test.value.status_code == 401
        assert "invalid, malformed, or expired" in exc_info_test.value.detail.lower()
    finally:
        settings.environment = original_env


@pytest.mark.asyncio
async def test_protected_endpoints_clean_401_no_stack_trace_leak():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Invalid JWT token
        res = await client.get("/api/v1/users/me/profile", headers={"Authorization": "Bearer not-a-real-jwt"})
        assert res.status_code == 401
        body = res.json()
        assert "detail" in body
        # Ensure clean generic message without stack trace, Python paths, or internal exception objects
        assert body["detail"] == "Invalid, malformed, or expired authentication token"
        assert "traceback" not in str(body).lower()
        assert "firebase" not in str(body).lower()
        assert "cryptography" not in str(body).lower()


@pytest.mark.asyncio
async def test_cross_user_isolation_blocks_writes_and_deletes():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        user1_headers = {"Authorization": "Bearer mock-user-user1"}
        user2_headers = {"Authorization": "Bearer mock-user-user2"}

        # User 1 creates a saved route
        route_payload = {
            "id": "user1-route-abc",
            "name": "User 1 Highway Route",
            "originId": "Noida",
            "destinationId": "Delhi"
        }
        res_create = await client.post("/api/v1/users/me/saved-routes", json=route_payload, headers=user1_headers)
        assert res_create.status_code == 200

        # User 2 attempts to delete User 1's route (should not affect User 1)
        res_del = await client.delete("/api/v1/users/me/saved-routes/user1-route-abc", headers=user2_headers)
        assert res_del.status_code == 200

        # Verify User 1's route still exists
        res_get = await client.get("/api/v1/users/me/saved-routes", headers=user1_headers)
        assert res_get.status_code == 200
        user1_routes = res_get.json()
        assert any(r["id"] == "user1-route-abc" for r in user1_routes)

        # User 2 must NOT see User 1's route
        res_u2_get = await client.get("/api/v1/users/me/saved-routes", headers=user2_headers)
        assert res_u2_get.status_code == 200
        user2_routes = res_u2_get.json()
        assert not any(r["id"] == "user1-route-abc" for r in user2_routes)
