import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_lightweight_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert "service" in data
        assert "version" in data
        assert "timestamp" in data


@pytest.mark.asyncio
async def test_readiness_probe_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for path in ("/api/v1/ready", "/api/v1/health/ready"):
            res = await client.get(path)
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "ready"
            assert "checks" in data
            checks = data["checks"]
            assert checks["config"] == "ok"
            assert "weather_provider" in checks
            assert "geocoding_provider" in checks
            assert "routing_provider" in checks
            assert "alert_provider" in checks
            assert "http_pool" in checks
            assert "database" in checks



@pytest.mark.asyncio
async def test_readiness_probe_fails_when_production_dependency_missing(monkeypatch):
    import app.api.dependencies as deps

    # Simulate production environment with missing database
    orig_env = settings.environment
    orig_db = deps.firestore_client
    try:
        settings.environment = "production"
        deps.firestore_client = None

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.get("/api/v1/ready")
            assert res.status_code == 503
            data = res.json()
            assert data["status"] == "not_ready"
            assert data["checks"]["database"]["status"] == "disconnected"
    finally:
        settings.environment = orig_env
        deps.firestore_client = orig_db
