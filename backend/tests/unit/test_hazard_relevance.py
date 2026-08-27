import pytest
from datetime import datetime, timezone, timedelta
from typing import List

from app.models.enums import TransportMode, HazardType, HazardSourceClass, RiskLevel
from app.decision_engine.normalized_models import (
    NormalizedRouteSegment,
    NormalizedWeatherPoint,
    NormalizedHazard,
    TripContext,
    NormalizedRoute
)
from app.decision_engine.engine import DecisionEngine
from app.decision_engine.risk_model import calculate_segment_risk
from app.core.config import settings

def _create_hazard(lat=28.6, lng=77.3, radius=1000.0, base_severity=100, trigger_precip=5.0, source_class=HazardSourceClass.government_open_data):
    return NormalizedHazard(
        id="test-hazard",
        type=HazardType.waterlogging,
        lat=lat,
        lng=lng,
        radius_meters=radius,
        base_severity=base_severity,
        source_name="Test Source",
        source_class=source_class,
        trigger_precipitation_mm=trigger_precip
    )

def _create_weather(precip=0.0, cond="Clear"):
    return NormalizedWeatherPoint(
        time=datetime.now(timezone.utc),
        temperature=30.0,
        precipitation_mm=precip,
        humidity=50,
        wind_speed=5.0,
        wind_gusts=5.0,
        visibility=10000.0,
        condition=cond,
        is_extreme_heat=False,
        is_poor_visibility=False
    )

def _create_segment(start_lat=28.6, start_lng=77.3, end_lat=28.61, end_lng=77.31):
    return NormalizedRouteSegment(
        start_lat=start_lat,
        start_lng=start_lng,
        end_lat=end_lat,
        end_lng=end_lng,
        distance_km=2.0,
        estimated_duration=timedelta(minutes=10)
    )

def test_hazard_within_influence_radius_and_triggered():
    hazard = _create_hazard(trigger_precip=5.0)
    weather = _create_weather(precip=10.0) # Trigger met
    segment = _create_segment()
    
    score, level, factors, reason, relevance_results = calculate_segment_risk(
        segment, weather, [hazard], TransportMode.car
    )
    
    assert len(relevance_results) == 1
    res = relevance_results[0]
    assert res.spatially_relevant is True
    assert res.weather_triggered is True
    assert res.currently_relevant is True
    
    expected_contrib = int(hazard.base_severity * settings.hazard_influence_factor)
    assert res.contribution_score == expected_contrib
    assert any(f.name == "Historical Hazard Risk" for f in factors)

def test_hazard_outside_influence_radius():
    hazard = _create_hazard(lat=10.0, lng=10.0, trigger_precip=5.0) # Far away
    weather = _create_weather(precip=10.0) # Trigger met
    segment = _create_segment()
    
    score, level, factors, reason, relevance_results = calculate_segment_risk(
        segment, weather, [hazard], TransportMode.car
    )
    
    assert relevance_results[0].spatially_relevant is False
    assert relevance_results[0].currently_relevant is False
    assert not any(f.name == "Historical Hazard Risk" for f in factors)

def test_hazard_near_route_no_weather_trigger():
    hazard = _create_hazard(trigger_precip=15.0)
    weather = _create_weather(precip=5.0) # Trigger NOT met
    segment = _create_segment()
    
    score, level, factors, reason, relevance_results = calculate_segment_risk(
        segment, weather, [hazard], TransportMode.car
    )
    
    assert relevance_results[0].spatially_relevant is True
    assert relevance_results[0].weather_triggered is False
    assert relevance_results[0].currently_relevant is False
    assert not any(f.name == "Historical Hazard Risk" for f in factors)

def test_dormant_hazard_does_not_increase_risk():
    hazard = _create_hazard(trigger_precip=10.0)
    weather = _create_weather(precip=0.0)
    segment = _create_segment()
    
    # Calculate without hazard
    score_no_hazard, _, _, _, _ = calculate_segment_risk(segment, weather, [], TransportMode.car)
    
    # Calculate with hazard
    score_with_hazard, _, _, _, _ = calculate_segment_risk(segment, weather, [hazard], TransportMode.car)
    
    assert score_no_hazard == score_with_hazard

def test_provenance_and_typed_source_class():
    hazard = _create_hazard(source_class=HazardSourceClass.authoritative)
    assert isinstance(hazard.source_class, HazardSourceClass)
    assert hazard.source_name == "Test Source"
    
def test_engine_deterministic_repeated_evaluation():
    hazard = _create_hazard(trigger_precip=5.0)
    weather = _create_weather(precip=10.0)
    segment = _create_segment()
    
    route = NormalizedRoute(segments=[segment], total_distance_km=2.0, total_duration=timedelta(minutes=10))
    
    ctx = TripContext(
        origin="A",
        destination="B",
        departure_time=weather.time,
        mode=TransportMode.car,
        route=route,
        weather_timeline=[weather],
        hazards=[hazard],
        alerts=[]
    )
    
    engine = DecisionEngine()
    result1 = engine.evaluate(ctx)
    result2 = engine.evaluate(ctx)
    
    assert result1.overall_risk.overall_score == result2.overall_risk.overall_score
    assert len(result1.hazards) == 1
    assert result1.hazards[0].relevance.currently_relevant is True
    assert result2.hazards[0].relevance.currently_relevant is True
