import pytest
import asyncio
from datetime import datetime, timezone
from app.models.trip import TripRequest
from app.models.enums import TransportMode
from app.services.trip_service import TripService
from app.providers.weather.mock import MockWeatherProvider
from app.providers.routing.mock import MockRoutingProvider
from app.providers.alerts.mock import MockAlertProvider
from app.providers.traffic.mock import MockTrafficProvider
from app.repositories.firestore.trip_repository import FirestoreTripRepository

@pytest.fixture
def memory_trip_repo():
    return FirestoreTripRepository(client=None)

@pytest.fixture
def trip_service(memory_trip_repo):
    return TripService(
        weather_provider=MockWeatherProvider(),
        routing_provider=MockRoutingProvider(),
        alert_provider=MockAlertProvider(),
        traffic_provider=MockTrafficProvider(),
        trip_repository=memory_trip_repo
    )

@pytest.mark.asyncio
async def test_non_blocking_trip_persistence(trip_service, memory_trip_repo):
    uid = "test_user_persistence"
    request = TripRequest(
        origin="Noida Sector 62",
        destination="Gurgaon Cyber Hub",
        departure_time=datetime.now(timezone.utc),
        mode=TransportMode.car
    )
    
    # Run analysis
    response = await trip_service.analyze_trip(request, uid=uid)
    assert response is not None
    assert response.analysis_id is not None
    
    # Allow background tasks to run (fire-and-forget save)
    await asyncio.sleep(0.1)
    
    # Verify it was saved to memory store
    history = await memory_trip_repo.get_trip_history(uid)
    assert len(history) == 1
    assert history[0].analysis_id == response.analysis_id
    
    # Retrieve detail
    detail = await memory_trip_repo.get_trip_decision(uid, response.analysis_id)
    assert detail is not None
    assert detail.analysis_id == response.analysis_id
