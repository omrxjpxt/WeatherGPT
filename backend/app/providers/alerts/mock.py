import asyncio
from typing import List
from datetime import datetime, timedelta, timezone
from app.providers.alerts.base import AlertProvider
from app.models.enums import AlertSeverity
from app.decision_engine.normalized_models import NormalizedAlert

class MockAlertProvider(AlertProvider):
    async def get_active_alerts(self, lat: float, lng: float) -> List[NormalizedAlert]:
        await asyncio.sleep(0.1)
        now = datetime.now(timezone.utc)
        
        # Mock: an Orange Alert (warning) that covers the current area
        return [
            NormalizedAlert(
                id="a1",
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
                requires_override=True, # Severe enough to override normal logic
            )
        ]
