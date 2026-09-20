from datetime import datetime, timezone
import logging
from typing import Optional
from app.providers.geocoding.base import (
    GeocodingProvider,
    GeocodingResult,
    GeocodingResultType,
    GeocodingProvenance,
    GeocodingResolutionError,
    parse_coordinate_query,
)
from app.providers.geocoding.gazetteer import CuratedGazetteerGeocodingProvider

logger = logging.getLogger(__name__)


class FallbackGeocodingProvider(GeocodingProvider):
    """
    Confidence-aware fallback geocoding chain:
    1. Direct numeric coordinate check (confidence 1.0)
    2. Primary Provider (e.g. Google Geocoding)
    3. Secondary Provider (e.g. Nominatim)
    4. Tertiary Provider (e.g. Open-Meteo GeoNames)
    5. Curated NCR Gazetteer (Offline, deterministic)

    Guarantees:
    - Ambiguous or low-confidence results (< min_confidence) are rejected.
    - Preserves provider provenance (live vs offline curated vs coordinate).
    - In-memory caching for resolved queries.
    """

    def __init__(
        self,
        providers: Optional[list[GeocodingProvider]] = None,
        min_confidence: float = 0.50,
        max_cache_entries: int = 1000,
    ):
        self.providers = providers or [CuratedGazetteerGeocodingProvider()]
        self.min_confidence = min_confidence
        self.max_cache_entries = max_cache_entries
        self._cache: dict[str, GeocodingResult] = {}

    @property
    def provider_name(self) -> str:
        return "fallback"

    def _store_in_cache(self, key: str, result: GeocodingResult) -> None:
        """Stores geocoding result with FIFO eviction if cache exceeds bounds."""
        if len(self._cache) >= self.max_cache_entries:
            oldest_key = next(iter(self._cache))
            self._cache.pop(oldest_key, None)
        self._cache[key] = result

    async def geocode(self, query: str) -> Optional[GeocodingResult]:
        if not query or not query.strip():
            raise GeocodingResolutionError(
                message="Location query cannot be empty",
                query=query,
                status="empty_query",
            )

        cleaned_query = query.strip()
        cache_key = cleaned_query.lower()

        # 1. Direct coordinate check
        coord_result = parse_coordinate_query(cleaned_query)
        if coord_result:
            return coord_result

        # 2. In-memory cache check
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 3. Iterate through fallback chain
        for provider in self.providers:
            try:
                result = await provider.geocode(cleaned_query)
                if result:
                    # Low-confidence threshold check
                    if result.confidence < self.min_confidence:
                        logger.warning(
                            f"Provider '{provider.provider_name}' resolved '{query}' with low confidence "
                            f"({result.confidence:.2f} < {self.min_confidence:.2f}). Rejecting."
                        )
                        continue

                    # Valid resolution
                    self._store_in_cache(cache_key, result)
                    return result
            except Exception as e:
                logger.warning(
                    f"Geocoding provider '{provider.provider_name}' failed for query '{cleaned_query}': {e}"
                )
                continue

        # If nothing resolved with sufficient confidence
        raise GeocodingResolutionError(
            message=f"Could not resolve location '{query}' with sufficient confidence. Please specify a more detailed landmark, sector, or city.",
            query=query,
            status="unresolved_location",
        )


class MockGeocodingProvider(GeocodingProvider):
    """
    Deterministic mock geocoding provider for unit tests.
    Explicitly tags results with MOCK_TEST provenance.
    """

    def __init__(self, mock_locations: Optional[dict[str, tuple[float, float, str]]] = None):
        self.mock_locations = mock_locations or {
            "noida": (28.6270, 77.3650, "Noida Sector 62 (Mock)"),
            "gurgaon": (28.4942, 77.0860, "Gurgaon Cyber Hub (Mock)"),
            "delhi": (28.6139, 77.2090, "Delhi Connaught Place (Mock)"),
        }

    @property
    def provider_name(self) -> str:
        return "mock"

    async def geocode(self, query: str) -> Optional[GeocodingResult]:
        cleaned = query.strip().lower()
        coord_result = parse_coordinate_query(cleaned)
        if coord_result:
            return coord_result

        for key, (lat, lng, display) in self.mock_locations.items():
            if key in cleaned:
                return GeocodingResult(
                    query=query,
                    lat=lat,
                    lng=lng,
                    display_name=display,
                    provider="mock",
                    result_type=GeocodingResultType.SECTOR_NEIGHBORHOOD,
                    confidence=1.0,
                    is_exact=True,
                    timestamp=datetime.now(timezone.utc),
                    provenance=GeocodingProvenance.MOCK_TEST,
                    raw_metadata={"mock": True},
                )

        # Ambiguity / low confidence simulation
        if "ambiguous" in cleaned:
            return GeocodingResult(
                query=query,
                lat=28.0,
                lng=77.0,
                display_name="Ambiguous Location",
                provider="mock",
                result_type=GeocodingResultType.UNKNOWN,
                confidence=0.30,
                is_exact=False,
                timestamp=datetime.now(timezone.utc),
                provenance=GeocodingProvenance.MOCK_TEST,
                raw_metadata={"ambiguous": True},
            )

        return None
