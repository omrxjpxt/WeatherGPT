import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.providers.weather.fallback import FallbackWeatherProvider
from app.providers.weather.base import WeatherProvider
from app.api.dependencies import get_weather_provider


class SimulatedWeatherOutage(RuntimeError):
    pass


class FailingWeatherProvider(WeatherProvider):
    @property
    def provider_name(self) -> str:
        return "Failing Weather Provider"

    async def get_current_weather(self, lat: float, lng: float):
        raise SimulatedWeatherOutage("Simulated Open-Meteo outage")

    async def get_forecast(self, lat: float, lng: float, start_time, hours: int):
        raise SimulatedWeatherOutage("Simulated Open-Meteo forecast outage")


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_standalone_weather_endpoints_success():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # GET /api/v1/weather/current
        res_curr = await client.get("/api/v1/weather/current?lat=28.627&lng=77.365")
        assert res_curr.status_code == 200
        curr_data = res_curr.json()
        assert "temperature" in curr_data
        assert "condition" in curr_data

        # GET /api/v1/weather/forecast
        res_fore = await client.get("/api/v1/weather/forecast?lat=28.627&lng=77.365&hours=6")
        assert res_fore.status_code == 200
        fore_data = res_fore.json()
        assert isinstance(fore_data, list)
        assert len(fore_data) > 0
        assert "temperature" in fore_data[0]
        assert "condition" in fore_data[0]


@pytest.mark.asyncio
async def test_standalone_weather_endpoints_503_on_provider_outage():
    app.dependency_overrides[get_weather_provider] = lambda: FailingWeatherProvider()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res_curr = await client.get("/api/v1/weather/current?lat=28.627&lng=77.365")
            assert res_curr.status_code == 503
            assert "unavailable" in res_curr.json()["detail"].lower()

            res_fore = await client.get("/api/v1/weather/forecast?lat=28.627&lng=77.365&hours=6")
            assert res_fore.status_code == 503
            assert "unavailable" in res_fore.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_weather_provider, None)


@pytest.mark.asyncio
async def test_fallback_provider_never_silently_uses_mock_when_secondary_is_none():
    provider = FallbackWeatherProvider(primary=FailingWeatherProvider(), secondary=None)
    with pytest.raises(SimulatedWeatherOutage):
        from datetime import datetime, timezone
        await provider.get_forecast(28.627, 77.365, datetime.now(timezone.utc), 6)
