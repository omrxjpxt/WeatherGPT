from datetime import datetime, timezone
from typing import List, Optional
import httpx
import logging

from app.providers.alerts.base import AlertProvider
from app.decision_engine.normalized_models import NormalizedAlert
from app.models.enums import AlertSeverity, AlertSourceClass
from app.providers.weatherapi_client import WeatherApiClient

logger = logging.getLogger(__name__)

class WeatherApiAlertProvider(AlertProvider):
    def __init__(self, client: Optional[WeatherApiClient] = None):
        self.client = client or WeatherApiClient()
        
    @property
    def provider_name(self) -> str:
        return "WeatherAPI"
        
    @property
    def provider_class(self) -> str:
        return AlertSourceClass.secondary
        
    async def get_active_alerts(self, lat: float, lng: float) -> List[NormalizedAlert]:
        try:
            # We can use days=1 since alerts are current/near-term
            data = await self.client.fetch_forecast(lat, lng, days=1)
            return self._normalize(data)
        except httpx.HTTPStatusError as e:
            logger.error(f"WeatherAPI Alert HTTP error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"WeatherAPI Alert fetch failed: {e}")
            return []
            
    def _parse_severity(self, severity_str: str) -> AlertSeverity:
        s = severity_str.lower()
        if "extreme" in s:
            return AlertSeverity.emergency
        if "severe" in s:
            return AlertSeverity.warning
        if "moderate" in s:
            return AlertSeverity.watch
        if "minor" in s:
            return AlertSeverity.advisory
        return AlertSeverity.warning # Default fallback
        
    def _normalize(self, data: dict) -> List[NormalizedAlert]:
        alerts_list = data.get("alerts", {}).get("alert", [])
        normalized = []
        
        for idx, a in enumerate(alerts_list):
            # Try to extract actual source from headline or desc
            headline = a.get("headline", "")
            desc = a.get("desc", "")
            
            source_name = "WeatherAPI"
            if "IMD" in headline or "India Meteorological Department" in headline or "IMD" in desc:
                source_name = "IMD via WeatherAPI"
            elif " by " in headline:
                # E.g. "... by NWS"
                parts = headline.split(" by ")
                if len(parts) > 1:
                    source_name = f"{parts[-1].strip()} via WeatherAPI"
                    
            try:
                # ISO 8601 strings
                issued_at = datetime.fromisoformat(a.get("effective", datetime.now(timezone.utc).isoformat()))
                expires_str = a.get("expires")
                expires_at = datetime.fromisoformat(expires_str) if expires_str else None
            except ValueError:
                issued_at = datetime.now(timezone.utc)
                expires_at = None

            alert = NormalizedAlert(
                id=f"wapi_{idx}_{issued_at.timestamp()}",
                source_name=source_name,
                source_class=AlertSourceClass.secondary,
                severity=self._parse_severity(a.get("severity", "")),
                affected_areas_polygon=[], # WeatherAPI does not provide polygons
                issued_at=issued_at,
                expires_at=expires_at,
                action=a.get("instruction"),
                source_url=None,
                is_override_eligible=False # Policy restricts this
            )
            normalized.append(alert)
            
        return normalized
