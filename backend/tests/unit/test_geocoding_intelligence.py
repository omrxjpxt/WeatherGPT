import asyncio
import time
from datetime import datetime, timezone
import pytest
import httpx

from app.providers.geocoding.base import (
    GeocodingProvider,
    GeocodingResult,
    GeocodingResultType,
    GeocodingProvenance,
    GeocodingResolutionError,
    parse_coordinate_query,
)
from app.providers.geocoding.gazetteer import CuratedGazetteerGeocodingProvider
from app.providers.geocoding.nominatim import NominatimGeocodingProvider
from app.providers.geocoding.open_meteo import OpenMeteoGeocodingProvider
from app.providers.geocoding.google import GoogleGeocodingProvider
from app.providers.geocoding.fallback import FallbackGeocodingProvider, MockGeocodingProvider
from app.models.trip import TripRequest
from app.models.enums import TransportMode
from app.services.trip_service import TripService
from app.providers.weather.mock import MockWeatherProvider
from app.providers.routing.mock import MockRoutingProvider
from app.providers.alerts.mock import MockAlertProvider


@pytest.mark.asyncio
async def test_coordinate_query_parsing():
    """Validates direct numeric coordinate extraction with exact confidence and user provenance."""
    res = parse_coordinate_query("28.6270, 77.3650")
    assert res is not None
    assert res.lat == 28.6270
    assert res.lng == 77.3650
    assert res.result_type == GeocodingResultType.COORDINATE
    assert res.confidence == 1.0
    assert res.is_exact is True
    assert res.provenance == GeocodingProvenance.USER_COORDINATE
    assert res.provider == "coordinate"

    # Variations
    res_no_space = parse_coordinate_query("28.4942,77.0860")
    assert res_no_space is not None
    assert res_no_space.lat == 28.4942

    # Non-coordinates return None
    assert parse_coordinate_query("Connaught Place") is None
    assert parse_coordinate_query("Noida Sector 62") is None


@pytest.mark.asyncio
async def test_curated_gazetteer_landmarks_and_sectors():
    """Verifies curated NCR gazetteer returns high-confidence exact landmarks and sectors."""
    gazetteer = CuratedGazetteerGeocodingProvider()
    assert gazetteer.provider_name == "curated-gazetteer"

    # 1. Exact Landmark: Cyber Hub
    hub_res = await gazetteer.geocode("DLF Cyber Hub")
    assert hub_res is not None
    assert hub_res.lat == 28.4942
    assert hub_res.lng == 77.0860
    assert hub_res.provenance == GeocodingProvenance.OFFLINE_CURATED
    assert hub_res.result_type == GeocodingResultType.EXACT_LANDMARK
    assert hub_res.confidence >= 0.90
    assert hub_res.is_exact is True

    # 2. Sector / Neighborhood: Noida Sector 62
    noida_res = await gazetteer.geocode("Noida Sector 62")
    assert noida_res is not None
    assert noida_res.lat == 28.6270
    assert noida_res.lng == 77.3650
    assert noida_res.provenance == GeocodingProvenance.OFFLINE_CURATED
    assert noida_res.result_type == GeocodingResultType.SECTOR_NEIGHBORHOOD
    assert noida_res.confidence >= 0.90

    # 3. Hospital / Landmark: AIIMS
    aiims_res = await gazetteer.geocode("aiims delhi")
    assert aiims_res is not None
    assert aiims_res.lat == 28.5672
    assert aiims_res.result_type == GeocodingResultType.EXACT_LANDMARK

    # 4. Unknown query returns None
    unknown = await gazetteer.geocode("Atlantis Submerged City")
    assert unknown is None


@pytest.mark.asyncio
async def test_nominatim_rate_limiting_enforcement(monkeypatch):
    """Verifies that consecutive Nominatim calls respect the 1 request/sec rate limiter."""
    call_times = []

    async def mock_get(url, params, headers, timeout):
        call_times.append(time.monotonic())
        mock_data = [{
            "lat": "28.6139",
            "lon": "77.2090",
            "display_name": "New Delhi, Delhi, India",
            "class": "place",
            "type": "city",
            "importance": 0.8,
        }]
        return httpx.Response(200, json=mock_data, request=httpx.Request("GET", url))

    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda req: None))
    monkeypatch.setattr(client, "get", mock_get)

    provider = NominatimGeocodingProvider(http_client=client)

    # Perform 2 back-to-back calls
    start = time.monotonic()
    await provider.geocode("Delhi")
    await provider.geocode("Noida")
    total_duration = time.monotonic() - start

    assert len(call_times) == 2
    # Second call should have waited >= 1.0s
    assert (call_times[1] - call_times[0]) >= 1.0
    assert total_duration >= 1.0


@pytest.mark.asyncio
async def test_nominatim_classification_and_ambiguity_penalty(monkeypatch):
    """Verifies OSM amenity, highway, suburb classification and ambiguity detection."""
    # Test 1: Amenity -> EXACT_LANDMARK
    amenity_item = [{
        "lat": "28.5672",
        "lon": "77.2100",
        "display_name": "AIIMS Hospital, New Delhi",
        "class": "amenity",
        "type": "hospital",
        "importance": 0.75,
    }]
    client1 = httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=amenity_item)))
    p1 = NominatimGeocodingProvider(http_client=client1)
    res1 = await p1.geocode("AIIMS Hospital")
    assert res1.result_type == GeocodingResultType.EXACT_LANDMARK
    assert res1.is_exact is True
    assert res1.confidence >= 0.85

    # Test 2: Ambiguous result with 2 divergent coordinates
    ambiguous_items = [
        {"lat": "28.5000", "lon": "77.1000", "display_name": "Location A", "class": "place", "type": "village", "importance": 0.50},
        {"lat": "22.5000", "lon": "88.1000", "display_name": "Location B (disparate state)", "class": "place", "type": "village", "importance": 0.49},
    ]
    client2 = httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=ambiguous_items)))
    p2 = NominatimGeocodingProvider(http_client=client2)
    res2 = await p2.geocode("Ambiguous Village")
    assert res2.confidence < 0.50  # Confidence penalized below threshold


@pytest.mark.asyncio
async def test_open_meteo_geocoding_parsing(monkeypatch):
    """Verifies Open-Meteo GeoNames parsing and India country prioritization."""
    mock_payload = {
        "results": [
            {
                "id": 1,
                "name": "Noida",
                "latitude": 28.57,
                "longitude": 77.32,
                "country_code": "IN",
                "admin1": "Uttar Pradesh",
                "country": "India",
                "feature_code": "PPLA2"
            }
        ]
    }
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=mock_payload)))
    provider = OpenMeteoGeocodingProvider(http_client=client)
    res = await provider.geocode("Noida")
    assert res is not None
    assert res.lat == 28.57
    assert res.lng == 77.32
    assert "Uttar Pradesh" in res.display_name
    assert res.provider == "open-meteo"
    assert res.result_type == GeocodingResultType.CITY_LOCALITY
    assert res.is_exact is False


@pytest.mark.asyncio
async def test_google_geocoding_location_types(monkeypatch):
    """Verifies Google Geocoding ROOFTOP, APPROXIMATE, and partial_match handling."""
    # ROOFTOP
    rooftop_payload = {
        "status": "OK",
        "results": [{
            "geometry": {
                "location": {"lat": 28.4942, "lng": 77.0860},
                "location_type": "ROOFTOP"
            },
            "types": ["establishment", "point_of_interest"],
            "formatted_address": "DLF Cyber Hub, Gurugram, India",
            "place_id": "ChIJ12345"
        }]
    }
    client1 = httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=rooftop_payload)))
    g1 = GoogleGeocodingProvider(api_key="fake-key", http_client=client1)
    res1 = await g1.geocode("Cyber Hub")
    assert res1.result_type == GeocodingResultType.EXACT_LANDMARK
    assert res1.confidence >= 0.95
    assert res1.is_exact is True

    # Partial match penalty
    partial_payload = {
        "status": "OK",
        "results": [
            {
                "geometry": {"location": {"lat": 28.0, "lng": 77.0}, "location_type": "APPROXIMATE"},
                "types": ["locality"],
                "formatted_address": "Vague Town",
                "partial_match": True
            },
            {
                "geometry": {"location": {"lat": 29.0, "lng": 78.0}, "location_type": "APPROXIMATE"},
                "types": ["locality"],
                "formatted_address": "Other Town",
                "partial_match": True
            }
        ]
    }
    client2 = httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=partial_payload)))
    g2 = GoogleGeocodingProvider(api_key="fake-key", http_client=client2)
    res2 = await g2.geocode("Vague")
    assert res2.confidence <= 0.50


@pytest.mark.asyncio
async def test_fallback_geocoding_chain_order_and_caching():
    """Verifies provider chain traversal, caching, and low-confidence rejection."""
    class FailingProvider(GeocodingProvider):
        @property
        def provider_name(self): return "failing"
        async def geocode(self, query): raise ConnectionError("Downstream failed")

    class LowConfidenceProvider(GeocodingProvider):
        @property
        def provider_name(self): return "low_conf"
        async def geocode(self, query):
            return GeocodingResult(
                query=query, lat=20.0, lng=70.0, display_name="Low Conf",
                provider="low_conf", confidence=0.35, is_exact=False,
                timestamp=datetime.now(timezone.utc), provenance=GeocodingProvenance.LIVE_PROVIDER
            )

    curated = CuratedGazetteerGeocodingProvider()

    chain = FallbackGeocodingProvider(
        providers=[FailingProvider(), LowConfidenceProvider(), curated],
        min_confidence=0.50
    )

    # 1. Resolves successfully via 3rd provider in chain (curated gazetteer)
    res = await chain.geocode("Connaught Place")
    assert res.provider == "curated-gazetteer"
    assert res.provenance == GeocodingProvenance.OFFLINE_CURATED

    # 2. Subsequent call hits in-memory cache
    cached_res = await chain.geocode("Connaught Place")
    assert cached_res.lat == res.lat

    # 3. Unresolved / low confidence raises GeocodingResolutionError
    with pytest.raises(GeocodingResolutionError) as exc_info:
        await chain.geocode("Unresolvable Nonexistent Place")
    assert exc_info.value.status == "unresolved_location"


@pytest.mark.asyncio
async def test_trip_service_geocoding_provenance_and_ambiguity_rejection():
    """Verifies that TripService retains geocoding provenance and rejects ambiguous inputs."""
    mock_geo = MockGeocodingProvider()
    service = TripService(
        weather_provider=MockWeatherProvider(),
        routing_provider=MockRoutingProvider(),
        alert_provider=MockAlertProvider(),
        geocoding_provider=mock_geo
    )

    # Valid trip
    valid_req = TripRequest(
        origin="Noida Sector 62",
        destination="Gurgaon Cyber Hub",
        departure_time=datetime(2026, 9, 20, 9, 0, tzinfo=timezone.utc),
        mode=TransportMode.car
    )
    res = await service.analyze_trip(valid_req)
    assert res.geocoding_provenance is not None
    assert "origin_provider" in res.geocoding_provenance
    assert res.geocoding_provenance["origin_provenance"] == "mock_test"
    assert res.geocoding_provenance["destination_confidence"] == "1.0"

    # Ambiguous origin rejection
    ambiguous_req = TripRequest(
        origin="ambiguous crossroads",
        destination="Gurgaon Cyber Hub",
        departure_time=datetime(2026, 9, 20, 9, 0, tzinfo=timezone.utc),
        mode=TransportMode.car
    )
    # TripService with FallbackGeocodingProvider rejecting low confidence
    strict_chain = FallbackGeocodingProvider(providers=[mock_geo], min_confidence=0.50)
    strict_service = TripService(
        weather_provider=MockWeatherProvider(),
        routing_provider=MockRoutingProvider(),
        alert_provider=MockAlertProvider(),
        geocoding_provider=strict_chain
    )
    with pytest.raises(GeocodingResolutionError):
        await strict_service.analyze_trip(ambiguous_req)
