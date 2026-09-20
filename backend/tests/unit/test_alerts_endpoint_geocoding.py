import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_alerts_endpoint_with_location_string():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/alerts/?location=Gurgaon+Cyber+Hub")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_alerts_endpoint_with_explicit_lat_lng():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/alerts/?lat=28.4595&lng=77.0266")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_alerts_endpoint_missing_all_parameters_returns_400():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/alerts/")
        assert res.status_code == 400
        assert "Must provide either 'location' or both 'lat' and 'lng'" in res.json()["detail"]


@pytest.mark.asyncio
async def test_alerts_endpoint_unresolvable_location_returns_400():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/alerts/?location=UnknownUnresolvablePlaceXYZ999")
        assert res.status_code == 400
        data = res.json()
        assert "unresolved_location" in data.get("status", "") or "Could not resolve location" in data.get("detail", "")
