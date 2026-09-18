import pytest
from datetime import datetime, timezone, timedelta
from app.models.enums import TransportMode, TrafficStatus, CongestionLevel, TrafficCondition, RiskLevel, TripStatus
from app.models.traffic import TrafficSnapshot, TrafficSegment
from app.models.trip import TripResponse, TripRequest
from app.providers.traffic.mock import MockTrafficProvider
from app.providers.traffic.fallback import UnavailableTrafficProvider, FallbackTrafficProvider
from app.decision_engine.normalized_models import (
    NormalizedRoute, NormalizedRouteSegment, NormalizedWeatherPoint, TripContext
)
from app.decision_engine.temporal_alignment import align_route_with_weather
from app.decision_engine.risk_model import calculate_segment_risk
from app.decision_engine.engine import DecisionEngine

def _make_dummy_route(segment_durations_mins=[15, 15]):
    segments = []
    for i, mins in enumerate(segment_durations_mins):
        segments.append(NormalizedRouteSegment(
            start_lat=28.5 + (i * 0.05),
            start_lng=77.3 + (i * 0.05),
            end_lat=28.5 + ((i + 1) * 0.05),
            end_lng=77.3 + ((i + 1) * 0.05),
            distance_km=10.0,
            estimated_duration=timedelta(minutes=mins)
        ))
    total_dur = timedelta(minutes=sum(segment_durations_mins))
    return NormalizedRoute(
        segments=segments,
        total_distance_km=10.0 * len(segment_durations_mins),
        total_duration=total_dur
    )

def _make_weather_timeline(base_time: datetime, hours=4):
    points = []
    for h in range(hours):
        t = base_time + timedelta(hours=h)
        # 1st hour is clear, 2nd hour is rainy
        precip = 15.0 if h >= 1 else 0.0
        cond = "Heavy Rain" if h >= 1 else "Clear"
        points.append(NormalizedWeatherPoint(
            time=t,
            temperature=28.0,
            precipitation_mm=precip,
            humidity=60,
            wind_speed=12.0,
            wind_gusts=18.0,
            visibility=10000.0,
            condition=cond,
            is_extreme_heat=False,
            is_poor_visibility=False
        ))
    return points

# ── 1. Model Validation & Contradictory Provenance Prevention ──

def test_traffic_models_validation_prevents_contradictory_provenance():
    now = datetime.now(timezone.utc)
    dur = timedelta(minutes=30)
    
    # status=live with mock provenance must raise ValueError
    with pytest.raises(ValueError, match="Contradictory traffic metadata"):
        TrafficSnapshot(
            status=TrafficStatus.live,
            condition=TrafficCondition.clear,
            congestion_level=CongestionLevel.free_flow,
            delay_seconds=0.0,
            static_duration=dur,
            traffic_aware_duration=dur,
            timestamp=now,
            source_name="Fake Provider",
            provenance="demo/mock"
        )

    # status=mock with live provenance must raise ValueError
    with pytest.raises(ValueError, match="Contradictory traffic metadata"):
        TrafficSnapshot(
            status=TrafficStatus.mock,
            condition=TrafficCondition.congested,
            congestion_level=CongestionLevel.heavy,
            delay_seconds=300.0,
            static_duration=dur,
            traffic_aware_duration=dur + timedelta(seconds=300),
            timestamp=now,
            source_name="Fake Provider",
            provenance="live_provider"
        )

# ── 2. Enforce trafficAwareDuration = staticDuration + trafficDelay (No Double Counting) ──

def test_traffic_duration_enforcement_and_no_double_counting():
    now = datetime.now(timezone.utc)
    static_dur = timedelta(minutes=40)
    delay_sec = 600.0 # 10 minutes
    
    snapshot = TrafficSnapshot(
        status=TrafficStatus.mock,
        condition=TrafficCondition.congested,
        congestion_level=CongestionLevel.moderate,
        delay_seconds=delay_sec,
        static_duration=static_dur,
        traffic_aware_duration=static_dur, # intentionally off to test auto-enforcement
        timestamp=now,
        source_name="Mock Traffic Provider (Demo)",
        provenance="demo/mock"
    )
    
    # Must equal static + delay
    assert snapshot.traffic_aware_duration == static_dur + timedelta(seconds=delay_sec)
    assert snapshot.traffic_aware_duration.total_seconds() == 3000.0 # 50 minutes

# ── 3. Mock Provider Determinism and Explicit Labeling ──

@pytest.mark.asyncio
async def test_mock_traffic_provider_metadata_and_provenance():
    provider = MockTrafficProvider()
    route = _make_dummy_route([20, 20])
    departure = datetime(2026, 8, 27, 8, 30, tzinfo=timezone.utc) # 8:30 AM rush hour
    
    snapshot = await provider.get_traffic_for_route(route, departure, TransportMode.car)
    
    assert snapshot.status == TrafficStatus.mock
    assert snapshot.provenance == "demo/mock"
    assert snapshot.source_name == "Mock Traffic Provider (Demo)"
    assert snapshot.delay_seconds > 0
    assert snapshot.traffic_aware_duration == snapshot.static_duration + timedelta(seconds=snapshot.delay_seconds)
    assert len(snapshot.segments) == len(route.segments)

# ── 4. Zero-Delay for Walk / Metro Modes ──

@pytest.mark.asyncio
async def test_mock_traffic_zero_delay_for_walk_and_metro():
    provider = MockTrafficProvider()
    route = _make_dummy_route([30])
    departure = datetime(2026, 8, 27, 8, 30, tzinfo=timezone.utc)
    
    walk_snapshot = await provider.get_traffic_for_route(route, departure, TransportMode.walk)
    assert walk_snapshot.delay_seconds == 0.0
    assert walk_snapshot.congestion_level == CongestionLevel.free_flow
    assert walk_snapshot.condition == TrafficCondition.clear
    assert walk_snapshot.traffic_aware_duration == walk_snapshot.static_duration
    
    metro_snapshot = await provider.get_traffic_for_route(route, departure, TransportMode.metro)
    assert metro_snapshot.delay_seconds == 0.0
    assert metro_snapshot.congestion_level == CongestionLevel.free_flow

# ── 5. Moderate Delay (Off-Peak) vs Heavy Delay (Rush Hour) ──

@pytest.mark.asyncio
async def test_mock_traffic_off_peak_vs_rush_hour():
    provider = MockTrafficProvider()
    route = _make_dummy_route([30])
    
    off_peak_time = datetime(2026, 8, 27, 14, 0, tzinfo=timezone.utc) # 2:00 PM
    rush_hour_time = datetime(2026, 8, 27, 8, 30, tzinfo=timezone.utc) # 8:30 AM
    
    off_peak = await provider.get_traffic_for_route(route, off_peak_time, TransportMode.car)
    rush_hour = await provider.get_traffic_for_route(route, rush_hour_time, TransportMode.car)
    
    assert rush_hour.delay_seconds > off_peak.delay_seconds
    assert rush_hour.congestion_level in (CongestionLevel.heavy, CongestionLevel.severe)
    assert off_peak.congestion_level == CongestionLevel.moderate

# ── 6. Unavailable Traffic Provider ──

@pytest.mark.asyncio
async def test_unavailable_traffic_provider():
    provider = UnavailableTrafficProvider()
    route = _make_dummy_route([25])
    departure = datetime(2026, 8, 27, 9, 0, tzinfo=timezone.utc)
    
    snapshot = await provider.get_traffic_for_route(route, departure, TransportMode.car)
    assert snapshot.status == TrafficStatus.unavailable
    assert snapshot.provenance == "unavailable"
    assert snapshot.delay_seconds == 0.0
    assert snapshot.traffic_aware_duration == snapshot.static_duration
    assert snapshot.current_speed_kmh is None

# ── 7. Downstream Weather Time Alignment After Delay (Effect 1) ──

def test_downstream_weather_time_alignment_after_delay():
    dep_time = datetime(2026, 8, 27, 8, 0, tzinfo=timezone.utc)
    route = _make_dummy_route([15, 15]) # 2 segments, 15 min each
    weather_timeline = _make_weather_timeline(dep_time, hours=4)
    
    # Case A: Zero traffic delay -> segment 2 arrival time is 8:15 AM (closest to 8:00 AM clear weather)
    aligned_no_traffic = align_route_with_weather(route, dep_time, weather_timeline, traffic=None)
    seg2_weather_no_traffic = aligned_no_traffic[1][2]
    assert aligned_no_traffic[1][1] == dep_time + timedelta(minutes=15)
    assert seg2_weather_no_traffic.precipitation_mm == 0.0 # Clear at 8:00 AM
    
    # Case B: Significant traffic delay on segment 1 (e.g. +45 min delay)
    # -> segment 2 arrival time is pushed to 8:00 + 15 + 45 = 9:00 AM (rain begins at 9:00 AM!)
    traffic_delayed = TrafficSnapshot(
        status=TrafficStatus.mock,
        condition=TrafficCondition.congested,
        congestion_level=CongestionLevel.heavy,
        delay_seconds=2700.0, # 45 minutes
        static_duration=route.total_duration,
        traffic_aware_duration=route.total_duration + timedelta(minutes=45),
        segments=[
            TrafficSegment(start_lat=28.5, start_lng=77.3, end_lat=28.55, end_lng=77.35, delay_seconds=2700.0),
            TrafficSegment(start_lat=28.55, start_lng=77.35, end_lat=28.6, end_lng=77.4, delay_seconds=0.0)
        ],
        timestamp=dep_time,
        source_name="Mock Traffic Provider (Demo)",
        provenance="demo/mock"
    )
    
    aligned_with_traffic = align_route_with_weather(route, dep_time, weather_timeline, traffic=traffic_delayed)
    assert aligned_with_traffic[1][1] == dep_time + timedelta(minutes=60) # 9:00 AM!
    seg2_weather_with_traffic = aligned_with_traffic[1][2]
    assert seg2_weather_with_traffic.precipitation_mm == 15.0 # Hit by heavy rain due to traffic delay!

# ── 8. Three Explicitly Separate Traffic Effects ──

def test_three_separate_traffic_effects():
    dep_time = datetime(2026, 8, 27, 8, 0, tzinfo=timezone.utc)
    route = _make_dummy_route([10]) # 10 min base duration
    seg = route.segments[0]
    
    weather = NormalizedWeatherPoint(
        time=dep_time,
        temperature=25.0,
        precipitation_mm=10.0, # Rain
        humidity=70,
        wind_speed=10.0,
        wind_gusts=15.0,
        visibility=8000.0,
        condition="Rain",
        is_extreme_heat=False,
        is_poor_visibility=False
    )
    
    # Effect 2 Check: Extended Environmental Exposure
    # Base duration 10 min: temporal_multiplier = 1.0
    score_base, _, _, _, _ = calculate_segment_risk(seg, weather, [], TransportMode.bike, traffic_delay_seconds=0.0)
    
    # Delayed duration +10 min (total 20 min): temporal_multiplier = 20/10 = 2.0
    score_delayed, _, _, _, _ = calculate_segment_risk(seg, weather, [], TransportMode.bike, traffic_delay_seconds=600.0)
    
    # Environmental risk must scale proportionally with longer duration spent in rain
    assert score_delayed > score_base
    
    # Effect 3 Check: Direct Congestion Factor
    engine = DecisionEngine()
    
    # Context with severe traffic
    traffic_severe = TrafficSnapshot(
        status=TrafficStatus.mock,
        condition=TrafficCondition.gridlock,
        congestion_level=CongestionLevel.severe,
        delay_seconds=1200.0,
        static_duration=route.total_duration,
        traffic_aware_duration=route.total_duration + timedelta(minutes=20),
        timestamp=dep_time,
        source_name="Mock Traffic Provider (Demo)",
        provenance="demo/mock"
    )
    
    ctx = TripContext(
        origin="A",
        destination="B",
        departure_time=dep_time,
        mode=TransportMode.car,
        route=route,
        weather_timeline=[weather],
        hazards=[],
        alerts=[],
        traffic=traffic_severe
    )
    
    res = engine.evaluate(ctx)
    factor_names = [f.name for f in res.overall_risk.factors]
    assert "Traffic Congestion" in factor_names
    traffic_factor = next(f for f in res.overall_risk.factors if f.name == "Traffic Congestion")
    assert traffic_factor.score == 40
    assert traffic_factor.level == RiskLevel.high

# ── 9. Backward-Compatible JSON Deserialization ──

def test_backward_compatible_json_deserialization():
    # Payload from older backend version without "traffic" key
    legacy_payload = {
        "analysisId": "test-id-123",
        "status": "success",
        "request": {
            "origin": "Noida",
            "destination": "Delhi",
            "departureTime": "2026-08-27T08:00:00Z",
            "mode": "car"
        },
        "route": [],
        "modeOptions": [],
        "hazards": [],
        "sources": [],
        "estimatedDuration": "PT30M",
        "distanceKm": 15.0
    }
    
    res = TripResponse.model_validate(legacy_payload)
    assert res.traffic is None
    assert res.status == TripStatus.success
    assert res.distance_km == 15.0

    # Payload with explicit "traffic": null
    null_traffic_payload = {**legacy_payload, "traffic": None}
    res_null = TripResponse.model_validate(null_traffic_payload)
    assert res_null.traffic is None
