from datetime import datetime, timezone
import logging
from typing import Optional
import httpx
from app.providers.geocoding.base import (
    GeocodingProvider,
    GeocodingResult,
    GeocodingResultType,
    GeocodingProvenance,
)

logger = logging.getLogger(__name__)

OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"


class OpenMeteoGeocodingProvider(GeocodingProvider):
    """
    Open-Meteo GeoNames Geocoding API.
    Free, non-commercial/commercial allowed up to 10k/day, no API key required.
    Resolves major cities, districts, and municipalities.
    """

    def __init__(
        self,
        timeout: float = 5.0,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        self.timeout = timeout
        self._external_client = http_client

    @property
    def provider_name(self) -> str:
        return "open-meteo"

    async def geocode(self, query: str) -> Optional[GeocodingResult]:
        if not query or not query.strip():
            return None

        params = {
            "name": query.strip(),
            "count": 5,
            "language": "en",
            "format": "json",
        }

        try:
            if self._external_client:
                response = await self._external_client.get(
                    OPEN_METEO_GEOCODING_URL,
                    params=params,
                    timeout=self.timeout,
                )
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        OPEN_METEO_GEOCODING_URL,
                        params=params,
                        timeout=self.timeout,
                    )

            if response.status_code != 200:
                logger.warning(
                    f"Open-Meteo geocoding returned status {response.status_code} for query: {query}"
                )
                return None

            data = response.json()
            results = data.get("results")
            if not results or not isinstance(results, list):
                return None

            # Prioritize Indian results ('IN')
            in_results = [r for r in results if r.get("country_code", "").upper() == "IN"]
            match = in_results[0] if in_results else results[0]

            lat = float(match["latitude"])
            lng = float(match["longitude"])
            name = match.get("name", query)
            admin1 = match.get("admin1")
            country = match.get("country", "")

            display_parts = [name]
            if admin1 and admin1 != name:
                display_parts.append(admin1)
            if country:
                display_parts.append(country)
            display_name = ", ".join(display_parts)

            # Confidence based on name match accuracy and country match
            exact_name = name.lower() == query.strip().lower()
            confidence = 0.75 if (exact_name and match.get("country_code", "").upper() == "IN") else 0.60

            # Result type
            feature_code = match.get("feature_code", "")
            if feature_code.startswith("PPL"):  # Populated place
                res_type = GeocodingResultType.CITY_LOCALITY
            elif feature_code.startswith("ADM"):  # Administrative division
                res_type = GeocodingResultType.ADMINISTRATIVE
            else:
                res_type = GeocodingResultType.CITY_LOCALITY

            return GeocodingResult(
                query=query,
                lat=lat,
                lng=lng,
                display_name=display_name,
                provider=self.provider_name,
                result_type=res_type,
                confidence=round(confidence, 2),
                is_exact=False,
                timestamp=datetime.now(timezone.utc),
                provenance=GeocodingProvenance.LIVE_PROVIDER,
                raw_metadata={
                    "id": match.get("id"),
                    "country_code": match.get("country_code"),
                    "feature_code": feature_code,
                    "population": match.get("population"),
                },
            )

        except Exception as e:
            logger.warning(f"Open-Meteo geocoding failed for query '{query}': {e}")
            return None
