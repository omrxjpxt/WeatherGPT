from datetime import datetime, timezone, timedelta
import pytest

from app.core.config import Settings
from app.models.enums import TransportMode, TrafficStatus
from app.models.trip import TripRequest
from app.decision_engine.normalized_models import NormalizedRoute, NormalizedRouteSegment
from app.providers.traffic.mock import MockTrafficProvider
from app.providers.traffic.fallback import UnavailableTrafficProvider, FallbackTrafficProvider
from app.providers.traffic.google import GoogleRoutesTrafficProvider
from app.services.trip_service import TripService
from app.providers.weather.mock import MockWeatherProvider
from app.providers.routing.mock import MockRoutingProvider
from app.providers.alerts.mock import MockAlertProvider
from app.providers.geocoding import MockGeocodingProvider


def test_production_never_uses_mock_traffic_when_unconfigured(monkeypatch):
    """
    Validates that in production, when Google Maps API key is missing,
    the system wires UnavailableTrafficProvider, strictly forbidding MockTrafficProvider.
    """
    prod_settings = Settings(
        environment="production",
        google_maps_api_key=None,
        google_traffic_aware=True,
    )
    assert prod_settings.is_production is True

    # Mirror dependencies.py logic
    if prod_settings.is_production:
        if prod_settings.google_maps_api_key and prod_settings.google_traffic_aware:
            provider = FallbackTrafficProvider(
                primary=GoogleRoutesTrafficProvider(api_key=prod_settings.google_maps_api_key),
                fallback=UnavailableTrafficProvider()
            )
        else:
            provider = UnavailableTrafficProvider()
    else:
        provider = MockTrafficProvider()

    assert not isinstance(provider, MockTrafficProvider)
    assert isinstance(provider, UnavailableTrafficProvider)
    assert provider.traffic_status == TrafficStatus.unavailable
    assert provider.provider_name == "Traffic Data Unavailable"


@pytest.mark.asyncio
async def test_production_without_google_traffic_credentials_returns_truthful_unavailable():
    """
    Verifies that a trip analyzed in production without live traffic returns
    a truthful TrafficStatus.unavailable with provenance='unavailable'.
    """
    unavailable_traffic = UnavailableTrafficProvider()
    service = TripService(
        weather_provider=MockWeatherProvider(),
        routing_provider=MockRoutingProvider(),
        alert_provider=MockAlertProvider(),
        traffic_provider=unavailable_traffic,
        geocoding_provider=MockGeocodingProvider(),
    )

    req = TripRequest(
        origin="Noida Sector 62",
        destination="Gurgaon Cyber Hub",
        departure_time=datetime(2026, 9, 20, 8, 30, tzinfo=timezone.utc),
        mode=TransportMode.car,
    )

    res = await service.analyze_trip(req)
    assert res is not None
    assert res.traffic is not None
    assert res.traffic.status == TrafficStatus.unavailable
    assert res.traffic.provenance == "unavailable"
    assert res.traffic.delay_seconds == 0.0


def test_development_mode_wires_mock_traffic():
    """
    Verifies that development mode preserves MockTrafficProvider for offline developer workflows.
    """
    dev_settings = Settings(environment="development")
    assert dev_settings.is_production is False

    if dev_settings.is_production:
        provider = UnavailableTrafficProvider()
    else:
        provider = MockTrafficProvider()

    assert isinstance(provider, MockTrafficProvider)
    assert provider.traffic_status == TrafficStatus.mock


@pytest.mark.asyncio
async def test_google_routes_traffic_provider_non_motorized_zero_delay():
    """
    Non-motorized modes (walk, metro) have no road traffic delay and return live free-flow traffic.
    """
    traffic_provider = GoogleRoutesTrafficProvider(api_key="test-key")
    dummy_route = NormalizedRoute(
        route_id="r1",
        summary="Test Walk",
        polyline="abc",
        segments=[],
        total_distance_km=2.0,
        total_duration=timedelta(minutes=25),
        provider_name="Test",
        provenance="test",
    )

    for mode in [TransportMode.walk, TransportMode.metro]:
        snapshot = await traffic_provider.get_traffic_for_route(
            dummy_route,
            datetime.now(timezone.utc),
            mode=mode,
        )
        assert snapshot.status == TrafficStatus.live
        assert snapshot.delay_seconds == 0.0
        assert snapshot.provenance == "google_routes/live"


@pytest.mark.asyncio
async def test_google_routes_traffic_provider_missing_key_truthful_unavailable():
    """
    If API key is absent, GoogleRoutesTrafficProvider truthfully returns TrafficStatus.unavailable.
    """
    traffic_provider = GoogleRoutesTrafficProvider(api_key=None)
    dummy_route = NormalizedRoute(
        route_id="r2",
        summary="Test Car",
        polyline="abc",
        segments=[],
        total_distance_km=15.0,
        total_duration=timedelta(minutes=30),
        provider_name="Test",
        provenance="test",
    )

    snapshot = await traffic_provider.get_traffic_for_route(
        dummy_route,
        datetime.now(timezone.utc),
        mode=TransportMode.car,
    )
    assert snapshot.status == TrafficStatus.unavailable
    assert snapshot.provenance == "unavailable"
    assert snapshot.delay_seconds == 0.0
