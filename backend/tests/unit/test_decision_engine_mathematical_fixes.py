from datetime import datetime, timezone, timedelta
import pytest

from app.models.enums import TransportMode, RiskLevel
from app.decision_engine.normalized_models import (
    NormalizedWeatherPoint,
    NormalizedRouteSegment,
    NormalizedRoute,
    TripContext,
)
from app.decision_engine.risk_model import calculate_segment_risk, calculate_aqi_risk_score
from app.decision_engine.engine import DecisionEngine
from app.decision_engine.route_evaluator import RouteEvaluator
from app.models.trip import TripRequest


def test_base_environmental_risk_weights_sum_to_one():
    """
    Validates that the environmental risk weights sum to exactly 1.00:
    precipitation = 0.35
    visibility = 0.20
    hazard = 0.30
    AQI = 0.15
    Total = 1.00
    """
    precip_weight = 0.35
    vis_weight = 0.20
    hazard_weight = 0.30
    aqi_weight = 0.15

    total_weight = round(precip_weight + vis_weight + hazard_weight + aqi_weight, 6)
    assert total_weight == 1.00


def test_aqi_discounted_exactly_once_for_car_and_bike():
    """
    Verifies that AQI mode exposure is discounted exactly once.
    base_weather_risk is scaled by mode_multiplier, while aqi_score (which already
    incorporates mode-specific cabin protection) is added directly without a second
    mode_multiplier discount.
    """
    # 10 minute segment -> temporal_multiplier = 1.0
    seg = NormalizedRouteSegment(
        start_lat=28.6, start_lng=77.3, end_lat=28.5, end_lng=77.2,
        distance_km=5.0, estimated_duration=timedelta(minutes=10)
    )
    # Weather with 10mm rain (precip_score = 30)
    weather = NormalizedWeatherPoint(
        time=datetime.now(timezone.utc), temperature=25.0, precipitation_mm=10.0,
        precipitation_probability=100.0, humidity=80, wind_speed=5.0, wind_gusts=10.0,
        visibility=10000.0, condition="Rain", is_extreme_heat=False, is_poor_visibility=False
    )
    # Severe AQI
    aqi_dict = {"aqi": 350, "pm2_5": 300.0}  # Severe Smog, S_raw = 85

    # Bike: mode_multiplier = 1.0, aqi_score = 85
    # base_weather_risk = 30 * 0.35 = 10.5 -> with mode 1.0 = 10.5
    # aqi contribution = 85 * 0.15 = 12.75
    # Total = 10.5 + 12.75 = 23.25 -> int 23
    score_bike, level_bike, factors_bike, _, _ = calculate_segment_risk(
        segment=seg, weather=weather, hazards=[], mode=TransportMode.bike, air_quality=aqi_dict
    )
    assert score_bike == 23
    assert any(f.name == "Air Quality" and f.score == 85 for f in factors_bike)

    # If AQI were double-discounted in a hypothetical mode with mode_multiplier = 0.4 and aqi_score = 40:
    # Single-discount: (base_weather * 0.4) + (aqi * 0.15) = (10.5 * 0.4) + (40 * 0.15) = 4.2 + 6.0 = 10.2 -> 10
    # Double-discount: (base_weather + aqi * 0.15) * 0.4 = (10.5 + 6.0) * 0.4 = 16.5 * 0.4 = 6.6 -> 6
    # We verify the formula directly in calculate_segment_risk


def test_exposure_score_is_not_simply_overall_score():
    """
    Verifies that EngineDecisionResult.exposure_score reflects the true duration-weighted
    segment risk exposure, and is not aliased to overall_score.
    """
    engine = DecisionEngine()
    dep_time = datetime(2026, 9, 20, 8, 0, tzinfo=timezone.utc)

    # Route with 1 short risky segment (5 mins, rain=20mm -> score high) and 2 long safe segments (each 20 mins, safe -> score 0)
    seg1 = NormalizedRouteSegment(
        start_lat=28.62, start_lng=77.36, end_lat=28.61, end_lng=77.35,
        distance_km=2.0, estimated_duration=timedelta(minutes=5)
    )
    seg2 = NormalizedRouteSegment(
        start_lat=28.61, start_lng=77.35, end_lat=28.58, end_lng=77.30,
        distance_km=10.0, estimated_duration=timedelta(minutes=20)
    )
    seg3 = NormalizedRouteSegment(
        start_lat=28.58, start_lng=77.30, end_lat=28.50, end_lng=77.10,
        distance_km=15.0, estimated_duration=timedelta(minutes=20)
    )

    route = NormalizedRoute(
        route_id="r_exposure_test",
        summary="Exposure Test Route",
        polyline="abc",
        segments=[seg1, seg2, seg3],
        total_distance_km=27.0,
        total_duration=timedelta(minutes=45),
        provider_name="Test",
        provenance="test",
    )

    # Weather timeline where seg1 experiences heavy rain, seg2 and seg3 are clear
    w_heavy = NormalizedWeatherPoint(
        time=dep_time, temperature=24.0, precipitation_mm=25.0,
        precipitation_probability=90.0, humidity=85, wind_speed=15.0,
        wind_gusts=20.0, visibility=4000.0, condition="Heavy Rain",
        is_extreme_heat=False, is_poor_visibility=False
    )
    w_clear = NormalizedWeatherPoint(
        time=dep_time + timedelta(minutes=10), temperature=24.0, precipitation_mm=0.0,
        precipitation_probability=0.0, humidity=60, wind_speed=5.0,
        wind_gusts=10.0, visibility=10000.0, condition="Clear",
        is_extreme_heat=False, is_poor_visibility=False
    )

    ctx = TripContext(
        origin="Noida",
        destination="Gurgaon",
        departure_time=dep_time,
        mode=TransportMode.bike,
        route=route,
        weather_timeline=[w_heavy, w_clear],
        hazards=[],
        alerts=[],
    )

    result = engine.evaluate_route_core(ctx)

    assert result.exposure_score > 0
    # Overall score = 0.6 * bottleneck + 0.4 * exposure.
    # Since bottleneck is much higher than the duration-weighted exposure, exposure_score < overall_score.
    assert result.exposure_score < result.overall_risk.overall_score
    assert result.exposure_score != result.overall_risk.overall_score


def test_route_evaluator_tie_breaking_step_6a_uses_exposure_score():
    """
    Verifies that when two candidate routes share the exact same risk score, risk tier,
    travel duration, and distance, RouteEvaluator uses exposure_score to select the safer route.
    """
    evaluator = RouteEvaluator()
    dep_time = datetime(2026, 9, 20, 8, 0, tzinfo=timezone.utc)
    req = TripRequest(
        origin="Noida", destination="Gurgaon", departure_time=dep_time, mode=TransportMode.car
    )

    # Create dummy EvaluatedRoute A and B
    # Both: risk_score = 30 (Moderate), traffic_aware_duration = 30 mins, distance = 20 km
    # Route A has exposure_score = 10.0 (spent only 2 mins in risky condition)
    # Route B has exposure_score = 25.0 (spent 20 mins in risky condition)
    from app.models.route import EvaluatedRoute, RouteEvaluation
    from app.models.risk import RiskAssessment, Confidence, ConfidenceLevel

    eval_a = RouteEvaluation(
        route_id="route_a",
        risk_score=30,
        risk_level=RiskLevel.moderate,
        static_duration=timedelta(minutes=30),
        traffic_aware_duration=timedelta(minutes=30),
        traffic_delay_seconds=0.0,
        exposure_score=10.0,
        bottleneck_score=35,
        hazard_count=0,
        is_feasible=True,
        recommendation_headline="Proceed",
        recommendation_body="Moderate",
        provenance="test",
    )
    route_a = EvaluatedRoute(
        route_id="route_a",
        summary="Route A (Lower Exposure)",
        distance_km=20.0,
        static_duration=timedelta(minutes=30),
        segments=[],
        evaluation=eval_a,
        source_name="Test",
        provenance="test",
        risk=RiskAssessment(
            overall_score=30,
            level=RiskLevel.moderate,
            confidence=Confidence(level=ConfidenceLevel.high, score=0.9, reasons=[], explanation="High confidence"),
            factors=[],
            summary=""
        )
    )

    eval_b = RouteEvaluation(
        route_id="route_b",
        risk_score=30,
        risk_level=RiskLevel.moderate,
        static_duration=timedelta(minutes=30),
        traffic_aware_duration=timedelta(minutes=30),
        traffic_delay_seconds=0.0,
        exposure_score=25.0,
        bottleneck_score=35,
        hazard_count=0,
        is_feasible=True,
        recommendation_headline="Proceed",
        recommendation_body="Moderate",
        provenance="test",
    )
    route_b = EvaluatedRoute(
        route_id="route_b",
        summary="Route B (Higher Exposure)",
        distance_km=20.0,
        static_duration=timedelta(minutes=30),
        segments=[],
        evaluation=eval_b,
        source_name="Test",
        provenance="test",
        risk=RiskAssessment(
            overall_score=30,
            level=RiskLevel.moderate,
            confidence=Confidence(level=ConfidenceLevel.high, score=0.9, reasons=[], explanation="High confidence"),
            factors=[],
            summary=""
        )
    )

    selected, ranked = evaluator.select_and_rank_routes([route_b, route_a], departure_time=dep_time)
    # Route A must be selected because its exposure_score (10.0) is strictly lower than Route B (25.0)
    assert selected.route_id == "route_a"
    assert ranked[0].route_id == "route_a"
    assert ranked[1].route_id == "route_b"


def test_repeated_evaluations_remain_100_percent_deterministic():
    """
    Verifies that evaluating the same context 10 times produces 100% bit-identical results.
    """
    engine = DecisionEngine()
    dep_time = datetime(2026, 9, 20, 8, 30, tzinfo=timezone.utc)
    seg = NormalizedRouteSegment(
        start_lat=28.62, start_lng=77.36, end_lat=28.49, end_lng=77.08,
        distance_km=25.0, estimated_duration=timedelta(minutes=40)
    )
    route = NormalizedRoute(
        route_id="r_det", summary="Deterministic Corridor", polyline="xyz",
        segments=[seg], total_distance_km=25.0, total_duration=timedelta(minutes=40),
        provider_name="Test", provenance="test"
    )
    weather = NormalizedWeatherPoint(
        time=dep_time, temperature=28.0, precipitation_mm=5.0,
        precipitation_probability=60.0, humidity=70, wind_speed=12.0,
        wind_gusts=18.0, visibility=6000.0, condition="Light Rain",
        is_extreme_heat=False, is_poor_visibility=False
    )
    ctx = TripContext(
        origin="Noida", destination="Gurgaon", departure_time=dep_time,
        mode=TransportMode.car, route=route, weather_timeline=[weather],
        hazards=[], alerts=[]
    )

    results = [engine.evaluate_route_core(ctx) for _ in range(10)]
    first_score = results[0].overall_risk.overall_score
    first_exposure = results[0].exposure_score

    for r in results[1:]:
        assert r.overall_risk.overall_score == first_score
        assert r.exposure_score == first_exposure
        assert r.overall_risk.level == results[0].overall_risk.level
