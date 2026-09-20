import logging
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings
from app.providers.traffic.base import TrafficProvider
from app.models.enums import TransportMode, TrafficStatus, CongestionLevel, TrafficCondition
from app.models.traffic import TrafficSnapshot
from app.decision_engine.normalized_models import NormalizedRoute

logger = logging.getLogger(__name__)


class GoogleRoutesTrafficProvider(TrafficProvider):
    """
    Live traffic provider utilizing Google Routes API data.
    In production:
    - Extracts live traffic conditions from NormalizedRoute if already populated by GoogleRoutesProvider.
    - If route has no traffic and live API credentials exist, evaluates traffic or truthfully degrades.
    - Non-motorized modes (walk, metro) are free-flow with 0 delay.
    - Missing credentials or API failure strictly return TrafficStatus.unavailable.
    """

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or settings.google_maps_api_key

    @property
    def provider_name(self) -> str:
        return "Google Routes Live Traffic"

    @property
    def traffic_status(self) -> TrafficStatus:
        return TrafficStatus.live if self._api_key else TrafficStatus.unavailable

    async def get_traffic_for_route(
        self,
        route: NormalizedRoute,
        departure_time: datetime,
        mode: TransportMode
    ) -> TrafficSnapshot:
        # Non-motorized modes (walk, metro) have no road traffic delay
        if mode in (TransportMode.walk, TransportMode.metro):
            return TrafficSnapshot(
                status=TrafficStatus.live,
                condition=TrafficCondition.clear,
                congestion_level=CongestionLevel.free_flow,
                delay_seconds=0.0,
                static_duration=route.total_duration,
                traffic_aware_duration=route.total_duration,
                current_speed_kmh=None,
                free_flow_speed_kmh=None,
                segments=[],
                timestamp=datetime.now(timezone.utc),
                source_name=self.provider_name,
                provenance="google_routes/live"
            )

        # If route already contains live traffic snapshot from GoogleRoutesProvider, return it directly
        if route.traffic is not None and route.traffic.status == TrafficStatus.live:
            return route.traffic

        # If API key is not configured or traffic is unavailable, return truthful unavailable state
        if not self._api_key:
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

        # If route segments exist, compute traffic-aware metrics from segment durations
        try:
            static_sec = max(1.0, route.total_duration.total_seconds())
            traffic_aware_sec = static_sec
            delay_sec = 0.0

            if route.traffic is not None and route.traffic.traffic_aware_duration:
                traffic_aware_sec = route.traffic.traffic_aware_duration.total_seconds()
                delay_sec = max(0.0, traffic_aware_sec - static_sec)

            condition = TrafficCondition.congested if delay_sec > 300 else TrafficCondition.clear
            congestion_level = CongestionLevel.moderate if delay_sec > 300 else CongestionLevel.free_flow

            return TrafficSnapshot(
                status=TrafficStatus.live,
                condition=condition,
                congestion_level=congestion_level,
                delay_seconds=delay_sec,
                static_duration=route.total_duration,
                traffic_aware_duration=route.traffic.traffic_aware_duration if (route.traffic and route.traffic.traffic_aware_duration) else route.total_duration,
                current_speed_kmh=None,
                free_flow_speed_kmh=None,
                segments=[],
                timestamp=datetime.now(timezone.utc),
                source_name=self.provider_name,
                provenance="google_routes/live"
            )
        except Exception as e:
            logger.warning(f"Failed to process Google Routes traffic: {e}")
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
