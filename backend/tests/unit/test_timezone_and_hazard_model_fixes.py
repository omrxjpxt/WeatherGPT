import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock

from app.models.trip import TripRequest
from app.models.enums import TransportMode, AlertSeverity, HazardType, HazardSourceClass
from app.decision_engine.normalized_models import (
    NormalizedRoute,
    NormalizedRouteSegment,
    NormalizedWeatherPoint,
    NormalizedHazard,
    NormalizedAlert,
)
from app.decision_engine.uncertainty import calculate_confidence
from app.decision_engine.source_comparison import AgreementStatus
from app.decision_engine.alert_override import check_alert_override
from app.decision_engine.temporal_alignment import align_route_with_weather
from app.services.trip_service import TripService
from app.repositories.hazard_repository import HazardRepository
from app.providers.weather.base import WeatherProvider
from app.providers.routing.base import RoutingProvider
from app.providers.alerts.base import AlertProvider
from app.providers.traffic.base import TrafficProvider
from app.providers.geocoding.base import GeocodingProvider, GeocodingResult, GeocodingResultType, GeocodingProvenance


def test_trip_request_normalizes_naive_datetime():
    # Naive datetime
    naive_dt = datetime(2026, 9, 20, 10, 0)
    req = TripRequest(
        origin="Noida Sector 62",
        destination="Gurgaon Cyber Hub",
        departure_time=naive_dt,
        mode=TransportMode.bike,
    )
    assert req.departure_time.tzinfo == timezone.utc
    assert req.departure_time.year == 2026
    assert req.departure_time.hour == 10

    # Aware datetime (e.g. UTC)
    aware_dt = datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc)
    req2 = TripRequest(
        origin="Noida Sector 62",
        destination="Gurgaon Cyber Hub",
        departure_time=aware_dt,
        mode=TransportMode.car,
    )
    assert req2.departure_time.tzinfo == timezone.utc


def test_uncertainty_calculate_confidence_with_naive_datetime():
    now_utc = datetime.now(timezone.utc)
    naive_dt = datetime(now_utc.year, now_utc.month, now_utc.day, now_utc.hour, now_utc.minute) + timedelta(hours=2)
    conf = calculate_confidence(naive_dt, AgreementStatus.high)
    level_val = conf.level.value if hasattr(conf.level, "value") else str(conf.level)
    assert level_val in ("high", "medium", "low")

    aware_dt = now_utc + timedelta(hours=2)
    conf_aware = calculate_confidence(aware_dt, AgreementStatus.high)
    level_aware_val = conf_aware.level.value if hasattr(conf_aware.level, "value") else str(conf_aware.level)
    assert level_aware_val in ("high", "medium", "low")


def test_alert_override_with_naive_datetime():
    seg = NormalizedRouteSegment(
        start_lat=28.6, start_lng=77.3,
        end_lat=28.7, end_lng=77.4,
        estimated_duration=timedelta(minutes=15),
        distance_km=10.0
    )
    route = NormalizedRoute(
        route_id="route-1",
        summary="Test Route",
        total_duration=timedelta(minutes=15),
        total_distance_km=10.0,
        polyline="test",
        segments=[seg]
    )
    now_utc = datetime.now(timezone.utc)
    alert = NormalizedAlert(
        id="alert-1",
        severity=AlertSeverity.warning,
        title="Test Storm Alert",
        description="Severe storm expected",
        source_name="NDMA",
        source_class="authoritative",
        issued_at=now_utc - timedelta(hours=1),
        expires_at=now_utc + timedelta(hours=3),
        affected_areas_polygon=[],
        is_override_eligible=True,
    )

    # Test with naive travel times aligned with current UTC time
    t_start_naive = datetime(now_utc.year, now_utc.month, now_utc.day, now_utc.hour, now_utc.minute)
    t_end_naive = t_start_naive + timedelta(minutes=30)
    override, is_exact = check_alert_override([alert], route, t_start_naive, t_end_naive)
    assert override is not None
    assert override.id == "alert-1"


def test_temporal_alignment_with_naive_target_time():
    seg = NormalizedRouteSegment(
        start_lat=28.6, start_lng=77.3,
        end_lat=28.7, end_lng=77.4,
        estimated_duration=timedelta(minutes=15),
        distance_km=10.0
    )
    route = NormalizedRoute(
        route_id="route-1",
        summary="Test Route",
        total_duration=timedelta(minutes=15),
        total_distance_km=10.0,
        polyline="test",
        segments=[seg]
    )
    wp = NormalizedWeatherPoint(
        time=datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc),
        temperature=30.0,
        precipitation_mm=0.0,
        humidity=60.0,
        wind_speed=10.0,
        wind_gusts=15.0,
        visibility=5000.0,
        condition="Clear",
        is_extreme_heat=False,
        is_poor_visibility=False,
    )

    naive_dep = datetime(2026, 9, 20, 10, 0)
    aligned = align_route_with_weather(route, naive_dep, [wp])
    assert len(aligned) == 1
    assert aligned[0][2].condition == "Clear"


class MockHazardRepo(HazardRepository):
    def __init__(self, hazards):
        self.hazards = hazards

    async def get_hazards_in_region(self, min_lat, min_lng, max_lat, max_lng):
        return self.hazards


@pytest.mark.asyncio
async def test_crit1_active_hazards_do_not_crash_multi_mode_evaluation():
    """
    Regression test for CRIT-1:
    Verifies that when NormalizedHazards are present in the corridor,
    TripService properly passes NormalizedHazard (not Hazard) to secondary modes,
    producing bike, car, and metro in mode_options without raising AttributeError.
    """
    mock_weather = AsyncMock(spec=WeatherProvider)
    mock_weather.provider_name = "Mock Weather"
    mock_weather.get_forecast.return_value = [
        NormalizedWeatherPoint(
            time=datetime(2026, 9, 20, 8, 0, tzinfo=timezone.utc),
            temperature=28.0,
            precipitation_mm=40.0,  # High rain to trigger waterlogging
            humidity=80.0,
            wind_speed=15.0,
            wind_gusts=20.0,
            visibility=3000.0,
            condition="Heavy Rain",
            is_extreme_heat=False,
            is_poor_visibility=False,
        )
    ]

    road_seg = NormalizedRouteSegment(
        start_lat=28.6270, start_lng=77.3650,
        end_lat=28.6300, end_lng=77.3700,
        estimated_duration=timedelta(minutes=30),
        distance_km=15.0
    )
    road_route = NormalizedRoute(
        route_id="road-route-1",
        summary="Road Arterial",
        total_duration=timedelta(minutes=30),
        total_distance_km=15.0,
        polyline="abc",
        segments=[road_seg]
    )

    metro_seg = NormalizedRouteSegment(
        start_lat=28.6270, start_lng=77.3650,
        end_lat=28.6300, end_lng=77.3700,
        estimated_duration=timedelta(minutes=35),
        distance_km=16.0
    )
    metro_route = NormalizedRoute(
        route_id="dmrc-metro-blue-yellow",
        summary="DMRC Metro Route",
        total_duration=timedelta(minutes=35),
        total_distance_km=16.0,
        polyline="def",
        segments=[metro_seg]
    )

    mock_routing = AsyncMock(spec=RoutingProvider)
    mock_routing.provider_name = "Mock Routing"
    mock_routing.route_status.value = "live"
    mock_routing.get_route.return_value = [road_route]

    mock_metro = AsyncMock(spec=RoutingProvider)
    mock_metro.provider_name = "DMRC Metro"
    mock_metro.route_status.value = "live"
    mock_metro.get_route.return_value = [metro_route]

    mock_alerts = AsyncMock(spec=AlertProvider)
    mock_alerts.provider_name = "Mock Alerts"
    mock_alerts.get_active_alerts.return_value = []

    mock_traffic = AsyncMock(spec=TrafficProvider)
    mock_traffic.provider_name = "Mock Traffic"
    from app.models.traffic import TrafficSnapshot
    mock_traffic.get_traffic_for_route.return_value = TrafficSnapshot(
        status="live",
        condition="clear",
        congestion_level="free_flow",
        delay_seconds=0.0,
        static_duration=road_route.total_duration,
        traffic_aware_duration=road_route.total_duration,
        timestamp=datetime.now(timezone.utc),
        source_name="Mock",
        provenance="google_routes/live"
    )

    mock_geocoding = AsyncMock(spec=GeocodingProvider)
    mock_geocoding.geocode.side_effect = lambda q: GeocodingResult(
        query=q,
        lat=28.6270,
        lng=77.3650,
        display_name=q,
        provider="MockGeocoder",
        result_type=GeocodingResultType.CITY_LOCALITY,
        confidence=0.95,
        is_exact=True,
        timestamp=datetime.now(timezone.utc),
        provenance=GeocodingProvenance.OFFLINE_CURATED,
    )

    # Active waterlogging hazard right on the segment
    active_hazard = NormalizedHazard(
        id="pwd-hotspot-1",
        type=HazardType.waterlogging,
        lat=28.6280,
        lng=77.3670,
        radius_meters=500.0,
        base_severity=85,
        source_name="Delhi PWD",
        source_class=HazardSourceClass.government_open_data,
        trigger_precipitation_mm=15.0,
        is_underpass=True,
        chronic=True,
        location_name="Hotspot 1"
    )

    hazard_repo = MockHazardRepo([active_hazard])

    service = TripService(
        weather_provider=mock_weather,
        routing_provider=mock_routing,
        alert_provider=mock_alerts,
        traffic_provider=mock_traffic,
        hazard_repository=hazard_repo,
        geocoding_provider=mock_geocoding,
        metro_provider=mock_metro,
    )

    req = TripRequest(
        origin="Noida Sector 62",
        destination="Gurgaon Cyber Hub",
        departure_time=datetime(2026, 9, 20, 8, 30),  # Naive timestamp test as well!
        mode=TransportMode.car,
    )

    response = await service.analyze_trip(req)

    # 1. Primary route contains the active hazard
    assert len(response.hazards) > 0

    # 2. All 3 modes are evaluated without crashing
    mode_types = [m.mode for m in response.mode_options]
    assert TransportMode.bike in mode_types
    assert TransportMode.car in mode_types
    assert TransportMode.metro in mode_types

    # 3. Metro option is unaffected by street waterlogging
    metro_opt = next(m for m in response.mode_options if m.mode == TransportMode.metro)
    assert metro_opt.risk is not None
    # Metro has lower risk than bike in heavy rain + waterlogging
    bike_opt = next(m for m in response.mode_options if m.mode == TransportMode.bike)
    assert bike_opt.risk is not None
    assert metro_opt.risk.overall_score < bike_opt.risk.overall_score
