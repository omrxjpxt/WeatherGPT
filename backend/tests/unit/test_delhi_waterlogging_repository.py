import pytest
from datetime import datetime, timezone, timedelta

from app.providers.hazard.delhi_waterlogging import DelhiWaterloggingHazardRepository
from app.decision_engine.normalized_models import (
    NormalizedHazard,
    NormalizedRouteSegment,
    NormalizedWeatherPoint,
)
from app.decision_engine.risk_model import calculate_segment_risk
from app.models.enums import TransportMode, HazardType, HazardSourceClass, RiskLevel


def _create_weather(precip_mm: float = 0.0, condition: str = "Rain") -> NormalizedWeatherPoint:
    return NormalizedWeatherPoint(
        time=datetime.now(timezone.utc),
        temperature=27.0,
        precipitation_mm=precip_mm,
        humidity=85,
        wind_speed=15.0,
        wind_gusts=20.0,
        visibility=3000.0,
        condition=condition,
        is_extreme_heat=False,
        is_poor_visibility=False,
    )


def _create_segment_near_minto_bridge() -> NormalizedRouteSegment:
    # Minto Bridge Underpass is at 28.6327, 77.2220
    return NormalizedRouteSegment(
        start_lat=28.6320,
        start_lng=77.2215,
        end_lat=28.6335,
        end_lng=77.2225,
        distance_km=0.3,
        estimated_duration=timedelta(minutes=3),
    )


@pytest.mark.asyncio
async def test_repository_indexing_and_loading():
    repo = DelhiWaterloggingHazardRepository()
    hazards = repo.get_all_hazards()
    
    assert len(hazards) >= 30
    assert any(h.id == "pwd-minto-bridge-underpass" for h in hazards)
    assert any(h.id == "pwd-zakhira-underpass" for h in hazards)
    assert any(h.id == "pwd-pul-prahladpur-underpass" for h in hazards)
    assert any(h.id == "pwd-moolchand-underpass" for h in hazards)


@pytest.mark.asyncio
async def test_verified_hotspot_metadata_and_provenance():
    repo = DelhiWaterloggingHazardRepository()
    hazards = repo.get_all_hazards()
    minto = next(h for h in hazards if h.id == "pwd-minto-bridge-underpass")
    
    assert minto.is_underpass is True
    assert minto.trigger_precipitation_mm == 15.0  # 15 mm/hr underpass threshold
    assert minto.source_class == HazardSourceClass.government_open_data
    assert "Delhi PWD" in minto.source_name
    assert minto.chronic is True
    assert "walk" in minto.impassable_modes
    assert "bike" in minto.impassable_modes
    assert "car" in minto.impassable_modes


@pytest.mark.asyncio
async def test_provenance_and_explicit_modeling_assumptions():
    repo = DelhiWaterloggingHazardRepository()
    meta = repo.metadata
    
    assert "source" in meta
    assert "retrieval_date" in meta
    assumptions = meta.get("modeling_assumptions", {})
    assert assumptions.get("underpass_activation_rainfall_mm_per_hr") == 15.0
    assert assumptions.get("surface_activation_rainfall_mm_per_hr") == 35.0
    assert assumptions.get("two_wheeler_impassable_water_depth_cm") == 15.0
    assert assumptions.get("car_stalling_water_depth_cm") == 30.0


@pytest.mark.asyncio
async def test_spatial_bounding_box_filtering():
    repo = DelhiWaterloggingHazardRepository()
    
    # Query small box around Connaught Place / Minto Bridge
    cp_hazards = await repo.get_hazards_in_region(28.62, 77.21, 28.64, 77.23)
    assert any(h.id == "pwd-minto-bridge-underpass" for h in cp_hazards)
    # Pul Prahlad Pur (MB Road, South Delhi) must NOT be in this central Delhi box
    assert not any(h.id == "pwd-pul-prahladpur-underpass" for h in cp_hazards)


def test_dormant_hazard_zero_risk_contribution():
    repo = DelhiWaterloggingHazardRepository()
    minto = next(h for h in repo.get_all_hazards() if h.id == "pwd-minto-bridge-underpass")
    segment = _create_segment_near_minto_bridge()
    
    # 5 mm/hr rainfall does not trigger 15 mm/hr underpass threshold
    dry_weather = _create_weather(precip_mm=5.0)
    score, level, factors, reason, relevance = calculate_segment_risk(
        segment, dry_weather, [minto], TransportMode.car
    )
    
    rel = relevance[0]
    assert rel.spatially_relevant is True
    assert rel.weather_triggered is False
    assert rel.currently_relevant is False
    assert rel.contribution_score == 0
    assert not any(f.name == "Historical Hazard Risk" for f in factors)


def test_rainfall_activation_triggers_risk():
    repo = DelhiWaterloggingHazardRepository()
    minto = next(h for h in repo.get_all_hazards() if h.id == "pwd-minto-bridge-underpass")
    segment = _create_segment_near_minto_bridge()
    
    # 20 mm/hr exceeds 15 mm/hr underpass threshold
    wet_weather = _create_weather(precip_mm=20.0)
    score, level, factors, reason, relevance = calculate_segment_risk(
        segment, wet_weather, [minto], TransportMode.car
    )
    
    rel = relevance[0]
    assert rel.spatially_relevant is True
    assert rel.weather_triggered is True
    assert rel.currently_relevant is True
    assert rel.contribution_score > 0
    assert any(f.name == "Historical Hazard Risk" for f in factors)


def test_mode_specific_behavior_exposure_and_metro_immunity():
    repo = DelhiWaterloggingHazardRepository()
    minto = next(h for h in repo.get_all_hazards() if h.id == "pwd-minto-bridge-underpass")
    segment = _create_segment_near_minto_bridge()
    wet_weather = _create_weather(precip_mm=25.0)
    
    # 1. Walk / Bike: highly exposed
    score_walk, _, factors_walk, _, _ = calculate_segment_risk(
        segment, wet_weather, [minto], TransportMode.walk
    )
    score_bike, _, factors_bike, _, _ = calculate_segment_risk(
        segment, wet_weather, [minto], TransportMode.bike
    )
    
    # 2. Car: protected cabin, lower exposure than bike/walk
    score_car, _, factors_car, _, _ = calculate_segment_risk(
        segment, wet_weather, [minto], TransportMode.car
    )
    
    assert score_walk > score_car
    assert score_bike > score_car
    
    # 3. Metro: immune to street-level waterlogging
    score_metro, _, factors_metro, _, relevance_metro = calculate_segment_risk(
        segment, wet_weather, [minto], TransportMode.metro
    )
    
    # Metro has no Historical Hazard Risk factor for street waterlogging
    assert not any(f.name == "Historical Hazard Risk" for f in factors_metro)
    assert relevance_metro[0].currently_relevant is False
    assert relevance_metro[0].contribution_score == 0
    assert "Metro" in relevance_metro[0].relevance_reason
