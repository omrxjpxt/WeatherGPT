import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.services.trip_service import TripService
from app.models.trip import TripRequest
from app.models.enums import TransportMode, AlertSeverity, AlertSourceClass, TripStatus
from app.providers.weather.mock import MockWeatherProvider
from app.providers.routing.mock import MockRoutingProvider
from app.providers.alerts.sachet_cap import NdmaSachetAlertProvider
from app.providers.hazard.delhi_waterlogging import DelhiWaterloggingHazardRepository
from app.providers.transit.dmrc_gtfs import DmrcMetroProvider
from app.providers.geocoding.pincode import NcrPincodeGeocodingProvider
from app.providers.geocoding.gazetteer import CuratedGazetteerGeocodingProvider
from app.providers.geocoding.fallback import FallbackGeocodingProvider
from app.providers.air_quality.mock import MockAirQualityProvider


def _build_phase21_trip_service(
    sachet_client: httpx.AsyncClient | None = None,
    mock_weather_timeline=None,
) -> TripService:
    weather_provider = MockWeatherProvider()
    routing_provider = MockRoutingProvider()
    
    # SACHET Alert Provider
    alert_provider = NdmaSachetAlertProvider(
        client=sachet_client,
        cache_ttl_seconds=300
    )
    
    # Delhi Waterlogging Repository
    hazard_repo = DelhiWaterloggingHazardRepository()
    
    # DMRC Metro Provider
    metro_provider = DmrcMetroProvider()
    
    # Fallback geocoding with NCR PIN fast-path
    pin_provider = NcrPincodeGeocodingProvider(enable_live_fallback=False)
    gazetteer = CuratedGazetteerGeocodingProvider()
    geocoding_provider = FallbackGeocodingProvider(
        providers=[pin_provider, gazetteer],
        min_confidence=0.50
    )
    
    aqi_provider = MockAirQualityProvider(default_aqi=140, default_pm25=50.0)
    
    return TripService(
        weather_provider=weather_provider,
        routing_provider=routing_provider,
        alert_provider=alert_provider,
        hazard_repository=hazard_repo,
        geocoding_provider=geocoding_provider,
        air_quality_provider=aqi_provider,
        metro_provider=metro_provider,
    )


@pytest.mark.asyncio
async def test_trip_analysis_with_pin_origin_and_destination():
    # Mock client returns empty RSS feed for SACHET
    mock_sachet = AsyncMock(spec=httpx.AsyncClient)
    mock_sachet.get.return_value = MagicMock(status_code=200, content=b"<rss><channel></channel></rss>", headers={})
    
    service = _build_phase21_trip_service(sachet_client=mock_sachet)
    
    request = TripRequest(
        origin="110001",       # Connaught Place PIN
        destination="201301",  # Noida Sector 16/18 PIN
        departure_time=datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc),
        mode=TransportMode.car,
    )
    
    response = await service.analyze_trip(request)
    
    assert response.status == TripStatus.success
    assert response.risk is not None
    assert response.geocoding_provenance is not None
    assert "110001" in response.request.origin
    assert "201301" in response.request.destination
    assert any("NDMA SACHET" in s.name for s in response.sources)


@pytest.mark.asyncio
async def test_trip_analysis_with_dmrc_metro_route():
    mock_sachet = AsyncMock(spec=httpx.AsyncClient)
    mock_sachet.get.return_value = MagicMock(status_code=200, content=b"<rss><channel></channel></rss>", headers={})
    
    service = _build_phase21_trip_service(sachet_client=mock_sachet)
    
    request = TripRequest(
        origin="110001",       # Connaught Place (near Rajiv Chowk)
        destination="201309",  # Noida Sector 62 PIN
        departure_time=datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc),
        mode=TransportMode.metro,
    )
    
    response = await service.analyze_trip(request)
    
    assert response.status == TripStatus.success
    assert response.risk is not None
    assert response.distance_km > 0
    assert response.estimated_duration.total_seconds() > 0
    # DMRC transit provider is cited in sources
    assert any("DMRC" in s.name for s in response.sources)


@pytest.mark.asyncio
async def test_trip_analysis_with_sachet_unavailable_graceful_degradation():
    mock_sachet = AsyncMock(spec=httpx.AsyncClient)
    # Simulate government gateway timeout
    mock_sachet.get.side_effect = httpx.TimeoutException("Government gateway timeout")
    
    service = _build_phase21_trip_service(sachet_client=mock_sachet)
    
    request = TripRequest(
        origin="110001",
        destination="201301",
        departure_time=datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc),
        mode=TransportMode.car,
    )
    
    # Must succeed with graceful degradation, zero fabricated alerts
    response = await service.analyze_trip(request)
    assert response.status == TripStatus.success
    assert response.risk is not None
    # No emergency alert overrides applied when feed fails
    assert response.recommendation is not None


@pytest.mark.asyncio
async def test_guest_vs_authenticated_trip_evaluation_parity():
    mock_sachet = AsyncMock(spec=httpx.AsyncClient)
    mock_sachet.get.return_value = MagicMock(status_code=200, content=b"<rss><channel></channel></rss>", headers={})
    
    service = _build_phase21_trip_service(sachet_client=mock_sachet)
    
    request = TripRequest(
        origin="110001",
        destination="122002",
        departure_time=datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc),
        mode=TransportMode.car,
    )
    
    # 1. Guest execution (uid=None)
    guest_res = await service.analyze_trip(request, uid=None)
    
    # 2. Authenticated execution (uid="auth-user-999")
    auth_res = await service.analyze_trip(request, uid="auth-user-999")
    
    # Both produce identical decision outputs
    assert guest_res.risk.overall_score == auth_res.risk.overall_score
    assert guest_res.risk.level == auth_res.risk.level
    assert guest_res.recommendation.headline == auth_res.recommendation.headline
    assert guest_res.recommendation.body == auth_res.recommendation.body
    assert guest_res.distance_km == auth_res.distance_km


@pytest.mark.asyncio
async def test_10x_concurrency_determinism_all_phase21_providers():
    mock_sachet = AsyncMock(spec=httpx.AsyncClient)
    mock_sachet.get.return_value = MagicMock(status_code=200, content=b"<rss><channel></channel></rss>", headers={})
    
    service = _build_phase21_trip_service(sachet_client=mock_sachet)
    
    request = TripRequest(
        origin="110001",
        destination="201301",
        departure_time=datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc),
        mode=TransportMode.car,
    )
    
    # Run 10 evaluations concurrently with asyncio.gather
    tasks = [service.analyze_trip(request) for _ in range(10)]
    responses = await asyncio.gather(*tasks)
    
    first = responses[0]
    for idx, resp in enumerate(responses[1:], start=2):
        assert resp.risk.overall_score == first.risk.overall_score, f"Determinism mismatch on run {idx}"
        assert resp.risk.level == first.risk.level
        assert resp.recommendation.headline == first.recommendation.headline
        assert resp.recommendation.body == first.recommendation.body
        assert resp.distance_km == first.distance_km
        assert resp.estimated_duration == first.estimated_duration
        assert len(resp.routes) == len(first.routes)
        assert resp.routes[0].route_id == first.routes[0].route_id
