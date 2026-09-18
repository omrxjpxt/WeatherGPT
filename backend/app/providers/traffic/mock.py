from datetime import datetime, timezone, timedelta
from typing import List

from app.providers.traffic.base import TrafficProvider
from app.models.enums import TransportMode, TrafficStatus, CongestionLevel, TrafficCondition
from app.models.traffic import TrafficSnapshot, TrafficSegment
from app.decision_engine.normalized_models import NormalizedRoute

class MockTrafficProvider(TrafficProvider):
    @property
    def provider_name(self) -> str:
        return "Mock Traffic Provider (Demo)"

    @property
    def traffic_status(self) -> TrafficStatus:
        return TrafficStatus.mock

    async def get_traffic_for_route(
        self,
        route: NormalizedRoute,
        departure_time: datetime,
        mode: TransportMode
    ) -> TrafficSnapshot:
        static_duration = route.total_duration
        static_seconds = max(1.0, static_duration.total_seconds())
        distance_km = max(0.1, route.total_distance_km)
        free_flow_speed = distance_km / (static_seconds / 3600.0)

        # Walk and Metro have no road traffic delay
        if mode in (TransportMode.walk, TransportMode.metro):
            return TrafficSnapshot(
                status=TrafficStatus.mock,
                condition=TrafficCondition.clear,
                congestion_level=CongestionLevel.free_flow,
                delay_seconds=0.0,
                static_duration=static_duration,
                traffic_aware_duration=static_duration,
                current_speed_kmh=round(free_flow_speed, 1),
                free_flow_speed_kmh=round(free_flow_speed, 1),
                segments=[
                    TrafficSegment(
                        start_lat=seg.start_lat,
                        start_lng=seg.start_lng,
                        end_lat=seg.end_lat,
                        end_lng=seg.end_lng,
                        congestion_level=CongestionLevel.free_flow,
                        delay_seconds=0.0,
                        current_speed_kmh=round(free_flow_speed, 1),
                        free_flow_speed_kmh=round(free_flow_speed, 1),
                    ) for seg in route.segments
                ],
                timestamp=datetime.now(timezone.utc),
                source_name=self.provider_name,
                provenance="demo/mock"
            )

        # Deterministic traffic profile for Car / Bike based on departure hour
        hour = departure_time.hour
        is_rush_hour = (8 <= hour <= 10) or (17 <= hour <= 20)

        if is_rush_hour:
            # 30% delay during rush hours
            delay_fraction = 0.35 if mode == TransportMode.car else 0.25
            congestion_level = CongestionLevel.heavy if delay_fraction >= 0.3 else CongestionLevel.moderate
            condition = TrafficCondition.congested
        else:
            # 10% mild delay during off-peak
            delay_fraction = 0.10
            congestion_level = CongestionLevel.moderate
            condition = TrafficCondition.clear

        total_delay_seconds = round(static_seconds * delay_fraction, 0)
        traffic_aware_duration = static_duration + timedelta(seconds=total_delay_seconds)
        current_speed = distance_km / ((static_seconds + total_delay_seconds) / 3600.0)

        # Distribute delay across segments deterministically (heavier in middle segments)
        num_segments = len(route.segments)
        traffic_segments: List[TrafficSegment] = []

        if num_segments == 0:
            traffic_segments = []
        elif num_segments == 1:
            traffic_segments.append(TrafficSegment(
                start_lat=route.segments[0].start_lat,
                start_lng=route.segments[0].start_lng,
                end_lat=route.segments[0].end_lat,
                end_lng=route.segments[0].end_lng,
                congestion_level=congestion_level,
                delay_seconds=total_delay_seconds,
                current_speed_kmh=round(current_speed, 1),
                free_flow_speed_kmh=round(free_flow_speed, 1),
            ))
        else:
            weights = []
            for i in range(num_segments):
                # Middle segments bear higher congestion
                pos = i / (num_segments - 1)
                weight = 1.0 + 1.5 * (1.0 - 4.0 * (pos - 0.5) ** 2)
                weights.append(weight)
            total_weight = sum(weights)

            for i, seg in enumerate(route.segments):
                seg_delay = round(total_delay_seconds * (weights[i] / total_weight), 1)
                seg_static_sec = max(1.0, seg.estimated_duration.total_seconds())
                seg_free_speed = seg.distance_km / (seg_static_sec / 3600.0)
                seg_curr_speed = seg.distance_km / ((seg_static_sec + seg_delay) / 3600.0)
                
                seg_congestion = congestion_level if seg_delay > (total_delay_seconds / num_segments) else CongestionLevel.moderate

                traffic_segments.append(TrafficSegment(
                    start_lat=seg.start_lat,
                    start_lng=seg.start_lng,
                    end_lat=seg.end_lat,
                    end_lng=seg.end_lng,
                    congestion_level=seg_congestion,
                    delay_seconds=seg_delay,
                    current_speed_kmh=round(seg_curr_speed, 1),
                    free_flow_speed_kmh=round(seg_free_speed, 1),
                ))

        return TrafficSnapshot(
            status=TrafficStatus.mock,
            condition=condition,
            congestion_level=congestion_level,
            delay_seconds=total_delay_seconds,
            static_duration=static_duration,
            traffic_aware_duration=traffic_aware_duration,
            current_speed_kmh=round(current_speed, 1),
            free_flow_speed_kmh=round(free_flow_speed, 1),
            segments=traffic_segments,
            timestamp=datetime.now(timezone.utc),
            source_name=self.provider_name,
            provenance="demo/mock"
        )
