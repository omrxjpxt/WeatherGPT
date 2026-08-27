import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
import httpx

from app.providers.weather.open_meteo import OpenMeteoWeatherProvider, OpenMeteoProviderError
from app.decision_engine.normalized_models import NormalizedWeatherPoint

@pytest.fixture
def provider():
    # Use a small max_retries for faster tests
    return OpenMeteoWeatherProvider(timeout_seconds=1.0, max_retries=1)

def _mock_response(status_code: int, json_data: dict = None) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    if json_data:
        mock_resp.json.return_value = json_data
    if status_code >= 400:
        def raise_for_status():
            raise httpx.HTTPStatusError(
                message=f"Error {status_code}",
                request=MagicMock(),
                response=mock_resp
            )
        mock_resp.raise_for_status.side_effect = raise_for_status
    else:
        mock_resp.raise_for_status.return_value = None
    return mock_resp

def test_successful_normalization(provider):
    start_time = datetime(2026, 8, 27, 8, 0, tzinfo=timezone.utc)
    
    mock_json = {
        "hourly": {
            "time": ["2026-08-27T08:00", "2026-08-27T09:00"],
            "temperature_2m": [30.5, 41.0],
            "relative_humidity_2m": [50, 45],
            "precipitation": [0.0, 30.0],
            "weather_code": [0, 95],
            "wind_speed_10m": [10.0, 25.0],
            "wind_gusts_10m": [15.0, 40.0],
            "visibility": [10000.0, 500.0]
        }
    }
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = _mock_response(200, mock_json)
        
        # Test using asyncio.run since we're in a sync test wrapper or use pytest.mark.asyncio
        # pytest-asyncio handles this with @pytest.mark.asyncio, but we can also just call it.
        pass

@pytest.mark.asyncio
async def test_successful_normalization_async(provider):
    start_time = datetime(2026, 8, 27, 8, 0, tzinfo=timezone.utc)
    
    mock_json = {
        "hourly": {
            "time": ["2026-08-27T08:00", "2026-08-27T09:00"],
            "temperature_2m": [30.5, 41.0],
            "relative_humidity_2m": [50, 45],
            "precipitation": [0.0, 30.0],
            "weather_code": [0, 95],
            "wind_speed_10m": [10.0, 25.0],
            "wind_gusts_10m": [15.0, 40.0],
            "visibility": [10000.0, 500.0]
        }
    }
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = _mock_response(200, mock_json)
        
        forecast = await provider.get_forecast(28.6, 77.3, start_time, 2)
        
        assert len(forecast) == 2
        
        pt1 = forecast[0]
        assert pt1.time == start_time
        assert pt1.temperature == 30.5
        assert pt1.precipitation_mm == 0.0
        assert pt1.humidity == 50
        assert pt1.condition == "Clear sky" # WMO 0
        assert not pt1.is_extreme_heat
        assert not pt1.is_poor_visibility
        assert pt1.visibility == 10000.0
        
        pt2 = forecast[1]
        assert pt2.temperature == 41.0
        assert pt2.precipitation_mm == 30.0
        assert pt2.condition == "Thunderstorm" # WMO 95
        assert pt2.is_extreme_heat # 41.0 > 40.0
        assert pt2.is_poor_visibility # visibility < 1000.0

@pytest.mark.asyncio
async def test_fail_fast_on_4xx(provider):
    start_time = datetime.now(timezone.utc)
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = _mock_response(400, {"error": True})
        
        with pytest.raises(OpenMeteoProviderError, match="Client error"):
            await provider.get_forecast(28.6, 77.3, start_time, 2)
            
        assert mock_get.call_count == 1 # No retries for 4xx

@pytest.mark.asyncio
async def test_retry_on_5xx(provider):
    start_time = datetime.now(timezone.utc)
    with patch("httpx.AsyncClient.get") as mock_get:
        # Return 500 twice, it will retry and eventually fail
        mock_get.return_value = _mock_response(500)
        
        with pytest.raises(OpenMeteoProviderError, match="Server error"):
            await provider.get_forecast(28.6, 77.3, start_time, 2)
            
        # 1 initial + 1 retry = 2 calls
        assert mock_get.call_count == 2

@pytest.mark.asyncio
async def test_missing_fields_raises_error(provider):
    start_time = datetime(2026, 8, 27, 8, 0, tzinfo=timezone.utc)
    mock_json = {
        "hourly": {
            "time": ["2026-08-27T08:00"],
            "temperature_2m": [30.5],
            # missing precipitation
        }
    }
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = _mock_response(200, mock_json)
        
        with pytest.raises(OpenMeteoProviderError, match="Missing or invalid field"):
            await provider.get_forecast(28.6, 77.3, start_time, 1)

@pytest.mark.asyncio
async def test_timeout_raises_error(provider):
    start_time = datetime.now(timezone.utc)
    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Timeout")):
        with pytest.raises(OpenMeteoProviderError, match="Request error to Open-Meteo"):
            await provider.get_forecast(28.6, 77.3, start_time, 1)

@pytest.mark.asyncio
async def test_fallback_provider_wrapper():
    from app.providers.weather.fallback import FallbackWeatherProvider
    from app.providers.weather.mock import MockWeatherProvider
    from app.providers.weather.open_meteo import OpenMeteoWeatherProvider
    
    start_time = datetime.now(timezone.utc)
    open_meteo = OpenMeteoWeatherProvider(max_retries=0)
    mock_prov = MockWeatherProvider()
    
    fallback = FallbackWeatherProvider(primary=open_meteo, secondary=mock_prov)
    
    assert fallback.provider_name == "Open-Meteo API"
    
    # Force primary to fail
    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Timeout")):
        forecast = await fallback.get_forecast(28.6, 77.3, start_time, 1)
        
        # Should fallback to mock and return results
        assert len(forecast) == 1
        assert fallback.provider_name == "Mock Weather API"
