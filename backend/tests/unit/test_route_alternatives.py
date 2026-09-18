import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.models.enums import TransportMode, RiskLevel, AlertSeverity, AlertSourceClass, TrafficStatus, TrafficCondition, CongestionLevel
from app.models.trip import TripRequest, TripResponse
from app.models.traffic import TrafficSnapshot
from app.decision_engine.normalized_models import (
    NormalizedRoute,
    NormalizedRouteSegment,
    NormalizedWeatherPoint,
    NormalizedAlert,
    NormalizedHazard,
    HazardType,
    HazardSourceClass,
)
from app.decision_engine.route_evaluator import RouteEvaluator
from app.providers.routing.mock import MockRoutingProvider
from app.services.trip_service import TripService
from app.providers.traffic.mock import MockTrafficProvider

def create_weather_timeline(base_time: datetime) -> list[NormalizedWeatherPoint]:
    timeline = []
    for i in range(10):
        t = base_time + timedelta(minutes=15 * i)
        timeline.append(NormalizedWeatherPoint(
            time=t,
            temperature=28.0,
            precipitation_mm=0.0,
            humidity=60,
            wind_speed=10.0,
            wind_gusts=15.0,
            visibility=10000.0,
            condition="Clear",
            is_extreme_heat=False,
            is_poor_visibility=False
        ))
    return timeline

def create_test_route(route_id: str, summary: str, distance_km: float, duration_mins: int) -> NormalizedRoute:
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

def create_traffic_snapshot(route: NormalizedRoute, delay_mins: int) -> TrafficSnapshot:
    static_dur = route.total_duration
    delay_sec = float(delay_mins * 60)
    aware_dur = static_dur + timedelta(seconds=delay_sec)
    return TrafficSnapshot(
        status=TrafficStatus.mock,
        condition=TrafficCondition.congested if delay_mins > 5 else TrafficCondition.clear,
        congestion_level=CongestionLevel.heavy if delay_mins >= 10 else CongestionLevel.moderate if delay_mins > 0 else CongestionLevel.free_flow,
        delay_seconds=delay_sec,
        static_duration=static_dur,
        traffic_aware_duration=aware_dur,
        current_speed_kmh=40.0,
        freeFlowSpeedKmh=50.0,
        timestamp=datetime.now(timezone.utc),
        source_name="Mock Traffic Provider (Demo)",
        provenance="demo/mock"
    )

@pytest.mark.asyncio
async def test_mock_routing_provider_route_counts():
    provider = MockRoutingProvider(route_count=1)
    r1 = await provider.get_route(28.6270, 77.3650, 28.4942, 77.0860, TransportMode.car)
    assert len(r1) == 1
    assert r1[0].route_id == "mock_route_1"
    assert "Via Noida-Greater Noida" in r1[0].summary

    provider.set_route_count(2)
    r2 = await provider.get_route(28.6270, 77.3650, 28.4942, 77.0860, TransportMode.car)
    assert len(r2) == 2
    assert r2[1].route_id == "mock_route_2"
    assert "Via DND Flyway" in r2[1].summary

    provider.set_route_count(3)
    r3 = await provider.get_route(28.6270, 77.3650, 28.4942, 77.0860, TransportMode.car)
    assert len(r3) == 3
    assert r3[2].route_id == "mock_route_3"
    assert "Via Outer Ring Road" in r3[2].summary

def test_different_risk_tiers_selection():
    evaluator = RouteEvaluator()
    base_time = datetime(2026, 9, 18, 8, 0, tzinfo=timezone.utc)
    weather = create_weather_timeline(base_time)
    request = TripRequest(origin="Noida", destination="Gurgaon", departure_time=base_time, mode=TransportMode.car)

    route_a = create_test_route("route_a", "Route A", 30.0, 30)
    traffic_a = create_traffic_snapshot(route_a, delay_mins=0)

    # Route B through weather with rain to force different risk tier
    route_b = create_test_route("route_b", "Route B", 30.0, 25)
    traffic_b = create_traffic_snapshot(route_b, delay_mins=0)

    eval_a = evaluator.evaluate_route(route_a, request, weather, [], [], traffic_a)
    # Force a higher risk tier on Route B
    eval_b = evaluator.evaluate_route(route_b, request, weather, [], [], traffic_b)
    eval_b.evaluation.risk_level = RiskLevel.high
    eval_b.evaluation.risk_score = 75

    eval_a.evaluation.risk_level = RiskLevel.low
    eval_a.evaluation.risk_score = 20

    selected, ranked = evaluator.select_and_rank_routes([eval_b, eval_a], base_time)
    assert selected.route_id == "route_a"
    assert selected.evaluation.is_selected is True
    assert "Higher risk tier" in ranked[1].evaluation.selection_reason

def test_same_tier_large_risk_difference_selection():
    evaluator = RouteEvaluator()
    base_time = datetime(2026, 9, 18, 8, 0, tzinfo=timezone.utc)
    weather = create_weather_timeline(base_time)
    request = TripRequest(origin="Noida", destination="Gurgaon", departure_time=base_time, mode=TransportMode.car)

    route_a = create_test_route("route_a", "Route A", 30.0, 40)
    route_b = create_test_route("route_b", "Route B", 30.0, 30)

    eval_a = evaluator.evaluate_route(route_a, request, weather, [], [], create_traffic_snapshot(route_a, 0))
    eval_b = evaluator.evaluate_route(route_b, request, weather, [], [], create_traffic_snapshot(route_b, 0))

    # Same tier: Moderate, but diff >= 15
    eval_a.evaluation.risk_level = RiskLevel.moderate
    eval_a.evaluation.risk_score = 42
    eval_b.evaluation.risk_level = RiskLevel.moderate
    eval_b.evaluation.risk_score = 62  # 62 - 42 = 20 >= 15

    selected, ranked = evaluator.select_and_rank_routes([eval_b, eval_a], base_time)
    assert selected.route_id == "route_a"
    assert "+20 higher risk score" in ranked[1].evaluation.selection_reason

def test_same_tier_small_risk_difference_traffic_duration_selection():
    """
    Test user example:
    Route A: 22 min static + 12 min traffic = 34 min effective travel time
    Route B: 27 min static + 2 min traffic = 29 min effective travel time
    Both in same risk tier and risk difference < 15 -> Route B is selected (29m < 34m)!
    """
    evaluator = RouteEvaluator()
    base_time = datetime(2026, 9, 18, 8, 0, tzinfo=timezone.utc)
    weather = create_weather_timeline(base_time)
    request = TripRequest(origin="Noida", destination="Gurgaon", departure_time=base_time, mode=TransportMode.car)

    route_a = create_test_route("route_a", "Route A", 25.0, 22)
    traffic_a = create_traffic_snapshot(route_a, delay_mins=12) # 22 + 12 = 34 min

    route_b = create_test_route("route_b", "Route B", 28.0, 27)
    traffic_b = create_traffic_snapshot(route_b, delay_mins=2) # 27 + 2 = 29 min

    eval_a = evaluator.evaluate_route(route_a, request, weather, [], [], traffic_a)
    eval_b = evaluator.evaluate_route(route_b, request, weather, [], [], traffic_b)

    # Both Moderate risk, small difference (< 15)
    eval_a.evaluation.risk_level = RiskLevel.moderate
    eval_a.evaluation.risk_score = 42
    eval_b.evaluation.risk_level = RiskLevel.moderate
    eval_b.evaluation.risk_score = 45 # Diff = 3 < 15

    selected, ranked = evaluator.select_and_rank_routes([eval_a, eval_b], base_time)
    assert selected.route_id == "route_b"
    assert selected.evaluation.traffic_aware_duration == timedelta(minutes=29)
    assert "5 min slower effective travel time" in ranked[1].evaluation.selection_reason

def test_deadline_filtering():
    evaluator = RouteEvaluator()
    base_time = datetime(2026, 9, 18, 8, 0, tzinfo=timezone.utc)
    deadline = base_time + timedelta(minutes=45) # Must arrive by 08:45
    weather = create_weather_timeline(base_time)
    request = TripRequest(origin="Noida", destination="Gurgaon", departure_time=base_time, arrival_deadline=deadline, mode=TransportMode.car)

    # Route A: 35 min total (arrives 08:35 <= 08:45) -> Feasible
    route_a = create_test_route("route_a", "Route A", 30.0, 35)
    eval_a = evaluator.evaluate_route(route_a, request, weather, [], [], create_traffic_snapshot(route_a, 0))

    # Route B: 55 min total (arrives 08:55 > 08:45) -> Infeasible
    route_b = create_test_route("route_b", "Route B", 35.0, 55)
    eval_b = evaluator.evaluate_route(route_b, request, weather, [], [], create_traffic_snapshot(route_b, 0))

    assert eval_a.evaluation.is_feasible is True
    assert eval_b.evaluation.is_feasible is False
    assert "exceeds requested deadline" in eval_b.evaluation.feasibility_reason

    selected, ranked = evaluator.select_and_rank_routes([eval_b, eval_a], base_time, deadline)
    assert selected.route_id == "route_a"
    assert "Infeasible:" in ranked[1].evaluation.selection_reason

def test_all_routes_infeasible_retained():
    evaluator = RouteEvaluator()
    base_time = datetime(2026, 9, 18, 8, 0, tzinfo=timezone.utc)
    deadline = base_time + timedelta(minutes=20) # Impossible deadline
    weather = create_weather_timeline(base_time)
    request = TripRequest(origin="Noida", destination="Gurgaon", departure_time=base_time, arrival_deadline=deadline, mode=TransportMode.car)

    route_a = create_test_route("route_a", "Route A", 30.0, 35)
    route_b = create_test_route("route_b", "Route B", 30.0, 45)

    eval_a = evaluator.evaluate_route(route_a, request, weather, [], [], create_traffic_snapshot(route_a, 0))
    eval_b = evaluator.evaluate_route(route_b, request, weather, [], [], create_traffic_snapshot(route_b, 0))

    assert eval_a.evaluation.is_feasible is False
    assert eval_b.evaluation.is_feasible is False

    # When all are infeasible, system does not crash and selects best effort
    selected, ranked = evaluator.select_and_rank_routes([eval_b, eval_a], base_time, deadline)
    assert selected is not None
    assert len(ranked) == 2

def test_hard_alert_avoidance():
    evaluator = RouteEvaluator()
    base_time = datetime(2026, 9, 18, 8, 0, tzinfo=timezone.utc)
    weather = create_weather_timeline(base_time)
    request = TripRequest(origin="Noida", destination="Gurgaon", departure_time=base_time, mode=TransportMode.car)

    route_a = create_test_route("route_a", "Route A", 30.0, 30)
    route_b = create_test_route("route_b", "Route B", 30.0, 35)

    eval_a = evaluator.evaluate_route(route_a, request, weather, [], [], create_traffic_snapshot(route_a, 0))
    eval_b = evaluator.evaluate_route(route_b, request, weather, [], [], create_traffic_snapshot(route_b, 0))

    # Route A has active evacuation / closure alert
    eval_a.evaluation.recommendation_headline = "Emergency Flood Evacuation"
    eval_a.evaluation.recommendation_body = "Road closure ordered due to deep floodwater. Avoid this route."

    selected, ranked = evaluator.select_and_rank_routes([eval_a, eval_b], base_time)
    assert selected.route_id == "route_b"
    assert "emergency alert/closure" in ranked[1].evaluation.selection_reason

def test_advisory_alert_handling():
    evaluator = RouteEvaluator()
    base_time = datetime(2026, 9, 18, 8, 0, tzinfo=timezone.utc)
    weather = create_weather_timeline(base_time)
    request = TripRequest(origin="Noida", destination="Gurgaon", departure_time=base_time, mode=TransportMode.car)

    route_a = create_test_route("route_a", "Route A", 30.0, 30)
    route_b = create_test_route("route_b", "Route B", 30.0, 45)

    eval_a = evaluator.evaluate_route(route_a, request, weather, [], [], create_traffic_snapshot(route_a, 0))
    eval_b = evaluator.evaluate_route(route_b, request, weather, [], [], create_traffic_snapshot(route_b, 0))

    # Route A has mild advisory (e.g. rain advisory with Proceed with caution)
    eval_a.evaluation.risk_level = RiskLevel.low
    eval_a.evaluation.risk_score = 25
    eval_a.evaluation.recommendation_headline = "Proceed with caution"
    eval_a.evaluation.recommendation_body = "Light rain advisory along corridor."

    eval_b.evaluation.risk_level = RiskLevel.moderate
    eval_b.evaluation.risk_score = 45

    # Advisory alert does NOT disqualify Route A
    selected, ranked = evaluator.select_and_rank_routes([eval_a, eval_b], base_time)
    assert selected.route_id == "route_a"

def test_all_routes_affected_by_hard_alert():
    evaluator = RouteEvaluator()
    base_time = datetime(2026, 9, 18, 8, 0, tzinfo=timezone.utc)
    weather = create_weather_timeline(base_time)
    request = TripRequest(origin="Noida", destination="Gurgaon", departure_time=base_time, mode=TransportMode.car)

    route_a = create_test_route("route_a", "Route A", 30.0, 30)
    route_b = create_test_route("route_b", "Route B", 30.0, 35)

    eval_a = evaluator.evaluate_route(route_a, request, weather, [], [], create_traffic_snapshot(route_a, 0))
    eval_b = evaluator.evaluate_route(route_b, request, weather, [], [], create_traffic_snapshot(route_b, 0))

    eval_a.evaluation.recommendation_headline = "Emergency Alert"
    eval_a.evaluation.recommendation_body = "Regional emergency: avoid travel."
    eval_b.evaluation.recommendation_headline = "Emergency Alert"
    eval_b.evaluation.recommendation_body = "Regional emergency: avoid travel."

    # Both routes retained without crash
    selected, ranked = evaluator.select_and_rank_routes([eval_a, eval_b], base_time)
    assert selected is not None
    assert len(ranked) == 2

@pytest.mark.asyncio
async def test_existing_traffic_data_reused_without_duplicate_provider_call():
    """
    Verifies that when NormalizedRoute already has verified traffic data (e.g. Google Routes),
    TripService reuses it directly without calling TrafficProvider (Prevent N+1 calls).
    """
    mock_traffic_provider = MagicMock(spec=MockTrafficProvider)
    mock_traffic_provider.get_traffic_for_route = AsyncMock()

    mock_weather = MagicMock()
    mock_weather.provider_name = "Mock Weather"
    mock_weather.get_forecast = AsyncMock(return_value=create_weather_timeline(datetime.now(timezone.utc)))

    mock_alert = MagicMock()
    mock_alert.provider_name = "Mock Alerts"
    mock_alert.provider_class = MagicMock(value="demo")
    mock_alert.get_active_alerts = AsyncMock(return_value=[])

    # Create a route that already has verified traffic attached
    route_with_traffic = create_test_route("route_pre_traffic", "Route Pre", 30.0, 30)
    embedded_traffic = create_traffic_snapshot(route_with_traffic, delay_mins=5)
    route_with_traffic.traffic = embedded_traffic

    mock_routing = MagicMock()
    mock_routing.provider_name = "Pre-traffic Routing"
    mock_routing.route_status = MagicMock(value="live")
    mock_routing.get_route = AsyncMock(return_value=[route_with_traffic])

    service = TripService(
        weather_provider=mock_weather,
        routing_provider=mock_routing,
        alert_provider=mock_alert,
        traffic_provider=mock_traffic_provider
    )

    request = TripRequest(
        origin="Noida",
        destination="Gurgaon",
        departure_time=datetime.now(timezone.utc),
        mode=TransportMode.car
    )

    response = await service.analyze_trip(request)
    assert response.traffic is not None
    assert response.traffic.delay_seconds == 300.0

    # Traffic provider should NOT have been called because traffic was already on the route
    mock_traffic_provider.get_traffic_for_route.assert_not_called()

def test_backward_compatible_json_payloads_with_and_without_routes():
    # Legacy payload omitting 'routes'
    legacy_json = {
        "analysisId": "leg-123",
        "status": "success",
        "request": {
            "origin": "Noida",
            "destination": "Gurgaon",
            "departureTime": "2026-09-18T08:00:00Z",
            "mode": "car"
        },
        "risk": {
            "overallScore": 30,
            "level": "low",
            "confidence": {"level": "high", "explanation": "deterministic"},
            "factors": [],
            "summary": "Clear route"
        },
        "route": [],
        "recommendation": {
            "headline": "Clear",
            "body": "Proceed"
        },
        "modeOptions": [],
        "hazards": [],
        "sources": [],
        "estimatedDuration": "PT30M",
        "distanceKm": 25.0
    }

    resp = TripResponse.model_validate(legacy_json)
    assert resp.routes == []
    assert resp.estimated_duration == timedelta(minutes=30)

    # Serializing response with routes
    route = create_test_route("r1", "Route 1", 30.0, 30)
    evaluator = RouteEvaluator()
    base_time = datetime(2026, 9, 18, 8, 0, tzinfo=timezone.utc)
    ev_route = evaluator.evaluate_route(route, TripRequest.model_validate(legacy_json["request"]), create_weather_timeline(base_time), [], [], create_traffic_snapshot(route, 0))

    resp.routes = [ev_route]
    out_dict = resp.model_dump(by_alias=True)
    assert "routes" in out_dict
    assert len(out_dict["routes"]) == 1
    assert out_dict["routes"][0]["routeId"] == "r1"
    assert out_dict["routes"][0]["evaluation"]["riskScore"] == ev_route.evaluation.risk_score
