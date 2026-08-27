import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data

@pytest.mark.asyncio
async def test_trip_analysis_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/trips/analyze", json={
            "origin": "Noida Sector 62",
            "destination": "Gurgaon Cyber Hub",
            "departureTime": "2026-08-27T08:00:00Z",
            "mode": "bike"
        })
    assert response.status_code == 200
    data = response.json()
    assert "analysisId" in data
    assert "risk" in data
    assert "route" in data
