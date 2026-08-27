import httpx
from typing import Dict, Any
from app.core.config import settings

class WeatherApiClient:
    """
    Shared HTTP client for WeatherAPI to avoid duplicating authentication and network logic.
    """
    def __init__(self):
        self.api_key = settings.weatherapi_api_key
        self.base_url = "https://api.weatherapi.com/v1"
        self.timeout = 5.0
        
    async def fetch_forecast(self, lat: float, lng: float, days: int = 2) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("WeatherAPI key is missing.")
            
        url = f"{self.base_url}/forecast.json"
        params = {
            "key": self.api_key,
            "q": f"{lat},{lng}",
            "days": days,
            "alerts": "yes", # Fetch alerts and forecast in one go
            "aqi": "no"
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
