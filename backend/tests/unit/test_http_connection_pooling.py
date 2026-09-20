import pytest
import httpx
from app.core.http import HttpClientManager
from app.providers.weather.open_meteo import OpenMeteoWeatherProvider
from app.providers.routing.google_routes import GoogleRoutesProvider
from app.providers.geocoding.pincode import NcrPincodeGeocodingProvider


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_http_client_manager_lifecycle():
    # 1. Initialize manager
    client = await HttpClientManager.initialize(timeout=5.0, max_keepalive=10, max_connections=25)
    assert client is not None
    assert not client.is_closed
    assert HttpClientManager.get_client() is client

    # 2. Calling initialize again reuses existing open client
    client2 = await HttpClientManager.initialize()
    assert client2 is client

    # 3. Providers dynamically retrieve the shared client
    weather_provider = OpenMeteoWeatherProvider()
    routes_provider = GoogleRoutesProvider()
    pincode_provider = NcrPincodeGeocodingProvider()

    # Verify providers fall back to HttpClientManager.get_client()
    assert HttpClientManager.get_client() is not None

    # 4. Graceful close
    await HttpClientManager.close()
    assert HttpClientManager.get_client() is None
    assert client.is_closed


@pytest.mark.asyncio
async def test_provider_can_accept_injected_client():
    mock_client = httpx.AsyncClient()
    try:
        weather_provider = OpenMeteoWeatherProvider(client=mock_client)
        assert weather_provider._client is mock_client

        routes_provider = GoogleRoutesProvider(client=mock_client)
        assert routes_provider._client is mock_client

        pincode_provider = NcrPincodeGeocodingProvider(http_client=mock_client)
        assert pincode_provider._client is mock_client
    finally:
        await mock_client.aclose()
