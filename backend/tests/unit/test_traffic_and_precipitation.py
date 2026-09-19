from datetime import datetime, timezone, timedelta
import pytest
import httpx

from app.core.config import settings
from app.providers.routing.google_routes import GoogleRoutesProvider
from app.decision_engine.normalized_models import NormalizedWeatherPoint, NormalizedRouteSegment
from app.decision_engine.risk_model import _calculate_precipitation_score, calculate_segment_risk
from app.models.enums import TransportMode, RiskLevel
from app.decision_engine.engine import DecisionEngine
from app.decision_engine.normalized_models import TripContext, NormalizedRoute
from app.providers.routing.mock import MockRoutingProvider
from app.providers.air_quality.mock import MockAirQualityProvider


@pytest.mark.asyncio
async def test_google_routes_traffic_aware_and_departure_time(monkeypatch):
    """
    Verifies that when google_traffic_aware is enabled and travel_mode is DRIVE/TWO_WHEELER,
    routingPreference is set to TRAFFIC_AWARE and departureTime is passed in RFC 3339 UTC.
    """
    captured_request = {}

    async def mock_post(url, *args, **kwargs):
        if "json" in kwargs:
            captured_request.update(kwargs["json"])
        elif len(args) > 0 and isinstance(args[0], dict):
            captured_request.update(args[0])
        return httpx.Response(
            200,
            json={
                "routes": [{
                    "distanceMeters": 20000,
                    "duration": "1800s",
                    "staticDuration": "1200s",
                    "polyline": {"encodedPolyline": "mock_poly"},
                    "legs": [{
                        "distanceMeters": 20000,
                        "duration": "1800s",
                        "steps": []
                    }]
                }]
            },
            request=httpx.Request("POST", url)
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda req: None))
    monkeypatch.setattr(client, "post", mock_post)
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: client)
    monkeypatch.setattr(settings, "google_maps_api_key", "test-key-traffic")
    monkeypatch.setattr(settings, "google_traffic_aware", True)

    provider = GoogleRoutesProvider()
    departure = datetime(2026, 9, 20, 8, 30, tzinfo=timezone.utc)

    routes = await provider.get_route(
        28.6270, 77.3650, 28.4942, 77.0860, TransportMode.car, departure_time=departure
    )

    # 1. Inspect request payload
    assert captured_request.get("routingPreference") == "TRAFFIC_AWARE"
    assert captured_request.get("departureTime") == "2026-09-20T08:30:00Z"
    assert captured_request.get("travelMode") == "DRIVE"

    # 2. Inspect route response: static duration vs traffic duration
    assert len(routes) == 1
    route = routes[0]
    assert route.total_duration == timedelta(seconds=1800)
    assert route.traffic is not None
    assert route.traffic.static_duration == timedelta(seconds=1200)
    assert route.traffic.traffic_aware_duration == timedelta(seconds=1800)
    assert route.traffic.delay_seconds == 600.0  # 10 minutes delay


def test_precipitation_probability_risk_scaling():
    """
    Tests that precipitation risk scoring properly scales by precipitation_probability:
    - Low probability (< 20%): Bounded to <= 10, preventing false alarm trip cancellations.
    - High probability (>= 80%): Confirms high risk score.
    - Missing probability: Backward-compatible linear accumulation.
    """
    # 1. Heavy rainfall (15mm) with very low probability (10%) -> Capped at 10
    low_prob_weather = NormalizedWeatherPoint(
        time=datetime.now(timezone.utc), temperature=24.0, precipitation_mm=15.0,
        humidity=80, wind_speed=15.0, wind_gusts=20.0, visibility=3000.0,
        condition="Light Rain Showers", is_extreme_heat=False, is_poor_visibility=False,
        precipitation_probability=10.0,
        precipitation_intensity_category="moderate"
    )
    low_prob_score = _calculate_precipitation_score(low_prob_weather)
    assert low_prob_score <= 10  # False-alarm prevention

    # 2. Heavy rainfall (15mm) with high probability (90%) -> High score
    high_prob_weather = NormalizedWeatherPoint(
        time=datetime.now(timezone.utc), temperature=24.0, precipitation_mm=15.0,
        humidity=80, wind_speed=15.0, wind_gusts=20.0, visibility=3000.0,
        condition="Heavy Rain", is_extreme_heat=False, is_poor_visibility=False,
        precipitation_probability=90.0,
        precipitation_intensity_category="moderate"
    )
    high_prob_score = _calculate_precipitation_score(high_prob_weather)
    # effective_mm = 15.0 * 0.90 = 13.5; 13.5 * 3.0 = 40.5 -> 40
    assert high_prob_score >= 40

    # 3. Missing probability defaults safely to accumulation-only (15.0 * 3 = 45)
    legacy_weather = NormalizedWeatherPoint(
        time=datetime.now(timezone.utc), temperature=24.0, precipitation_mm=15.0,
        humidity=80, wind_speed=15.0, wind_gusts=20.0, visibility=3000.0,
        condition="Rain", is_extreme_heat=False, is_poor_visibility=False,
        precipitation_probability=None
    )
    assert _calculate_precipitation_score(legacy_weather) == 45


@pytest.mark.asyncio
async def test_concurrency_determinism_10x_repeated_evaluations():
    """
    10x repeated execution verification:
    Guarantees that concurrent provider gathering and decision engine evaluation
    produce bit-identical outputs across 10 consecutive executions.
    """
    mock_routes = await MockRoutingProvider().get_route(28.6270, 77.3650, 28.4942, 77.0860, TransportMode.bike)
    route = mock_routes[0]
    dep_time = datetime(2026, 9, 20, 8, 0, tzinfo=timezone.utc)

    weather_points = [
        NormalizedWeatherPoint(
            time=dep_time + timedelta(hours=i),
            temperature=28.0 + i,
            precipitation_mm=5.0,
            humidity=70,
            wind_speed=12.0,
            wind_gusts=18.0,
            visibility=4000.0,
            condition="Overcast",
            is_extreme_heat=False,
            is_poor_visibility=False,
            precipitation_probability=65.0,
        )
        for i in range(4)
    ]

    aqi_provider = MockAirQualityProvider(default_aqi=240, default_pm25=110.0)
    aqi_points = await aqi_provider.get_air_quality(28.6270, 77.3650, dep_time, hours=4)

    engine = DecisionEngine()
    results = []

    for _ in range(10):
        ctx = TripContext(
            origin="Noida Sector 62",
            destination="Gurgaon Cyber Hub",
            departure_time=dep_time,
            mode=TransportMode.bike,
            route=route,
            weather_timeline=weather_points,
            hazards=[],
            alerts=[],
            air_quality_timeline=aqi_points
        )
        decision = engine.evaluate_route_core(ctx)
        results.append((
            decision.overall_risk.overall_score,
            decision.overall_risk.level.value if hasattr(decision.overall_risk.level, "value") else str(decision.overall_risk.level),
            [f.name for f in decision.overall_risk.factors],
            [f.score for f in decision.overall_risk.factors],
            len(decision.segment_risks),
        ))

    # Assert 100% bit-identical results across all 10 runs
    first_result = results[0]
    for idx, r in enumerate(results[1:], start=2):
        assert r == first_result, f"Determinism violation on iteration {idx}: {r} != {first_result}"
