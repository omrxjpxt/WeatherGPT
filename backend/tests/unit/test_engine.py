import pytest
from datetime import datetime, timezone, timedelta
from app.decision_engine.engine import DecisionEngine
from app.decision_engine.scenario_ranker import rank_scenarios
from app.decision_engine.normalized_models import (
    TripContext, NormalizedRoute, NormalizedRouteSegment,
    NormalizedWeatherPoint, NormalizedHazard, NormalizedAlert
)
from app.models.enums import TransportMode, AlertSeverity, RiskLevel, ConfidenceLevel, HazardType, AlertSourceClass, HazardSourceClass

@pytest.fixture
def base_route():
    return NormalizedRoute(
        segments=[
            NormalizedRouteSegment(
                start_lat=28.6, start_lng=77.3, end_lat=28.5, end_lng=77.2,
                distance_km=10.0, estimated_duration=timedelta(minutes=20)
            )
        ],
        total_distance_km=10.0,
        total_duration=timedelta(minutes=20)
    )

@pytest.fixture
def clear_weather():
    now = datetime.now(timezone.utc)
    # Give a long enough timeline to support alternative departure search
    timeline = []
    for i in range(-2, 5):
        timeline.append(
            NormalizedWeatherPoint(
                time=now + timedelta(hours=i), temperature=30.0, precipitation_mm=0.0, humidity=50,
                wind_speed=5.0, wind_gusts=5.0, visibility=10000.0, condition="Clear", is_extreme_heat=False, is_poor_visibility=False
            )
        )
    return timeline

@pytest.fixture
def heavy_rain_weather():
    now = datetime.now(timezone.utc)
    timeline = []
    for i in range(-2, 5):
        timeline.append(
            NormalizedWeatherPoint(
                time=now + timedelta(hours=i), temperature=25.0, precipitation_mm=30.0, humidity=95,
                wind_speed=25.0, wind_gusts=40.0, visibility=500.0, condition="Heavy Rain", is_extreme_heat=False, is_poor_visibility=True
            )
        )
    return timeline

def test_engine_clear_weather(base_route, clear_weather):
    engine = DecisionEngine()
    ctx = TripContext(
        origin="A", destination="B", departure_time=clear_weather[2].time,
        mode=TransportMode.bike, route=base_route, weather_timeline=clear_weather,
        hazards=[], alerts=[]
    )
    result = engine.evaluate(ctx)
    assert result.overall_risk.level == RiskLevel.low
    assert result.alert_override_applied is False

def test_engine_heavy_rain(base_route, heavy_rain_weather):
    engine = DecisionEngine()
    ctx = TripContext(
        origin="A", destination="B", departure_time=heavy_rain_weather[2].time,
        mode=TransportMode.bike, route=base_route, weather_timeline=heavy_rain_weather,
        hazards=[], alerts=[]
    )
    result = engine.evaluate(ctx)
    assert result.overall_risk.level == RiskLevel.severe
    assert result.overall_risk.overall_score >= 75

def test_mode_exposure_differences(base_route, heavy_rain_weather):
    engine = DecisionEngine()
    ctx_bike = TripContext(
        origin="A", destination="B", departure_time=heavy_rain_weather[2].time,
        mode=TransportMode.bike, route=base_route, weather_timeline=heavy_rain_weather,
        hazards=[], alerts=[]
    )
    res_bike = engine.evaluate(ctx_bike)
    
    ctx_metro = TripContext(
        origin="A", destination="B", departure_time=heavy_rain_weather[2].time,
        mode=TransportMode.metro, route=base_route, weather_timeline=heavy_rain_weather,
        hazards=[], alerts=[]
    )
    res_metro = engine.evaluate(ctx_metro)
    
    assert res_metro.overall_risk.overall_score < res_bike.overall_risk.overall_score

def test_engine_determinism(base_route, heavy_rain_weather):
    engine = DecisionEngine()
    ctx = TripContext(
        origin="A", destination="B", departure_time=heavy_rain_weather[2].time,
        mode=TransportMode.bike, route=base_route, weather_timeline=heavy_rain_weather,
        hazards=[], alerts=[]
    )
    res1 = engine.evaluate(ctx)
    res2 = engine.evaluate(ctx)
    assert res1.overall_risk.overall_score == res2.overall_risk.overall_score

# --- NEW TESTS ---

def test_hazard_outside_radius(base_route, clear_weather):
    engine = DecisionEngine()
    # Route is approx 28.6, 77.3 to 28.5, 77.2
    # Place hazard far away (e.g. 30.0, 77.3)
    hazard = NormalizedHazard(
        id="h1", type=HazardType.waterlogging, lat=30.0, lng=77.3, 
        radius_meters=1000.0, base_severity=80, source_name="Test Source", source_class=HazardSourceClass.demo
    )
    ctx = TripContext(
        origin="A", destination="B", departure_time=clear_weather[2].time,
        mode=TransportMode.bike, route=base_route, weather_timeline=clear_weather,
        hazards=[hazard], alerts=[]
    )
    res = engine.evaluate(ctx)
    # Should be unaffected by hazard
    assert res.overall_risk.level == RiskLevel.low

def test_hazard_inside_radius(base_route, clear_weather):
    engine = DecisionEngine()
    # Place hazard exactly on start point
    hazard = NormalizedHazard(
        id="h1", type=HazardType.waterlogging, lat=28.6, lng=77.3, 
        radius_meters=1000.0, base_severity=100, source_name="Test Source", source_class=HazardSourceClass.demo, trigger_condition="Clear"
    )
    ctx = TripContext(
        origin="A", destination="B", departure_time=clear_weather[2].time,
        mode=TransportMode.bike, route=base_route, weather_timeline=clear_weather,
        hazards=[hazard], alerts=[]
    )
    res = engine.evaluate(ctx)
    # Should be affected by hazard (score 50 * 1.5 mode multiplier -> approx 30)
    assert res.overall_risk.level != RiskLevel.low

def test_multiple_alerts_strongest_wins(base_route, clear_weather):
    engine = DecisionEngine()
    now = clear_weather[2].time
    
    alert1 = NormalizedAlert(
        id="a1", source_name="P1", source_class=AlertSourceClass.authoritative, severity=AlertSeverity.warning,
        affected_areas_polygon=[[28.4, 77.0], [28.7, 77.0], [28.7, 77.5], [28.4, 77.5]],
        issued_at=now - timedelta(hours=1),
        expires_at=now + timedelta(hours=5),
        is_override_eligible=True
    )
    alert2 = NormalizedAlert(
        id="a2", source_name="P2", source_class=AlertSourceClass.authoritative, severity=AlertSeverity.emergency, # Stronger
        affected_areas_polygon=[[28.4, 77.0], [28.7, 77.0], [28.7, 77.5], [28.4, 77.5]],
        issued_at=now - timedelta(hours=2),
        expires_at=now + timedelta(hours=5),
        is_override_eligible=True
    )
    
    ctx = TripContext(
        origin="A", destination="B", departure_time=now,
        mode=TransportMode.bike, route=base_route, weather_timeline=clear_weather,
        hazards=[], alerts=[alert1, alert2]
    )
    
    result = engine.evaluate(ctx)
    assert result.active_override_alert.id == "a2"

def test_alert_no_geometry_regional_match(base_route, clear_weather):
    engine = DecisionEngine()
    now = clear_weather[2].time
    
    alert = NormalizedAlert(
        id="a1", source_name="P1", source_class=AlertSourceClass.authoritative, severity=AlertSeverity.warning,
        affected_areas_polygon=[], # Missing geometry
        issued_at=now - timedelta(hours=1),
        expires_at=now + timedelta(hours=5),
        is_override_eligible=True
    )
    
    ctx = TripContext(
        origin="A", destination="B", departure_time=now,
        mode=TransportMode.bike, route=base_route, weather_timeline=clear_weather,
        hazards=[], alerts=[alert]
    )
    
    result = engine.evaluate(ctx)
    assert result.alert_override_applied is True
    assert result.active_override_alert.id == "a1"

def test_exposure_vs_bottleneck_aggregation(heavy_rain_weather):
    # Route with one severe segment (short) and one safe segment (long)
    route = NormalizedRoute(
        segments=[
            NormalizedRouteSegment(start_lat=28.6, start_lng=77.3, end_lat=28.5, end_lng=77.2, distance_km=5.0, estimated_duration=timedelta(minutes=15)),
            NormalizedRouteSegment(start_lat=28.5, start_lng=77.2, end_lat=28.4, end_lng=77.1, distance_km=20.0, estimated_duration=timedelta(minutes=120))
        ],
        total_distance_km=25.0,
        total_duration=timedelta(minutes=135)
    )
    
    engine = DecisionEngine()
    hazard = NormalizedHazard(
        id="h1", type=HazardType.waterlogging, lat=28.6, lng=77.3,
        radius_meters=1000.0, base_severity=100, source_name="Test Source", source_class=HazardSourceClass.demo, trigger_condition="Heavy Rain"
    )
    
    # We want the first 15 mins to be severe (using heavy_rain_weather)
    # The next 120 mins should be clear
    mixed_weather = heavy_rain_weather[:]
    # Fast forward a bit so the second segment hits clear weather
    for i in range(3, len(mixed_weather)):
        mixed_weather[i].precipitation_mm = 0.0
        mixed_weather[i].is_poor_visibility = False
        mixed_weather[i].visibility = 10000.0
        
    ctx = TripContext(
        origin="A", destination="B", departure_time=mixed_weather[2].time,
        mode=TransportMode.bike, route=route, weather_timeline=mixed_weather,
        hazards=[hazard], alerts=[]
    )
    
    res = engine.evaluate(ctx)
    # Bottleneck should be >= 75
    # Overall score should be >= 75 due to guardrail
    assert res.overall_risk.overall_score >= 75

def test_better_departure_time_selected(base_route, clear_weather):
    engine = DecisionEngine()
    now = clear_weather[2].time
    
    weather = clear_weather[:]
    # Make current time bad
    weather[2].precipitation_mm = 50.0
    weather[2].visibility = 500.0
    # Make +30 mins good
    weather[3].precipitation_mm = 0.0
    weather[3].visibility = 10000.0
    
    ctx = TripContext(
        origin="A", destination="B", departure_time=now,
        mode=TransportMode.bike, route=base_route, weather_timeline=weather,
        hazards=[], alerts=[]
    )
    
    res = engine.evaluate(ctx)
    assert res.suggested_time is not None
    assert res.suggested_time != now

def test_departure_candidate_violating_deadline(base_route, clear_weather):
    engine = DecisionEngine()
    now = clear_weather[2].time
    weather = clear_weather[:]
    weather[2].precipitation_mm = 50.0
    weather[2].visibility = 500.0
    weather[3].precipitation_mm = 0.0
    weather[3].visibility = 10000.0
    
    ctx = TripContext(
        origin="A", destination="B", departure_time=now,
        mode=TransportMode.bike, route=base_route, weather_timeline=weather,
        hazards=[], alerts=[],
        arrival_deadline=now + timedelta(minutes=25)
    )
    
    res = engine.evaluate(ctx)
    assert res.suggested_time is None or res.suggested_time < now

def test_scenario_risk_filtering_and_ranking(base_route, clear_weather):
    engine = DecisionEngine()
    now = clear_weather[2].time
    weather = clear_weather[:]
    
    res_feasible = engine._evaluate_core(
        TripContext(origin="A", destination="B", departure_time=now, mode=TransportMode.car, route=base_route, weather_timeline=weather, hazards=[], alerts=[])
    )
    
    weather[2].precipitation_mm = 100.0
    res_unfeasible = engine._evaluate_core(
        TripContext(origin="A", destination="B", departure_time=now, mode=TransportMode.bike, route=base_route, weather_timeline=weather, hazards=[], alerts=[])
    )
    
    scenarios = [(res_feasible, now, None), (res_unfeasible, now, None)]
    ranked = rank_scenarios(scenarios)
    
    assert ranked[0] == res_feasible

def test_qualitative_confidence(base_route, clear_weather):
    engine = DecisionEngine()
    ctx = TripContext(
        origin="A", destination="B", departure_time=clear_weather[2].time,
        mode=TransportMode.bike, route=base_route, weather_timeline=clear_weather,
        hazards=[], alerts=[]
    )
    res = engine.evaluate(ctx)
    assert res.overall_risk.confidence.level == ConfidenceLevel.high
    assert hasattr(res.overall_risk.confidence, "percentage") is False
    assert "freshness" in res.overall_risk.confidence.explanation
