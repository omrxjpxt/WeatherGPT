import asyncio
from typing import List
from datetime import datetime, timedelta, timezone
from app.providers.alerts.base import AlertProvider
from app.models.enums import AlertSeverity, AlertSourceClass
from app.decision_engine.normalized_models import NormalizedAlert
from app.core.config import settings

class MockAlertProvider(AlertProvider):
    @property
    def provider_name(self) -> str:
        return "WeatherGPT Internal Mock"
        
    @property
    def provider_class(self) -> str:
        return AlertSourceClass.demo

    async def get_active_alerts(self, lat: float, lng: float) -> List[NormalizedAlert]:
        await asyncio.sleep(0.1)
        now = datetime.now(timezone.utc)
        
        # Mock: an Orange Alert (warning) that covers the current area
        return [
            NormalizedAlert(
                id="a1",
                source_name=self.provider_name,
                source_class=self.provider_class,
                severity=AlertSeverity.warning,
                # Using a bounding box [ [lat, lng], ... ] conceptually
                affected_areas_polygon=[
                    [28.4, 77.0],
                    [28.7, 77.0],
                    [28.7, 77.4],
                    [28.4, 77.4],
                ],
                issued_at=now - timedelta(hours=2),
                expires_at=now + timedelta(hours=10),
                action="Avoid unnecessary travel.",
                source_url="https://example.com/alert/a1",
            )
        ]
