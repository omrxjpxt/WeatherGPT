import pytest
from datetime import datetime, timezone, timedelta
from app.decision_engine.engine import DecisionEngine
from app.decision_engine.scenario_ranker import rank_scenarios
from app.decision_engine.normalized_models import (
    TripContext, NormalizedRoute, NormalizedRouteSegment,
    NormalizedWeatherPoint, NormalizedHazard, NormalizedAlert
)
from app.models.enums import TransportMode, AlertSeverity, RiskLevel

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
    return [
        NormalizedWeatherPoint(
            time=now, temperature=30.0, precipitation=0.0, humidity=50,
            wind_speed=5.0, condition="Clear", is_extreme_heat=False, is_poor_visibility=False
        )
    ]

@pytest.fixture
def heavy_rain_weather():
    now = datetime.now(timezone.utc)
    return [
        NormalizedWeatherPoint(
            time=now, temperature=25.0, precipitation=30.0, humidity=95,
            wind_speed=25.0, condition="Heavy Rain", is_extreme_heat=False, is_poor_visibility=True
        )
    ]

def test_engine_clear_weather(base_route, clear_weather):
    engine = DecisionEngine()
    ctx = TripContext(
        origin="A", destination="B", departure_time=clear_weather[0].time,
        mode=TransportMode.bike, route=base_route, weather_timeline=clear_weather,
        hazards=[], alerts=[]
    )
    result = engine.evaluate(ctx)
    assert result.overall_risk.level == RiskLevel.low
    assert result.alert_override_applied is False

def test_engine_heavy_rain(base_route, heavy_rain_weather):
    engine = DecisionEngine()
    ctx = TripContext(
        origin="A", destination="B", departure_time=heavy_rain_weather[0].time,
        mode=TransportMode.bike, route=base_route, weather_timeline=heavy_rain_weather,
        hazards=[], alerts=[]
    )
    result = engine.evaluate(ctx)
    # 30mm/hr precip * 3 = 90. Plus 60*0.2 = 12. Score around 102 capped to 100.
    assert result.overall_risk.level == RiskLevel.severe
    assert result.overall_risk.overall_score >= 75

def test_mode_exposure_differences(base_route, heavy_rain_weather):
    engine = DecisionEngine()
    
    # Bike scenario
    ctx_bike = TripContext(
        origin="A", destination="B", departure_time=heavy_rain_weather[0].time,
        mode=TransportMode.bike, route=base_route, weather_timeline=heavy_rain_weather,
        hazards=[], alerts=[]
    )
    res_bike = engine.evaluate(ctx_bike)
    
    # Metro scenario
    ctx_metro = TripContext(
        origin="A", destination="B", departure_time=heavy_rain_weather[0].time,
        mode=TransportMode.metro, route=base_route, weather_timeline=heavy_rain_weather,
        hazards=[], alerts=[]
    )
    res_metro = engine.evaluate(ctx_metro)
    
    # Given identical conditions, metro should have significantly lower risk than bike
    assert res_metro.overall_risk.overall_score < res_bike.overall_risk.overall_score

def test_engine_determinism(base_route, heavy_rain_weather):
    engine = DecisionEngine()
    ctx = TripContext(
        origin="A", destination="B", departure_time=heavy_rain_weather[0].time,
        mode=TransportMode.bike, route=base_route, weather_timeline=heavy_rain_weather,
        hazards=[], alerts=[]
    )
    res1 = engine.evaluate(ctx)
    res2 = engine.evaluate(ctx)
    assert res1.overall_risk.overall_score == res2.overall_risk.overall_score
    assert res1.recommendation_headline == res2.recommendation_headline

def test_alert_override(base_route, clear_weather):
    engine = DecisionEngine()
    
    alert = NormalizedAlert(
        id="a1", severity=AlertSeverity.warning,
        affected_areas_polygon=[[28.4, 77.0], [28.7, 77.0], [28.7, 77.5], [28.4, 77.5]],
        issued_at=clear_weather[0].time - timedelta(hours=1),
        expires_at=clear_weather[0].time + timedelta(hours=5),
        requires_override=True
    )
    
    ctx = TripContext(
        origin="A", destination="B", departure_time=clear_weather[0].time,
        mode=TransportMode.bike, route=base_route, weather_timeline=clear_weather,
        hazards=[], alerts=[alert]
    )
    
    result = engine.evaluate(ctx)
    # Even though weather is clear, alert forces severe risk
    assert result.alert_override_applied is True
    assert result.overall_risk.level == RiskLevel.severe
    assert result.overall_risk.overall_score >= 85

def test_scenario_ranking(base_route, heavy_rain_weather):
    engine = DecisionEngine()
    ctx1 = TripContext(
        origin="A", destination="B", departure_time=heavy_rain_weather[0].time,
        mode=TransportMode.bike, route=base_route, weather_timeline=heavy_rain_weather,
        hazards=[], alerts=[]
    )
    ctx2 = TripContext(
        origin="A", destination="B", departure_time=heavy_rain_weather[0].time,
        mode=TransportMode.metro, route=base_route, weather_timeline=heavy_rain_weather,
        hazards=[], alerts=[]
    )
    
    res1 = engine.evaluate(ctx1)
    res2 = engine.evaluate(ctx2)
    
    ranked = rank_scenarios([res1, res2])
    # Metro should be ranked first because it has lower risk
    assert ranked[0].overall_risk.overall_score < ranked[1].overall_risk.overall_score
