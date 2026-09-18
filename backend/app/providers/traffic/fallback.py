import logging
from datetime import datetime, timezone
from typing import Optional

from app.providers.traffic.base import TrafficProvider
from app.models.enums import TransportMode, TrafficStatus, CongestionLevel, TrafficCondition
from app.models.traffic import TrafficSnapshot
from app.decision_engine.normalized_models import NormalizedRoute

logger = logging.getLogger(__name__)

class UnavailableTrafficProvider(TrafficProvider):
    @property
    def provider_name(self) -> str:
        return "Traffic Data Unavailable"

    @property
    def traffic_status(self) -> TrafficStatus:
        return TrafficStatus.unavailable

    async def get_traffic_for_route(
        self,
        route: NormalizedRoute,
        departure_time: datetime,
        mode: TransportMode
    ) -> TrafficSnapshot:
        return TrafficSnapshot(
            status=TrafficStatus.unavailable,
            condition=TrafficCondition.unknown,
            congestion_level=CongestionLevel.unknown,
            delay_seconds=0.0,
            static_duration=route.total_duration,
            traffic_aware_duration=route.total_duration,
            current_speed_kmh=None,
            free_flow_speed_kmh=None,
            segments=[],
            timestamp=datetime.now(timezone.utc),
            source_name=self.provider_name,
            provenance="unavailable"
        )

class FallbackTrafficProvider(TrafficProvider):
    def __init__(self, primary: TrafficProvider, fallback: Optional[TrafficProvider] = None):
        self.primary = primary
        self.fallback = fallback or UnavailableTrafficProvider()
        self._last_status = primary.traffic_status

    @property
    def provider_name(self) -> str:
        return self.primary.provider_name

    @property
    def traffic_status(self) -> TrafficStatus:
        return self._last_status

    async def get_traffic_for_route(
        self,
        route: NormalizedRoute,
        departure_time: datetime,
        mode: TransportMode
    ) -> TrafficSnapshot:
        try:
            snapshot = await self.primary.get_traffic_for_route(route, departure_time, mode)
            self._last_status = snapshot.status
            return snapshot
        except Exception as e:
            logger.warning(f"Primary traffic provider '{self.primary.provider_name}' failed: {e}. Falling back.")
            self._last_status = self.fallback.traffic_status
            return await self.fallback.get_traffic_for_route(route, departure_time, mode)
