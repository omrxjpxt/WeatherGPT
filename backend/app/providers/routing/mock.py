import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from app.providers.routing.base import RoutingProvider
from app.models.enums import TransportMode, RouteStatus
from app.decision_engine.normalized_models import NormalizedRoute, NormalizedRouteSegment

class MockRoutingProvider(RoutingProvider):
    def __init__(self, route_count: int = 1):
        self.route_count = route_count

    @property
    def provider_name(self) -> str:
        return "Mock Routing API"
        
    @property
    def route_status(self) -> RouteStatus:
        return RouteStatus.mock

    def set_route_count(self, count: int) -> None:
        self.route_count = max(1, min(3, count))

    async def get_route(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        mode: TransportMode,
        departure_time: Optional[datetime] = None
    ) -> List[NormalizedRoute]:
        await asyncio.sleep(0.05)
        
        if mode == TransportMode.metro:
            return [NormalizedRoute(
                route_id="mock_route_metro_1",
                summary="Via Blue & Yellow Line Metro",
                polyline="mock_metro_polyline_1",
                segments=[
                    NormalizedRouteSegment(
                        start_lat=origin_lat, start_lng=origin_lng,
                        end_lat=28.5850, end_lng=77.3200,
                        distance_km=5.0,
                        estimated_duration=timedelta(minutes=15)
                    ),
                    NormalizedRouteSegment(
                        start_lat=28.5850, start_lng=77.3200,
                        end_lat=dest_lat, end_lng=dest_lng,
                        distance_km=37.0,
                        estimated_duration=timedelta(minutes=60)
                    )
                ],
                total_distance_km=42.0,
                total_duration=timedelta(minutes=75),
                provider_name=self.provider_name,
                provenance="demo/mock"
            )]
            
        # Default road route 1 (Primary - Via Noida-Greater Noida Expy)
        duration_1 = timedelta(minutes=55) if mode == TransportMode.bike else timedelta(minutes=65)
        route_1 = NormalizedRoute(
            route_id="mock_route_1",
            summary="Via Noida-Greater Noida Expy",
            polyline="mock_polyline_1",
            segments=[
                NormalizedRouteSegment(
                    start_lat=origin_lat, start_lng=origin_lng,
                    end_lat=28.6150, end_lng=77.3400,
                    distance_km=3.5,
                    estimated_duration=timedelta(minutes=8)
                ),
                NormalizedRouteSegment(
                    start_lat=28.6150, start_lng=77.3400,
                    end_lat=28.5850, end_lng=77.2800,
                    distance_km=8.0,
                    estimated_duration=timedelta(minutes=12)
                ),
                NormalizedRouteSegment(
                    start_lat=28.5850, start_lng=77.2800,
                    end_lat=28.5650, end_lng=77.2200,
                    distance_km=7.5,
                    estimated_duration=timedelta(minutes=15)
                ),
                NormalizedRouteSegment(
                    start_lat=28.5650, start_lng=77.2200,
                    end_lat=28.5400, end_lng=77.1700,
                    distance_km=6.5,
                    estimated_duration=timedelta(minutes=10)
                ),
                NormalizedRouteSegment(
                    start_lat=28.5400, start_lng=77.1700,
                    end_lat=28.4950, end_lng=77.0890,
                    distance_km=8.0,
                    estimated_duration=timedelta(minutes=8)
                ),
                NormalizedRouteSegment(
                    start_lat=28.4950, start_lng=77.0890,
                    end_lat=dest_lat, end_lng=dest_lng,
                    distance_km=2.0,
                    estimated_duration=timedelta(minutes=2)
                )
            ],
            total_distance_km=35.5,
            total_duration=duration_1,
            provider_name=self.provider_name,
            provenance="demo/mock"
        )
        
        routes = [route_1]
        
        if self.route_count >= 2:
            # Alternative route 2: Via DND Flyway (shorter static duration, distinct corridor)
            duration_2 = timedelta(minutes=48) if mode == TransportMode.bike else timedelta(minutes=56)
            route_2 = NormalizedRoute(
                route_id="mock_route_2",
                summary="Via DND Flyway",
                polyline="mock_polyline_2",
                segments=[
                    NormalizedRouteSegment(
                        start_lat=origin_lat, start_lng=origin_lng,
                        end_lat=28.5880, end_lng=77.3050,
                        distance_km=6.0,
                        estimated_duration=timedelta(minutes=10)
                    ),
                    NormalizedRouteSegment(
                        start_lat=28.5880, start_lng=77.3050,
                        end_lat=28.5680, end_lng=77.2500,
                        distance_km=9.0,
                        estimated_duration=timedelta(minutes=14)
                    ),
                    NormalizedRouteSegment(
                        start_lat=28.5680, start_lng=77.2500,
                        end_lat=28.5300, end_lng=77.1900,
                        distance_km=8.5,
                        estimated_duration=timedelta(minutes=12)
                    ),
                    NormalizedRouteSegment(
                        start_lat=28.5300, start_lng=77.1900,
                        end_lat=28.4950, end_lng=77.0890,
                        distance_km=11.5,
                        estimated_duration=timedelta(minutes=16)
                    ),
                    NormalizedRouteSegment(
                        start_lat=28.4950, start_lng=77.0890,
                        end_lat=dest_lat, end_lng=dest_lng,
                        distance_km=3.0,
                        estimated_duration=timedelta(minutes=4)
                    ),
                ],
                total_distance_km=38.0,
                total_duration=duration_2,
                provider_name=self.provider_name,
                provenance="demo/mock"
            )
            routes.append(route_2)
            
        if self.route_count >= 3:
            # Alternative route 3: Via Outer Ring Road
            duration_3 = timedelta(minutes=62) if mode == TransportMode.bike else timedelta(minutes=72)
            route_3 = NormalizedRoute(
                route_id="mock_route_3",
                summary="Via Outer Ring Road",
                polyline="mock_polyline_3",
                segments=[
                    NormalizedRouteSegment(
                        start_lat=origin_lat, start_lng=origin_lng,
                        end_lat=28.6300, end_lng=77.3100,
                        distance_km=7.5,
                        estimated_duration=timedelta(minutes=14)
                    ),
                    NormalizedRouteSegment(
                        start_lat=28.6300, start_lng=77.3100,
                        end_lat=28.6000, end_lng=77.2100,
                        distance_km=12.0,
                        estimated_duration=timedelta(minutes=20)
                    ),
                    NormalizedRouteSegment(
                        start_lat=28.6000, start_lng=77.2100,
                        end_lat=28.5200, end_lng=77.1300,
                        distance_km=13.0,
                        estimated_duration=timedelta(minutes=22)
                    ),
                    NormalizedRouteSegment(
                        start_lat=28.5200, start_lng=77.1300,
                        end_lat=dest_lat, end_lng=dest_lng,
                        distance_km=9.0,
                        estimated_duration=timedelta(minutes=16)
                    ),
                ],
                total_distance_km=41.5,
                total_duration=duration_3,
                provider_name=self.provider_name,
                provenance="demo/mock"
            )
            routes.append(route_3)
            
        return routes
