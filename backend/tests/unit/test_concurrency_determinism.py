import pytest
import asyncio
from datetime import datetime, timezone
from app.models.trip import TripRequest
from app.models.enums import TransportMode, TripStatus
from app.services.trip_service import TripService
from app.providers.weather.mock import MockWeatherProvider
from app.providers.routing.mock import MockRoutingProvider
from app.providers.traffic.mock import MockTrafficProvider
from app.providers.alerts.mock import MockAlertProvider
from app.repositories.mock_hazard_repository import MockHazardRepository


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def trip_service():
    return TripService(
        weather_provider=MockWeatherProvider(),
        routing_provider=MockRoutingProvider(),
        alert_provider=MockAlertProvider(),
        traffic_provider=MockTrafficProvider(),
        hazard_repository=MockHazardRepository()
    )


@pytest.mark.asyncio
async def test_concurrent_repeated_evaluations_are_strictly_deterministic(trip_service):
    request = TripRequest(
        origin="Noida Sector 62",
        destination="Gurgaon Cyber Hub",
        departure_time=datetime(2026, 8, 27, 8, 0, tzinfo=timezone.utc),
        mode=TransportMode.bike
    )

    # Launch 10 simultaneous trip analyses concurrently
    tasks = [trip_service.analyze_trip(request) for _ in range(10)]
    results = await asyncio.gather(*tasks)

    # Verify every single execution returned identical deterministic outputs
    first_res = results[0]
    assert first_res.status == TripStatus.success
    assert first_res.risk is not None

    baseline_score = first_res.risk.overall_score
    baseline_level = first_res.risk.level
    baseline_route_id = first_res.routes[0].route_id if first_res.routes else None
    baseline_rec = first_res.recommendation.headline

    for i, res in enumerate(results[1:], start=2):
        assert res.risk.overall_score == baseline_score, f"Run {i} score {res.risk.overall_score} != baseline {baseline_score}"
        assert res.risk.level == baseline_level, f"Run {i} level {res.risk.level} != baseline {baseline_level}"
        selected_route_id = res.routes[0].route_id if res.routes else None
        assert selected_route_id == baseline_route_id, f"Run {i} route {selected_route_id} != baseline {baseline_route_id}"
        assert res.recommendation.headline == baseline_rec, f"Run {i} rec headline differs"
