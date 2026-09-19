from datetime import datetime, timezone, timedelta
import pytest

from app.providers.air_quality.base import (
    AirQualityPoint,
    AirQualitySnapshot,
    calculate_us_aqi_from_pm25,
    classify_aqi_category,
)
from app.providers.air_quality.mock import MockAirQualityProvider
from app.providers.air_quality.open_meteo import OpenMeteoAirQualityProvider
from app.decision_engine.risk_model import calculate_aqi_risk_score, calculate_segment_risk
from app.models.enums import TransportMode, RiskLevel
from app.models.trip import TripRequest
from app.services.trip_service import TripService
from app.providers.weather.mock import MockWeatherProvider
from app.providers.routing.mock import MockRoutingProvider
from app.providers.alerts.mock import MockAlertProvider
from app.providers.geocoding import MockGeocodingProvider
from app.decision_engine.normalized_models import NormalizedWeatherPoint, NormalizedRouteSegment


def test_us_epa_pm25_piecewise_breakpoints():
    """Validates PM2.5 to US EPA AQI mapping across all official EPA breakpoints."""
    # Good (0-12.0 µg/m³ -> 0-50 AQI)
    assert calculate_us_aqi_from_pm25(0.0) == 0
    assert calculate_us_aqi_from_pm25(6.0) == 25
    assert calculate_us_aqi_from_pm25(12.0) == 50

    # Moderate (12.1-35.4 µg/m³ -> 51-100 AQI)
    assert calculate_us_aqi_from_pm25(12.1) == 51
    assert calculate_us_aqi_from_pm25(35.4) == 100

    # Unhealthy for Sensitive Groups (35.5-55.4 µg/m³ -> 101-150 AQI)
    assert calculate_us_aqi_from_pm25(35.5) == 101
    assert calculate_us_aqi_from_pm25(55.4) == 150

    # Unhealthy (55.5-150.4 µg/m³ -> 151-200 AQI)
    assert calculate_us_aqi_from_pm25(55.5) == 151
    assert calculate_us_aqi_from_pm25(150.4) == 200

    # Very Unhealthy (150.5-250.4 µg/m³ -> 201-300 AQI)
    assert calculate_us_aqi_from_pm25(150.5) == 201
    assert calculate_us_aqi_from_pm25(250.4) == 300

    # Severe / Hazardous (250.5-350.4 µg/m³ -> 301-400 AQI)
    assert calculate_us_aqi_from_pm25(250.5) == 301
    assert calculate_us_aqi_from_pm25(350.4) == 400

    # Hazardous (> 350.5 µg/m³ -> 401-500 AQI)
    assert calculate_us_aqi_from_pm25(350.5) == 401
    assert calculate_us_aqi_from_pm25(500.4) == 500
    assert calculate_us_aqi_from_pm25(600.0) == 500  # Cap at 500


def test_aqi_category_classification():
    """Validates standard EPA category thresholds."""
    assert classify_aqi_category(40) == "Good"
    assert classify_aqi_category(75) == "Moderate"
    assert classify_aqi_category(125) == "Unhealthy for Sensitive Groups"
    assert classify_aqi_category(180) == "Unhealthy"
    assert classify_aqi_category(250) == "Very Unhealthy"
    assert classify_aqi_category(350) == "Severe"
    assert classify_aqi_category(450) == "Hazardous"


def test_deterministic_aqi_thresholds_and_mode_multipliers():
    """
    Tests exact AQI thresholds against all transport modes:
    - walk, bike: Multiplier 1.0 (direct exposure)
    - car: Multiplier 0.15 (enclosed private vehicle)
    - metro: Multiplier 0.10 (enclosed public rail)
    """
    # 1. AQI <= 100: Zero risk for ALL modes
    for mode in [TransportMode.walk, TransportMode.bike, TransportMode.car, TransportMode.metro]:
        score, factor = calculate_aqi_risk_score(aqi=85, pm2_5=28.0, mode=mode)
        assert score == 0
        assert factor is None

    # 2. Moderate Smog: AQI 160 (Unhealthy, S_raw = 45)
    # Bike/Walk: score = 45 -> Moderate risk factor emitted
    bike_score, bike_factor = calculate_aqi_risk_score(aqi=160, pm2_5=75.0, mode=TransportMode.bike)
    assert bike_score == 45
    assert bike_factor is not None
    assert bike_factor.name == "Air Quality"
    assert bike_factor.level == RiskLevel.moderate
    assert bike_factor.weight == 0.15
    assert "N95 mask" in bike_factor.description

    # Car: 45 * 0.15 = 6.75 -> round(7) < 20 -> filtered out (clean cabin)
    car_score, car_factor = calculate_aqi_risk_score(aqi=160, pm2_5=75.0, mode=TransportMode.car)
    assert car_score == 0
    assert car_factor is None

    # Metro: 45 * 0.10 = 4.5 -> round(5) < 20 -> filtered out
    metro_score, metro_factor = calculate_aqi_risk_score(aqi=160, pm2_5=75.0, mode=TransportMode.metro)
    assert metro_score == 0
    assert metro_factor is None

    # 3. Severe Smog: AQI 350 (Severe / Hazardous, S_raw = 85)
    # Bike/Walk: score = 85 -> Severe risk factor
    bike_sev_score, bike_sev_factor = calculate_aqi_risk_score(aqi=350, pm2_5=300.0, mode=TransportMode.bike)
    assert bike_sev_score == 85
    assert bike_sev_factor.level == RiskLevel.severe

    # Car: 85 * 0.15 = 12.75 -> round(13) < 20 -> filtered out
    car_sev_score, car_sev_factor = calculate_aqi_risk_score(aqi=350, pm2_5=300.0, mode=TransportMode.car)
    assert car_sev_score == 0

    # 4. Emergency Smog: AQI 480 (Hazardous, S_raw = 100)
    # Car: 100 * 0.15 = 15 -> < 20 -> filtered out
    # If emergency smog reaches severe levels in cabin:
    # Walk: 100 -> score 100, Severe
    walk_score, walk_factor = calculate_aqi_risk_score(aqi=480, pm2_5=450.0, mode=TransportMode.walk)
    assert walk_score == 100
    assert walk_factor.score == 100


def test_pm25_precedence_over_stale_or_underreported_aqi():
    """
    If reported AQI is low (e.g. 90) but PM2.5 is high (e.g. 180 µg/m³ -> AQI ~230),
    effective AQI must use the calculated PM2.5 AQI.
    """
    # Reported AQI is 90 (which alone would give score 0), but PM2.5 is 180 (Very Unhealthy)
    score, factor = calculate_aqi_risk_score(aqi=90, pm2_5=180.0, mode=TransportMode.bike)
    assert score == 70  # Maps to Very Unhealthy (201-300 range)
    assert factor is not None
    assert factor.level == RiskLevel.high
    assert "Very Unhealthy" in factor.description


def test_missing_aqi_never_fabricated():
    """Verifies that missing AQI is never fabricated and segment risk computes cleanly without it."""
    dummy_seg = NormalizedRouteSegment(
        start_lat=28.6, start_lng=77.3, end_lat=28.5, end_lng=77.2,
        distance_km=10.0, estimated_duration=timedelta(minutes=20)
    )
    dummy_weather = NormalizedWeatherPoint(
        time=datetime.now(timezone.utc), temperature=25.0, precipitation_mm=0.0,
        humidity=50, wind_speed=10.0, wind_gusts=15.0, visibility=5000.0,
        condition="Clear", is_extreme_heat=False, is_poor_visibility=False
    )

    # Missing AQI: None passed
    score, level, factors, reason, _ = calculate_segment_risk(
        segment=dummy_seg,
        weather=dummy_weather,
        hazards=[],
        mode=TransportMode.bike,
        air_quality=None
    )

    assert not any(f.name == "Air Quality" for f in factors)
    assert score == 0
    assert level == RiskLevel.low


@pytest.mark.asyncio
async def test_stale_aqi_explicit_provenance():
    """Verifies that stale AQI (>6h old) retains explicit is_stale=True flag."""
    provider = MockAirQualityProvider(default_aqi=220, simulate_stale=True)
    points = await provider.get_air_quality(28.6, 77.3, datetime.now(timezone.utc), hours=2)
    assert len(points) == 2
    assert points[0].is_stale is True
    assert points[0].observation_time is not None


@pytest.mark.asyncio
async def test_aqi_provider_failure_truthful_degradation():
    """Verifies that an AQI provider failure produces a truthful degraded snapshot rather than crashing."""
    failing_provider = MockAirQualityProvider(simulate_failure=True)
    service = TripService(
        weather_provider=MockWeatherProvider(),
        routing_provider=MockRoutingProvider(),
        alert_provider=MockAlertProvider(),
        geocoding_provider=MockGeocodingProvider(),
        air_quality_provider=failing_provider
    )

    req = TripRequest(
        origin="Noida Sector 62",
        destination="Gurgaon Cyber Hub",
        departure_time=datetime(2026, 9, 20, 9, 0, tzinfo=timezone.utc),
        mode=TransportMode.bike
    )

    res = await service.analyze_trip(req)
    assert res is not None
    # Trip evaluation succeeds
    assert res.status.value == "success"
    # Air quality is truthfully marked unavailable / degraded
    assert res.air_quality is not None
    assert res.air_quality.is_available is False
    assert res.air_quality.provenance == "degraded"
    assert res.air_quality.category == "Unavailable"


@pytest.mark.asyncio
async def test_aqi_cannot_override_official_alerts():
    """
    Even in clean air (AQI 30, Good), an authoritative Red Alert flood condition
    must not be diluted or overridden by air quality.
    """
    from app.decision_engine.models import EngineDecisionResult
    from app.models.enums import AlertSeverity, AlertSourceClass
    from app.decision_engine.normalized_models import NormalizedAlert, TripContext
    from app.decision_engine.engine import DecisionEngine

    clean_aqi = [AirQualityPoint(
        time=datetime.now(timezone.utc),
        pm2_5=5.0, pm10=10.0, aqi=20, category="Good", source_name="test"
    )]

    alert = NormalizedAlert(
        id="flood_alert_1",
        source_name="IMD",
        source_class=AlertSourceClass.authoritative,
        severity=AlertSeverity.emergency,
        affected_areas_polygon=[[28.0, 77.0], [29.0, 78.0]],
        issued_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=5),
        action="Avoid travel due to severe road flooding",
        is_override_eligible=True
    )

    engine = DecisionEngine()
    ctx = TripContext(
        origin="Noida Sector 62",
        destination="Gurgaon Cyber Hub",
        departure_time=datetime.now(timezone.utc),
        mode=TransportMode.car,
        route=MockRoutingProvider().get_route_sync() if hasattr(MockRoutingProvider(), "get_route_sync") else (await MockRoutingProvider().get_route(28.6, 77.3, 28.4, 77.1, TransportMode.car))[0],
        weather_timeline=[NormalizedWeatherPoint(
            time=datetime.now(timezone.utc), temperature=25.0, precipitation_mm=0.0,
            humidity=50, wind_speed=5.0, wind_gusts=10.0, visibility=5000.0,
            condition="Clear", is_extreme_heat=False, is_poor_visibility=False
        )],
        hazards=[],
        alerts=[alert],
        air_quality_timeline=clean_aqi
    )

    res = engine.evaluate_route_core(ctx)
    # The authoritative alert MUST override despite clean air
    assert res.alert_override_applied is True
    assert res.overall_risk.level in (RiskLevel.high, RiskLevel.severe)
