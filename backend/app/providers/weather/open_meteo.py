import httpx
import structlog
import asyncio
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta
from app.providers.weather.base import WeatherProvider
from app.decision_engine.normalized_models import NormalizedWeatherPoint

logger = structlog.get_logger(__name__)

# WMO Weather interpretation codes (WW)
# https://open-meteo.com/en/docs
WMO_CODE_MAP = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

class OpenMeteoProviderError(Exception):
    pass

class OpenMeteoWeatherProvider(WeatherProvider):
    """
    Open-Meteo Weather API Provider.
    Non-commercial, free-tier API. Data provided under CC-BY 4.0.
    """
    
    def __init__(self, timeout_seconds: float = 5.0, max_retries: int = 2):
        self.timeout = timeout_seconds
        self.max_retries = max_retries
        self.base_url = "https://api.open-meteo.com/v1/forecast"

    @property
    def provider_name(self) -> str:
        return "Open-Meteo API"

    async def _fetch_with_retry(self, client: httpx.AsyncClient, params: Dict[str, Any]) -> Dict[str, Any]:
        for attempt in range(self.max_retries + 1):
            try:
                response = await client.get(self.base_url, params=params)
                
                # Fail fast on 4xx errors
                if 400 <= response.status_code < 500:
                    logger.error("open_meteo_client_error", status_code=response.status_code, text=response.text)
                    raise OpenMeteoProviderError(f"Client error from Open-Meteo: {response.status_code}")
                
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                # 5xx errors can be retried
                if attempt == self.max_retries:
                    logger.error("open_meteo_server_error", status_code=e.response.status_code, retries_exhausted=True)
                    raise OpenMeteoProviderError(f"Server error from Open-Meteo after {self.max_retries} retries: {e.response.status_code}")
                await asyncio.sleep(0.5 * (2 ** attempt)) # Exponential backoff
            except httpx.RequestError as e:
                if attempt == self.max_retries:
                    logger.error("open_meteo_request_error", error=str(e), retries_exhausted=True)
                    raise OpenMeteoProviderError(f"Request error to Open-Meteo: {str(e)}")
                await asyncio.sleep(0.5 * (2 ** attempt))
                
        raise OpenMeteoProviderError("Unexpected error in fetch_with_retry")

    def _normalize_weather_code(self, code: int) -> str:
        return WMO_CODE_MAP.get(code, "Unknown")

    async def get_forecast(self, lat: float, lng: float, start_time: datetime, hours: int) -> List[NormalizedWeatherPoint]:
        # Request timezone=auto to get hourly times in local time, or use UTC.
        # Open-Meteo returns ISO8601 strings. If we request no timezone parameter, it defaults to GMT/UTC.
        # We will request GMT/UTC to keep everything consistently UTC.
        
        # Determine the number of hours we need to fetch. Open-Meteo provides 7 days by default.
        # If we need specific hours, we can fetch forecast_hours.
        params = {
            "latitude": lat,
            "longitude": lng,
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m,wind_gusts_10m,visibility",
            "timezone": "UTC",
            "forecast_hours": min(72, hours + 24) # Fetch enough hours to cover start_time
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            data = await self._fetch_with_retry(client, params)

        if "hourly" not in data or "time" not in data["hourly"]:
            raise OpenMeteoProviderError("Malformed response: missing 'hourly' data")

        hourly = data["hourly"]
        times = hourly["time"]
        
        # Ensure start_time is UTC for comparison
        target_start = start_time
        if target_start.tzinfo is None:
            target_start = target_start.replace(tzinfo=timezone.utc)
            
        forecast = []
        found_start = False
        hours_collected = 0
        
        for i, time_str in enumerate(times):
            # Open-Meteo returns time as "YYYY-MM-DDTHH:MM" in the requested timezone (UTC)
            dt = datetime.fromisoformat(time_str).replace(tzinfo=timezone.utc)
            
            # Find the closest hour to our requested start_time
            if not found_start:
                if dt >= target_start - timedelta(minutes=30):
                    found_start = True
                else:
                    continue
            
            # Start collecting
            if hours_collected >= hours:
                break
                
            try:
                temp = float(hourly["temperature_2m"][i])
                precip = float(hourly["precipitation"][i])
                humidity = int(hourly["relative_humidity_2m"][i])
                wind_speed = float(hourly["wind_speed_10m"][i])
                wind_gusts = float(hourly["wind_gusts_10m"][i])
                visibility = float(hourly["visibility"][i])
                wmo_code = int(hourly["weather_code"][i])
            except (TypeError, ValueError, IndexError, KeyError) as e:
                logger.error("open_meteo_missing_data", index=i, error=str(e))
                raise OpenMeteoProviderError("Missing or invalid field in Open-Meteo response")
                
            condition = self._normalize_weather_code(wmo_code)
            
            forecast.append(NormalizedWeatherPoint(
                time=dt,
                temperature=temp,
                precipitation_mm=precip,
                humidity=humidity,
                wind_speed=wind_speed,
                wind_gusts=wind_gusts,
                visibility=visibility,
                condition=condition,
                is_extreme_heat=temp > 40.0,
                is_poor_visibility=visibility < 1000.0,
            ))
            
            hours_collected += 1
            
        if not forecast:
            raise OpenMeteoProviderError("Could not find requested time window in forecast")
            
        return forecast
