import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.providers.geocoding.pincode import NcrPincodeGeocodingProvider
from app.providers.geocoding.base import (
    GeocodingResultType,
    GeocodingProvenance,
    GeocodingResolutionError,
)
from app.providers.geocoding.fallback import FallbackGeocodingProvider
from app.providers.geocoding.gazetteer import CuratedGazetteerGeocodingProvider


@pytest.mark.asyncio
async def test_pincode_110001_delhi():
    provider = NcrPincodeGeocodingProvider(enable_live_fallback=False)
    res = await provider.geocode("110001")
    
    assert res is not None
    assert abs(res.lat - 28.6328) < 0.01
    assert abs(res.lng - 77.2197) < 0.01
    assert "Connaught Place" in res.display_name
    assert "110001" in res.display_name
    assert res.result_type == GeocodingResultType.POSTAL_CODE
    assert res.confidence == 0.90
    assert res.is_exact is False  # Area centroid, NOT rooftop
    assert res.provenance == GeocodingProvenance.OFFLINE_CURATED


@pytest.mark.asyncio
async def test_pincode_201301_noida():
    provider = NcrPincodeGeocodingProvider(enable_live_fallback=False)
    res = await provider.geocode("Noida 201301")
    
    assert res is not None
    assert abs(res.lat - 28.5700) < 0.01
    assert abs(res.lng - 77.3260) < 0.01
    assert "Noida" in res.display_name
    assert res.result_type == GeocodingResultType.POSTAL_CODE
    assert res.is_exact is False


@pytest.mark.asyncio
async def test_pincode_122002_gurgaon():
    provider = NcrPincodeGeocodingProvider(enable_live_fallback=False)
    res = await provider.geocode("122002")
    
    assert res is not None
    assert abs(res.lat - 28.4950) < 0.01
    assert abs(res.lng - 77.0890) < 0.01
    assert "Cyber City" in res.display_name or "DLF" in res.display_name
    assert res.result_type == GeocodingResultType.POSTAL_CODE
    assert res.is_exact is False


@pytest.mark.asyncio
async def test_invalid_six_digit_pincode():
    provider = NcrPincodeGeocodingProvider(enable_live_fallback=False)
    # Non-existent 6-digit PIN
    res = await provider.geocode("999999")
    assert res is None


@pytest.mark.asyncio
async def test_out_of_ncr_live_fallback():
    provider = NcrPincodeGeocodingProvider(enable_live_fallback=True)
    
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = [
        {
            "Status": "Success",
            "PostOffice": [
                {
                    "Name": "Mumbai G.P.O.",
                    "District": "Mumbai",
                    "State": "Maharashtra",
                    "Latitude": "18.9400",
                    "Longitude": "72.8350",
                }
            ],
        }
    ]
    
    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_resp)):
        res = await provider.geocode("400001")
        assert res is not None
        assert abs(res.lat - 18.94) < 0.01
        assert "Mumbai" in res.display_name
        assert res.is_exact is False
        assert res.provenance == GeocodingProvenance.LIVE_PROVIDER


@pytest.mark.asyncio
async def test_does_not_override_exact_street_address():
    provider = NcrPincodeGeocodingProvider(enable_live_fallback=False)
    # Detailed street query with PIN at the end
    detailed_query = "Flat 402, Building 12, Kasturba Gandhi Marg, Connaught Place, 110001"
    res = await provider.geocode(detailed_query)
    
    # Must yield to higher-confidence exact street geocoder
    assert res is None


@pytest.mark.asyncio
async def test_fallback_chain_integration_priority():
    pin_provider = NcrPincodeGeocodingProvider(enable_live_fallback=False)
    gazetteer = CuratedGazetteerGeocodingProvider()
    chain = FallbackGeocodingProvider(providers=[pin_provider, gazetteer], min_confidence=0.50)
    
    # 1. Pure PIN code query resolves via PIN provider
    res_pin = await chain.geocode("110001")
    assert res_pin.result_type == GeocodingResultType.POSTAL_CODE
    assert res_pin.is_exact is False
    assert "NCR Postal PIN Directory" in res_pin.provider
    
    # 2. Named landmark without PIN resolves via Gazetteer
    res_landmark = await chain.geocode("Connaught Place")
    assert res_landmark.result_type == GeocodingResultType.SECTOR_NEIGHBORHOOD
    assert res_landmark.is_exact is True
    assert res_landmark.provider == "curated-gazetteer"
