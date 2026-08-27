import asyncio
from datetime import timedelta
from app.providers.routing.base import RoutingProvider
from app.models.enums import TransportMode
from app.decision_engine.normalized_models import NormalizedRoute, NormalizedRouteSegment

class MockRoutingProvider(RoutingProvider):
    async def get_route(self, origin: str, destination: str, mode: TransportMode) -> NormalizedRoute:
        await asyncio.sleep(0.1)
        
        if mode == TransportMode.metro:
            return NormalizedRoute(
                segments=[
                    NormalizedRouteSegment(
                        start_lat=28.6270, start_lng=77.3650,
                        end_lat=28.5850, end_lng=77.3200,
                        distance_km=5.0,
                        estimated_duration=timedelta(minutes=15)
                    ),
                    NormalizedRouteSegment(
                        start_lat=28.5850, start_lng=77.3200,
                        end_lat=28.4942, end_lng=77.0860,
                        distance_km=37.0,
                        estimated_duration=timedelta(minutes=60)
                    )
                ],
                total_distance_km=42.0,
                total_duration=timedelta(minutes=75)
            )
            
        # Default road route (Bike/Car)
        duration = timedelta(minutes=55) if mode == TransportMode.bike else timedelta(minutes=65)
        return NormalizedRoute(
            segments=[
                NormalizedRouteSegment(
                    start_lat=28.6270, start_lng=77.3650,
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
                    end_lat=28.4942, end_lng=77.0860,
                    distance_km=2.0,
                    estimated_duration=timedelta(minutes=2)
                )
            ],
            total_distance_km=35.5,
            total_duration=duration
        )
