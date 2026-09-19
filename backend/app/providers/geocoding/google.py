from datetime import datetime, timezone
import logging
from typing import Optional
import httpx
from app.core.config import settings
from app.providers.geocoding.base import (
    GeocodingProvider,
    GeocodingResult,
    GeocodingResultType,
    GeocodingProvenance,
)

logger = logging.getLogger(__name__)

GOOGLE_GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"


class GoogleGeocodingProvider(GeocodingProvider):
    """
    Google Maps Geocoding API provider.
    Active when google_maps_api_key is provided.
    Provides best-in-class precision for Indian addresses and colloquial landmarks.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: float = 5.0,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        self.api_key = api_key or settings.google_maps_api_key
        self.timeout = timeout
        self._external_client = http_client

    @property
    def provider_name(self) -> str:
        return "google"

    def _classify_google_result(self, result: dict) -> tuple[GeocodingResultType, float, bool]:
        loc_type = result.get("geometry", {}).get("location_type", "")
        types = result.get("types", [])

        if loc_type == "ROOFTOP" or any(t in ("establishment", "point_of_interest", "premise") for t in types):
            return GeocodingResultType.EXACT_LANDMARK, 0.98, True
        if loc_type == "RANGE_INTERPOLATED" or "street_address" in types or "route" in types:
            return GeocodingResultType.STREET, 0.92, True
        if any(t in ("sublocality", "neighborhood", "sublocality_level_1") for t in types):
            return GeocodingResultType.SECTOR_NEIGHBORHOOD, 0.82, False
        if "locality" in types:
            return GeocodingResultType.CITY_LOCALITY, 0.70, False
        if any(t.startswith("administrative_area") for t in types):
            return GeocodingResultType.ADMINISTRATIVE, 0.55, False

        return GeocodingResultType.UNKNOWN, 0.60, False

    async def geocode(self, query: str) -> Optional[GeocodingResult]:
        if not self.api_key:
            return None
        if not query or not query.strip():
            return None

        params = {
            "address": query.strip(),
            "key": self.api_key,
            "region": "in",  # Bias to India
        }

        try:
            if self._external_client:
                response = await self._external_client.get(
                    GOOGLE_GEOCODING_URL,
                    params=params,
                    timeout=self.timeout,
                )
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        GOOGLE_GEOCODING_URL,
                        params=params,
                        timeout=self.timeout,
                    )

            if response.status_code != 200:
                logger.warning(
                    f"Google Geocoding returned status {response.status_code} for query: {query}"
                )
                return None

            data = response.json()
            status = data.get("status")
            if status != "OK":
                logger.debug(f"Google Geocoding status '{status}' for query '{query}'")
                return None

            results = data.get("results", [])
            if not results:
                return None

            best = results[0]
            loc = best.get("geometry", {}).get("location", {})
            lat = float(loc.get("lat", 0.0))
            lng = float(loc.get("lng", 0.0))
            formatted_address = best.get("formatted_address", query)
            res_type, confidence, is_exact = self._classify_google_result(best)

            # Check for ambiguity: multiple results with partial_match
            if len(results) > 1 and best.get("partial_match"):
                confidence = max(0.45, confidence - 0.20)

            return GeocodingResult(
                query=query,
                lat=lat,
                lng=lng,
                display_name=formatted_address,
                provider=self.provider_name,
                result_type=res_type,
                confidence=round(confidence, 2),
                is_exact=is_exact,
                timestamp=datetime.now(timezone.utc),
                provenance=GeocodingProvenance.LIVE_PROVIDER,
                raw_metadata={
                    "place_id": best.get("place_id"),
                    "location_type": best.get("geometry", {}).get("location_type"),
                    "types": best.get("types"),
                },
            )

        except Exception as e:
            logger.warning(f"Google Geocoding failed for query '{query}': {e}")
            return None
