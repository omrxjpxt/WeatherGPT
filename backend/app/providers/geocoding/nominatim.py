import asyncio
from datetime import datetime, timezone
import logging
import time
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

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"


class NominatimGeocodingProvider(GeocodingProvider):
    """
    OpenStreetMap Nominatim Geocoder.
    Enforces a strict 1 request/second rate-limit guard adhering to OSM Acceptable Use Policy.
    """

    def __init__(
        self,
        user_agent: Optional[str] = None,
        timeout: float = 5.0,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        self.user_agent = user_agent or settings.nominatim_user_agent
        self.timeout = timeout
        self._external_client = http_client
        self._lock = asyncio.Lock()
        self._last_request_time: float = 0.0

    @property
    def provider_name(self) -> str:
        return "nominatim"

    async def _rate_limit_wait(self):
        """Ensures at least 1.05s has elapsed since the previous request."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if elapsed < 1.05:
                wait_time = 1.05 - elapsed
                await asyncio.sleep(wait_time)
            self._last_request_time = time.monotonic()

    def _classify_osm_result(self, item: dict) -> tuple[GeocodingResultType, float, bool]:
        osm_class = item.get("class", "")
        osm_type = item.get("type", "")
        importance = float(item.get("importance", 0.5))

        if osm_class in ("amenity", "building", "tourism", "shop", "leisure", "historic"):
            return GeocodingResultType.EXACT_LANDMARK, min(0.95, max(0.85, 0.85 + importance * 0.1)), True
        if osm_class == "highway" or "road" in osm_type or "street" in osm_type:
            return GeocodingResultType.STREET, min(0.92, max(0.80, 0.80 + importance * 0.1)), True
        if osm_type in ("suburb", "neighbourhood", "quarter", "residential"):
            return GeocodingResultType.SECTOR_NEIGHBORHOOD, min(0.88, max(0.75, 0.75 + importance * 0.1)), False
        if osm_type in ("city", "town", "village", "municipality"):
            return GeocodingResultType.CITY_LOCALITY, min(0.80, max(0.60, 0.60 + importance * 0.1)), False
        if osm_class == "boundary" or osm_type in ("state", "administrative"):
            return GeocodingResultType.ADMINISTRATIVE, 0.50, False

        return GeocodingResultType.UNKNOWN, 0.55, False

    async def geocode(self, query: str) -> Optional[GeocodingResult]:
        if not query or not query.strip():
            return None

        await self._rate_limit_wait()

        headers = {
            "User-Agent": self.user_agent,
            "Accept-Language": "en",
        }
        params = {
            "q": query.strip(),
            "format": "jsonv2",
            "limit": 3,
            "countrycodes": "in",  # Prioritize Indian geographic entities
        }

        try:
            if self._external_client:
                response = await self._external_client.get(
                    NOMINATIM_SEARCH_URL,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                )
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        NOMINATIM_SEARCH_URL,
                        params=params,
                        headers=headers,
                        timeout=self.timeout,
                    )

            if response.status_code != 200:
                logger.warning(
                    f"Nominatim returned status {response.status_code} for query: {query}"
                )
                return None

            data = response.json()
            if not data or not isinstance(data, list):
                return None

            best_match = data[0]
            lat = float(best_match["lat"])
            lng = float(best_match["lon"])
            display_name = best_match.get("display_name", query)
            res_type, confidence, is_exact = self._classify_osm_result(best_match)

            # Ambiguity guard: If 2 top results have very similar importance but divergent coords (> 50km apart)
            if len(data) > 1:
                second = data[1]
                imp1 = float(best_match.get("importance", 0.5))
                imp2 = float(second.get("importance", 0.5))
                lat2 = float(second.get("lat", 0))
                lng2 = float(second.get("lon", 0))
                dist_approx = abs(lat - lat2) + abs(lng - lng2)
                if abs(imp1 - imp2) < 0.05 and dist_approx > 0.5:
                    # Conflicting ambiguous results
                    confidence = max(0.40, confidence - 0.25)

            return GeocodingResult(
                query=query,
                lat=lat,
                lng=lng,
                display_name=display_name,
                provider=self.provider_name,
                result_type=res_type,
                confidence=round(confidence, 2),
                is_exact=is_exact,
                timestamp=datetime.now(timezone.utc),
                provenance=GeocodingProvenance.LIVE_PROVIDER,
                raw_metadata={
                    "osm_id": best_match.get("osm_id"),
                    "place_rank": best_match.get("place_rank"),
                    "importance": best_match.get("importance"),
                },
            )

        except Exception as e:
            logger.warning(f"Nominatim geocoding failed for query '{query}': {e}")
            return None
