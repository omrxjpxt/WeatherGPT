import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock

from app.models.trip import TripRequest
from app.models.enums import TransportMode, RiskLevel, TripStatus
from app.decision_engine.normalized_models import (
    NormalizedRoute,
    NormalizedRouteSegment,
    NormalizedWeatherPoint,
)
from app.services.trip_service import TripService
from app.services.scenario_service import ScenarioService
from app.providers.geocoding.base import GeocodingResult, GeocodingResultType, GeocodingProvenance
from app.models.enums import AlertSourceClass


@pytest.fixture
def anyio_backend():
    return "asyncio"


class CountingWeatherProvider:
    def __init__(self):
        self.provider_name = "CountingWeather"
        self.call_count = 0

    async def get_forecast(self, lat: float, lng: float, start_time: datetime, hours: int):
        self.call_count += 1
        points = []
        base = start_time if start_time.tzinfo else start_time.replace(tzinfo=timezone.utc)
        for h in range(hours):
            points.append(
                NormalizedWeatherPoint(
                    time=base + timedelta(hours=h),
                    temperature=28.0 + (h % 5),
                    precipitation_mm=0.0,
                    humidity=50.0,
                    wind_speed=12.0,
                    wind_gusts=15.0,
                    visibility=8000.0,
                    condition="Clear",
                    is_extreme_heat=False,
                    is_poor_visibility=False,
                )
            )
        return points


class CountingRoutingProvider:
    def __init__(self):
        self.provider_name = "CountingRouting"
        self.route_status = AsyncMock(value="ok")
        self.call_count = 0

    async def get_route(self, origin_lat, origin_lng, dest_lat, dest_lng, mode, departure_time=None):
        self.call_count += 1
        seg = NormalizedRouteSegment(
            start_lat=origin_lat,
            start_lng=origin_lng,
            end_lat=dest_lat,
            end_lng=dest_lng,
            distance_km=15.0,
            estimated_duration=timedelta(minutes=30),
            traffic_congestion_factor=1.0,
        )
        return [
            NormalizedRoute(
                route_id="counting_route_1",
                summary="Optimal Corridor",
                polyline="dummy_polyline",
                segments=[seg],
                total_distance_km=15.0,
                total_duration=timedelta(minutes=30),
                provider_name="CountingRouting",
                provenance="live",
            )
        ]


class CountingGeocodingProvider:
    def __init__(self):
        self.call_count = 0

    async def geocode(self, query: str):
        self.call_count += 1
        return GeocodingResult(
            query=query,
            lat=28.6270,
            lng=77.3650,
            display_name=f"Resolved {query}",
            provider="counting_geo",
            result_type=GeocodingResultType.CITY_LOCALITY,
            confidence=1.0,
            is_exact=True,
            timestamp=datetime.now(timezone.utc),
            provenance=GeocodingProvenance.MOCK_TEST,
        )


class CountingAlertProvider:
    def __init__(self):
        self.provider_name = "CountingAlerts"
        self.provider_class = AlertSourceClass.authoritative
        self.call_count = 0

    async def get_active_alerts(self, lat: float, lng: float):
        self.call_count += 1
        return []


@pytest.mark.asyncio
async def test_scenario_single_pass_eliminates_13x_provider_explosion():
    weather = CountingWeatherProvider()
    routing = CountingRoutingProvider()
    geocoding = CountingGeocodingProvider()
    alerts = CountingAlertProvider()

    trip_service = TripService(
        weather_provider=weather,
        routing_provider=routing,
        alert_provider=alerts,
        geocoding_provider=geocoding,
    )
    scenario_service = ScenarioService(trip_service=trip_service)

    base_time = datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc)
    departure_times = [base_time + timedelta(minutes=i * 30) for i in range(13)]

    req = TripRequest(
        origin="Noida Sector 62",
        destination="Gurgaon Cyber Hub",
        departure_time=base_time,
        mode=TransportMode.car,
    )

    import time
    t0 = time.monotonic()
    results = await scenario_service.evaluate_scenarios(req, departure_times)
    elapsed_ms = (time.monotonic() - t0) * 1000

    # 1. Assert exactly 13 results returned
    assert len(results) == 13

    # 2. Assert each result has matching departure time and valid status
    for i, res in enumerate(results):
        assert res.departure_time == departure_times[i]
        assert res.status == TripStatus.success
        assert res.risk is not None
        assert res.risk.overall_score >= 0.0
        assert res.estimated_duration == timedelta(minutes=30)
        assert res.recommendation is not None

    # 3. Assert provider call counts:
    # Exactly 2 geocoding calls (origin + destination), NOT 26!
    assert geocoding.call_count == 2
    # Exactly 1 primary weather call, NOT 13!
    assert weather.call_count == 1
    # Exactly 1 routing call (car mode), NOT 13!
    assert routing.call_count == 1
    # Exactly 1 alert call, NOT 13!
    assert alerts.call_count == 1

    # 4. Assert in-memory performance: 13 evaluations completed in under 500ms
    assert elapsed_ms < 500.0, f"Scenario evaluation took {elapsed_ms:.1f}ms, expected < 500ms"
