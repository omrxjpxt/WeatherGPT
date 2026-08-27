import pytest
from datetime import datetime, timezone
import httpx
from unittest.mock import AsyncMock

from app.providers.weatherapi_client import WeatherApiClient
from app.providers.weather.weatherapi import WeatherApiWeatherProvider
from app.providers.alerts.weatherapi import WeatherApiAlertProvider
from app.models.enums import AlertSourceClass, AlertSeverity

@pytest.fixture
def mock_client():
    client = WeatherApiClient()
    client.fetch_forecast = AsyncMock()
    return client

@pytest.mark.asyncio
async def test_weatherapi_weather_normalization(mock_client):
    mock_client.fetch_forecast.return_value = {
        "forecast": {
            "forecastday": [
                {
                    "hour": [
                        {
                            "time_epoch": int(datetime.now(timezone.utc).timestamp()),
                            "temp_c": 35.0,
                            "precip_mm": 2.5,
                            "humidity": 60,
                            "wind_kph": 20.0,
                            "gust_kph": 30.0,
                            "vis_km": 5.0,
                            "condition": {"text": "Rain"}
                        }
                    ]
                }
            ]
        }
    }
    
    provider = WeatherApiWeatherProvider(client=mock_client)
    res = await provider.get_forecast(28.0, 77.0, datetime.now(timezone.utc), 12)
    
    assert len(res) == 1
    p = res[0]
    assert p.temperature == 35.0
    assert p.precipitation_mm == 2.5
    assert p.visibility == 5000.0 # Converted to meters
    assert p.condition == "Rain"

@pytest.mark.asyncio
async def test_weatherapi_alert_normalization(mock_client):
    mock_client.fetch_forecast.return_value = {
        "alerts": {
            "alert": [
                {
                    "headline": "Flood Warning issued by IMD",
                    "desc": "Heavy rain expected",
                    "severity": "Moderate",
                    "effective": "2026-08-27T10:00:00+00:00",
                    "expires": "2026-08-27T18:00:00+00:00",
                    "instruction": "Avoid low areas"
                },
                {
                    "headline": "Heat Wave by NWS",
                    "severity": "Severe"
                }
            ]
        }
    }
    
    provider = WeatherApiAlertProvider(client=mock_client)
    res = await provider.get_active_alerts(28.0, 77.0)
    
    assert len(res) == 2
    a1, a2 = res
    
    assert a1.source_class == AlertSourceClass.secondary
    assert not a1.is_override_eligible
    assert a1.source_name == "IMD via WeatherAPI"
    assert a1.severity == AlertSeverity.watch
    
    assert a2.source_class == AlertSourceClass.secondary
    assert a2.source_name == "NWS via WeatherAPI"
    assert a2.severity == AlertSeverity.warning
