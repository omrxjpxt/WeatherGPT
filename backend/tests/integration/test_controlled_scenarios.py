import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from app.models.trip import TripRequest, TripResponse
from app.models.enums import (
    TransportMode,
    TripStatus,
    RiskLevel,
    TrafficStatus,
    AlertSeverity,
    AlertSourceClass,
    RouteStatus,
    CongestionLevel,
    TrafficCondition,
)
from app.models.weather import WeatherPoint
from app.models.traffic import TrafficSnapshot
from app.models.hazard import Hazard
from app.models.alert import OfficialAlert
from app.decision_engine.normalized_models import (
    NormalizedRoute,
    NormalizedRouteSegment,
    NormalizedWeatherPoint,
    NormalizedHazard,
    NormalizedAlert,
    HazardRelevanceResult,
)
from app.services.trip_service import TripService
from app.providers.weather.open_meteo import OpenMeteoWeatherProvider
from app.providers.weather.base import WeatherProvider
from app.providers.routing.base import RoutingProvider
from app.providers.routing.mock import MockRoutingProvider
from app.providers.routing.errors import ConfigurationError
from app.providers.traffic.base import TrafficProvider
from app.providers.traffic.mock import MockTrafficProvider
from app.providers.traffic.fallback import UnavailableTrafficProvider
from app.providers.alerts.base import AlertProvider
from app.providers.alerts.mock import MockAlertProvider
from app.repositories.mock_hazard_repository import MockHazardRepository
from app.decision_engine.route_evaluator import RouteEvaluator


class FailingWeatherProvider(WeatherProvider):
    @property
    def provider_name(self) -> str:
        return "Failing Weather Provider"

    async def get_forecast(self, lat: float, lng: float, start_time: datetime, hours: int) -> List[NormalizedWeatherPoint]:
        raise RuntimeError("Weather service down")


class FailingRoutingProvider(RoutingProvider):
    @property
    def provider_name(self) -> str:
        return "Failing Routing Provider"

    @property
    def route_status(self) -> RouteStatus:
        return RouteStatus.unavailable

    async def get_route(self, origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float, mode: TransportMode) -> List[NormalizedRoute]:
        raise ConfigurationError("Routing provider misconfigured or unavailable")


def create_weather_timeline(base_time: datetime, count: int = 10, condition: str = "Clear", precip: float = 0.0) -> List[NormalizedWeatherPoint]:
    timeline = []
    for i in range(count):
        t = base_time + timedelta(minutes=15 * i)
        timeline.append(NormalizedWeatherPoint(
            time=t,
            temperature=28.0,
            precipitation_mm=precip,
            humidity=60,
            wind_speed=10.0,
            wind_gusts=15.0,
            visibility=10000.0,
            condition=condition,
            is_extreme_heat=False,
            is_poor_visibility=False
        ))
    return timeline


def create_test_route(route_id: str, summary: str, distance_km: float, duration_mins: float, status: RouteStatus = RouteStatus.live) -> NormalizedRoute:
    return NormalizedRoute(
        route_id=route_id,
        summary=summary,
        segments=[
            NormalizedRouteSegment(
                start_lat=28.6270, start_lng=77.3650,
                end_lat=28.5850, end_lng=77.3200,
                distance_km=distance_km / 2.0,
                estimated_duration=timedelta(minutes=duration_mins / 2.0)
            ),
            NormalizedRouteSegment(
                start_lat=28.5850, start_lng=77.3200,
                end_lat=28.4942, end_lng=77.0860,
                distance_km=distance_km / 2.0,
                estimated_duration=timedelta(minutes=duration_mins / 2.0)
            ),
        ],
        total_distance_km=distance_km,
        total_duration=timedelta(minutes=duration_mins),
        provider_name="Mock Routing API",
        provenance="demo/mock"
    )


def create_traffic_snapshot(route: NormalizedRoute, delay_mins: float, base_time: datetime) -> TrafficSnapshot:
    static_dur = route.total_duration
    delay_sec = float(delay_mins * 60)
    aware_dur = static_dur + timedelta(seconds=delay_sec)
    return TrafficSnapshot(
        status=TrafficStatus.mock,
        condition=TrafficCondition.congested if delay_mins > 5 else TrafficCondition.clear,
        congestion_level=CongestionLevel.heavy if delay_mins >= 10 else (CongestionLevel.moderate if delay_mins > 0 else CongestionLevel.free_flow),
        delay_seconds=delay_sec,
        static_duration=static_dur,
        traffic_aware_duration=aware_dur,
        current_speed_kmh=40.0,
        freeFlowSpeedKmh=50.0,
        timestamp=base_time,
        source_name="Mock Traffic Provider (Demo)",
        provenance="demo/mock"
    )


# Scenario 1: successful live weather + route
@pytest.mark.asyncio
async def test_scenario_1_successful_live_weather_and_route():
    service = TripService(
        weather_provider=OpenMeteoWeatherProvider(),
        routing_provider=MockRoutingProvider(route_count=1),
        alert_provider=MockAlertProvider(),
        traffic_provider=MockTrafficProvider(),
        hazard_repository=MockHazardRepository()
    )
    req = TripRequest(
        origin="Noida Sector 62",
        destination="Gurgaon Cyber Hub",
        departure_time=datetime.now(timezone.utc),
        mode=TransportMode.car
    )
    res = await service.analyze_trip(req)
    assert res.status == TripStatus.success
    assert res.risk is not None
    assert len(res.routes) == 1
    assert any("Open-Meteo" in s.name for s in res.sources)
    assert not any("authoritative" in s.name.lower() and "open-meteo" in s.name.lower() for s in res.sources)


# Scenario 2: live weather + routing unavailable
@pytest.mark.asyncio
async def test_scenario_2_live_weather_routing_unavailable():
    service = TripService(
        weather_provider=OpenMeteoWeatherProvider(),
        routing_provider=FailingRoutingProvider(),
        alert_provider=MockAlertProvider(),
        traffic_provider=MockTrafficProvider(),
        hazard_repository=MockHazardRepository()
    )
    req = TripRequest(
        origin="Noida Sector 62",
        destination="Gurgaon Cyber Hub",
        departure_time=datetime.now(timezone.utc),
        mode=TransportMode.car
    )
    res = await service.analyze_trip(req)
    assert res.status == TripStatus.routing_unavailable
    assert res.risk is None
    assert len(res.routes) == 0
    assert any("Routing [unavailable]" in s.type for s in res.sources)


# Scenario 3: weather unavailable
@pytest.mark.asyncio
async def test_scenario_3_weather_unavailable():
    service = TripService(
        weather_provider=FailingWeatherProvider(),
        routing_provider=MockRoutingProvider(),
        alert_provider=MockAlertProvider(),
        traffic_provider=MockTrafficProvider(),
        hazard_repository=MockHazardRepository()
    )
    req = TripRequest(
        origin="Noida Sector 62",
        destination="Gurgaon Cyber Hub",
        departure_time=datetime.now(timezone.utc),
        mode=TransportMode.car
    )
    res = await service.analyze_trip(req)
    assert res.status == TripStatus.weather_unavailable
    assert res.risk is None
    assert len(res.routes) == 0


# Scenario 4: traffic unavailable
@pytest.mark.asyncio
async def test_scenario_4_traffic_unavailable():
    service = TripService(
        weather_provider=OpenMeteoWeatherProvider(),
        routing_provider=MockRoutingProvider(route_count=1),
        alert_provider=MockAlertProvider(),
        traffic_provider=UnavailableTrafficProvider(),
        hazard_repository=MockHazardRepository()
    )
    req = TripRequest(
        origin="Noida Sector 62",
        destination="Gurgaon Cyber Hub",
        departure_time=datetime.now(timezone.utc),
        mode=TransportMode.car
    )
    res = await service.analyze_trip(req)
    assert res.status == TripStatus.success
    assert res.traffic is not None
    assert res.traffic.status == TrafficStatus.unavailable
    assert any("Traffic [unavailable]" in s.type for s in res.sources)
    assert res.traffic.delay_seconds == 0.0


# Scenario 5: multiple routes
@pytest.mark.asyncio
async def test_scenario_5_multiple_routes():
    service = TripService(
        weather_provider=OpenMeteoWeatherProvider(),
        routing_provider=MockRoutingProvider(route_count=3),
        alert_provider=MockAlertProvider(),
        traffic_provider=MockTrafficProvider(),
        hazard_repository=MockHazardRepository()
    )
    req = TripRequest(
        origin="Noida Sector 62",
        destination="Gurgaon Cyber Hub",
        departure_time=datetime.now(timezone.utc),
        mode=TransportMode.car
    )
    res = await service.analyze_trip(req)
    assert res.status == TripStatus.success
    assert len(res.routes) == 3
    selected_routes = [r for r in res.routes if r.evaluation.is_selected]
    assert len(selected_routes) == 1
    assert selected_routes[0].evaluation.selection_reason is not None


# Scenario 6: different traffic delays per route
@pytest.mark.asyncio
async def test_scenario_6_different_traffic_delays_per_route():
    evaluator = RouteEvaluator()
    base_time = datetime(2026, 9, 18, 8, 0, tzinfo=timezone.utc)
    weather = create_weather_timeline(base_time)
    req = TripRequest(origin="Noida", destination="Gurgaon", departure_time=base_time, mode=TransportMode.car)

    ra = create_test_route("ra", "Route A", distance_km=30.0, duration_mins=25)
    rb = create_test_route("rb", "Route B", distance_km=32.0, duration_mins=27)

    # Route A gets 12 mins delay -> 37 mins total
    # Route B gets 2 mins delay -> 29 mins total
    ta = create_traffic_snapshot(ra, delay_mins=12, base_time=base_time)
    tb = create_traffic_snapshot(rb, delay_mins=2, base_time=base_time)

    ea = evaluator.evaluate_route(ra, req, weather, [], [], ta)
    eb = evaluator.evaluate_route(rb, req, weather, [], [], tb)

    selected, ranked = evaluator.select_and_rank_routes([ea, eb], base_time)
    # Since both have low risk, shorter traffic-aware duration wins (Route B: 29m vs Route A: 37m)
    assert selected.route_id == "rb"
    assert selected.evaluation.is_selected is True
    assert ranked[1].route_id == "ra"
    assert ranked[1].evaluation.is_selected is False


# Scenario 7: hazard-relevant route
@pytest.mark.asyncio
async def test_scenario_7_hazard_relevant_route():
    service = TripService(
        weather_provider=OpenMeteoWeatherProvider(),
        routing_provider=MockRoutingProvider(route_count=1),
        alert_provider=MockAlertProvider(),
        traffic_provider=MockTrafficProvider(),
        hazard_repository=MockHazardRepository()
    )
    req = TripRequest(
        origin="Noida Sector 62",
        destination="Gurgaon Cyber Hub",
        departure_time=datetime.now(timezone.utc),
        mode=TransportMode.car
    )
    res = await service.analyze_trip(req)
    assert res.status == TripStatus.success
    assert isinstance(res.hazards, list)


# Scenario 8: alert-relevant route
@pytest.mark.asyncio
async def test_scenario_8_alert_relevant_route():
    evaluator = RouteEvaluator()
    base_time = datetime(2026, 9, 18, 8, 0, tzinfo=timezone.utc)
    weather = create_weather_timeline(base_time)
    req = TripRequest(origin="Noida", destination="Gurgaon", departure_time=base_time, mode=TransportMode.car)

    ra = create_test_route("ra", "Route A", distance_km=30.0, duration_mins=30)
    rb = create_test_route("rb", "Route B", distance_km=30.0, duration_mins=30)

    hard_alert = NormalizedAlert(
        id="alert_closure",
        source_name="State Police",
        source_class=AlertSourceClass.authoritative,
        severity=AlertSeverity.emergency,
        affected_areas_polygon=[],
        issued_at=base_time,
        expires_at=base_time + timedelta(hours=5),
        action="Evacuate and close expressway",
        is_override_eligible=True
    )

    ea = evaluator.evaluate_route(ra, req, weather, [], [hard_alert], None)
    eb = evaluator.evaluate_route(rb, req, weather, [], [], None)

    selected, ranked = evaluator.select_and_rank_routes([ea, eb], base_time)
    assert selected.route_id == "rb"
    assert ranked[1].route_id == "ra"
    assert "emergency" in ranked[1].evaluation.selection_reason.lower() or "alert" in ranked[1].evaluation.selection_reason.lower()


# Scenario 9: arrival deadline
@pytest.mark.asyncio
async def test_scenario_9_arrival_deadline():
    evaluator = RouteEvaluator()
    base_time = datetime(2026, 9, 18, 8, 0, tzinfo=timezone.utc)
    weather = create_weather_timeline(base_time)
    deadline = base_time + timedelta(minutes=45)
    req = TripRequest(
        origin="Noida",
        destination="Gurgaon",
        departure_time=base_time,
        mode=TransportMode.car,
        arrival_deadline=deadline
    )

    ra = create_test_route("ra", "Route A", distance_km=30.0, duration_mins=30)  # 30m <= 45m deadline
    rb = create_test_route("rb", "Route B", distance_km=30.0, duration_mins=60)  # 60m > 45m deadline

    ea = evaluator.evaluate_route(ra, req, weather, [], [], None)
    eb = evaluator.evaluate_route(rb, req, weather, [], [], None)

    assert ea.evaluation.is_feasible is True
    assert eb.evaluation.is_feasible is False

    selected, ranked = evaluator.select_and_rank_routes([ea, eb], base_time, arrival_deadline=deadline)
    assert selected.route_id == "ra"
    assert ranked[1].route_id == "rb"
    assert not ranked[1].evaluation.is_feasible


# Scenario 10: all routes infeasible
@pytest.mark.asyncio
async def test_scenario_10_all_routes_infeasible():
    evaluator = RouteEvaluator()
    base_time = datetime(2026, 9, 18, 8, 0, tzinfo=timezone.utc)
    weather = create_weather_timeline(base_time)
    deadline = base_time + timedelta(minutes=20)
    req = TripRequest(
        origin="Noida",
        destination="Gurgaon",
        departure_time=base_time,
        mode=TransportMode.car,
        arrival_deadline=deadline
    )

    ra = create_test_route("ra", "Route A", distance_km=30.0, duration_mins=35)  # > 20m
    rb = create_test_route("rb", "Route B", distance_km=30.0, duration_mins=45)  # > 20m

    ea = evaluator.evaluate_route(ra, req, weather, [], [], None)
    eb = evaluator.evaluate_route(rb, req, weather, [], [], None)

    assert ea.evaluation.is_feasible is False
    assert eb.evaluation.is_feasible is False

    selected, ranked = evaluator.select_and_rank_routes([ea, eb], base_time, arrival_deadline=deadline)
    assert len(ranked) == 2
    assert selected.route_id == "ra"
    assert selected.evaluation.is_feasible is False
