from datetime import datetime, timezone
import re
from typing import Optional
from app.providers.geocoding.base import (
    GeocodingProvider,
    GeocodingResult,
    GeocodingResultType,
    GeocodingProvenance,
)

# Curated registry of prominent Delhi-NCR navigation points
# Coordinates verified against official Survey of India / OpenStreetMap NCR geographic records
CURATED_NCR_LOCATIONS = {
    # Central Delhi & Historic
    "connaught place": (28.6315, 77.2167, "Connaught Place, New Delhi", GeocodingResultType.SECTOR_NEIGHBORHOOD),
    "cp": (28.6315, 77.2167, "Connaught Place, New Delhi", GeocodingResultType.SECTOR_NEIGHBORHOOD),
    "rajiv chowk": (28.6328, 77.2195, "Rajiv Chowk, New Delhi", GeocodingResultType.EXACT_LANDMARK),
    "india gate": (28.6129, 77.2295, "India Gate, Central Delhi", GeocodingResultType.EXACT_LANDMARK),
    "chandni chowk": (28.6506, 77.2303, "Chandni Chowk, Old Delhi", GeocodingResultType.SECTOR_NEIGHBORHOOD),
    "kashmere gate": (28.6675, 77.2285, "Kashmere Gate, Delhi", GeocodingResultType.EXACT_LANDMARK),
    "karol bagh": (28.6517, 77.1906, "Karol Bagh, New Delhi", GeocodingResultType.SECTOR_NEIGHBORHOOD),
    "new delhi railway station": (28.6429, 77.2193, "New Delhi Railway Station", GeocodingResultType.EXACT_LANDMARK),
    "ndls": (28.6429, 77.2193, "New Delhi Railway Station", GeocodingResultType.EXACT_LANDMARK),

    # South Delhi
    "aiims": (28.5672, 77.2100, "AIIMS, Ansari Nagar, New Delhi", GeocodingResultType.EXACT_LANDMARK),
    "aiims delhi": (28.5672, 77.2100, "AIIMS, Ansari Nagar, New Delhi", GeocodingResultType.EXACT_LANDMARK),
    "saket": (28.5245, 77.2066, "Saket, South Delhi", GeocodingResultType.SECTOR_NEIGHBORHOOD),
    "hauz khas": (28.5494, 77.2001, "Hauz Khas, South Delhi", GeocodingResultType.SECTOR_NEIGHBORHOOD),
    "nehru place": (28.5492, 77.2519, "Nehru Place, New Delhi", GeocodingResultType.SECTOR_NEIGHBORHOOD),
    "lajpat nagar": (28.5700, 77.2400, "Lajpat Nagar, South Delhi", GeocodingResultType.SECTOR_NEIGHBORHOOD),
    "dhaula kuan": (28.5923, 77.1617, "Dhaula Kuan, New Delhi", GeocodingResultType.EXACT_LANDMARK),
    "aerocity": (28.5488, 77.1210, "Aerocity, New Delhi", GeocodingResultType.SECTOR_NEIGHBORHOOD),
    "igi airport": (28.5562, 77.1000, "Indira Gandhi International Airport, Terminal 3", GeocodingResultType.EXACT_LANDMARK),
    "delhi airport": (28.5562, 77.1000, "Indira Gandhi International Airport, Terminal 3", GeocodingResultType.EXACT_LANDMARK),

    # West & North Delhi
    "dwarka": (28.5921, 77.0460, "Dwarka, Southwest Delhi", GeocodingResultType.SECTOR_NEIGHBORHOOD),
    "dwarka sector 21": (28.5523, 77.0583, "Dwarka Sector 21 Metro, Delhi", GeocodingResultType.EXACT_LANDMARK),
    "rohini": (28.7166, 77.1189, "Rohini, North West Delhi", GeocodingResultType.SECTOR_NEIGHBORHOOD),
    "pitampura": (28.6989, 77.1386, "Pitampura, North West Delhi", GeocodingResultType.SECTOR_NEIGHBORHOOD),
    "janakpuri": (28.6219, 77.0878, "Janakpuri, West Delhi", GeocodingResultType.SECTOR_NEIGHBORHOOD),

    # East Delhi
    "anand vihar": (28.6469, 77.3160, "Anand Vihar ISBT / Railway Terminal, Delhi", GeocodingResultType.EXACT_LANDMARK),
    "mayur vihar": (28.6094, 77.2989, "Mayur Vihar Phase 1, East Delhi", GeocodingResultType.SECTOR_NEIGHBORHOOD),
    "akshardham": (28.6127, 77.2773, "Akshardham Temple, East Delhi", GeocodingResultType.EXACT_LANDMARK),
    "laxmi nagar": (28.6306, 77.2776, "Laxmi Nagar, East Delhi", GeocodingResultType.SECTOR_NEIGHBORHOOD),

    # Noida & Greater Noida
    "noida sector 62": (28.6270, 77.3650, "Sector 62, Noida, Uttar Pradesh", GeocodingResultType.SECTOR_NEIGHBORHOOD),
    "sector 62 noida": (28.6270, 77.3650, "Sector 62, Noida, Uttar Pradesh", GeocodingResultType.SECTOR_NEIGHBORHOOD),
    "noida 62": (28.6270, 77.3650, "Sector 62, Noida, Uttar Pradesh", GeocodingResultType.SECTOR_NEIGHBORHOOD),
    "noida sector 18": (28.5708, 77.3261, "Sector 18 (Atta Market), Noida, Uttar Pradesh", GeocodingResultType.SECTOR_NEIGHBORHOOD),
    "botanical garden": (28.5645, 77.3343, "Botanical Garden Metro, Noida", GeocodingResultType.EXACT_LANDMARK),
    "noida sector 128": (28.5138, 77.3712, "Sector 128 (Jaypee Wish Town), Noida", GeocodingResultType.SECTOR_NEIGHBORHOOD),
    "noida sector 137": (28.5085, 77.4042, "Sector 137, Noida Expressway", GeocodingResultType.SECTOR_NEIGHBORHOOD),
    "noida sector 150": (28.4417, 77.4694, "Sector 150, Noida", GeocodingResultType.SECTOR_NEIGHBORHOOD),
    "noida electronic city": (28.6280, 77.3742, "Noida Electronic City Metro Station", GeocodingResultType.EXACT_LANDMARK),
    "pari chowk": (28.4674, 77.5138, "Pari Chowk, Greater Noida", GeocodingResultType.EXACT_LANDMARK),
    "greater noida": (28.4744, 77.5040, "Greater Noida, Uttar Pradesh", GeocodingResultType.CITY_LOCALITY),
    "noida": (28.5700, 77.3200, "Noida, Gautam Buddha Nagar, Uttar Pradesh", GeocodingResultType.CITY_LOCALITY),

    # Gurgaon / Gurugram
    "cyber hub": (28.4942, 77.0860, "DLF Cyber Hub, DLF Phase 2, Gurugram", GeocodingResultType.EXACT_LANDMARK),
    "dlf cyber hub": (28.4942, 77.0860, "DLF Cyber Hub, DLF Phase 2, Gurugram", GeocodingResultType.EXACT_LANDMARK),
    "gurgaon cyber hub": (28.4942, 77.0860, "DLF Cyber Hub, DLF Phase 2, Gurugram", GeocodingResultType.EXACT_LANDMARK),
    "cyber hub gurgaon": (28.4942, 77.0860, "DLF Cyber Hub, DLF Phase 2, Gurugram", GeocodingResultType.EXACT_LANDMARK),
    "cyber city": (28.4942, 77.0880, "DLF Cyber City, Gurugram", GeocodingResultType.SECTOR_NEIGHBORHOOD),
    "iffco chowk": (28.4727, 77.0725, "IFFCO Chowk, Gurugram", GeocodingResultType.EXACT_LANDMARK),
    "ambience mall": (28.5042, 77.0968, "Ambience Mall, Gurugram", GeocodingResultType.EXACT_LANDMARK),
    "mg road gurgaon": (28.4799, 77.0802, "MG Road, Gurugram", GeocodingResultType.STREET),
    "sector 29 gurgaon": (28.4682, 77.0632, "Sector 29, Gurugram", GeocodingResultType.SECTOR_NEIGHBORHOOD),
    "golf course road": (28.4552, 77.0987, "Golf Course Road, Gurugram", GeocodingResultType.STREET),
    "sohna road": (28.4124, 77.0421, "Sohna Road, Gurugram", GeocodingResultType.STREET),
    "udyog vihar": (28.5028, 77.0805, "Udyog Vihar Phase 1-5, Gurugram", GeocodingResultType.SECTOR_NEIGHBORHOOD),
    "gurgaon": (28.4595, 77.0266, "Gurugram, Haryana", GeocodingResultType.CITY_LOCALITY),
    "gurugram": (28.4595, 77.0266, "Gurugram, Haryana", GeocodingResultType.CITY_LOCALITY),

    # Ghaziabad & Faridabad
    "indirapuram": (28.6382, 77.3686, "Indirapuram, Ghaziabad", GeocodingResultType.SECTOR_NEIGHBORHOOD),
    "vaishali": (28.6433, 77.3385, "Vaishali, Ghaziabad", GeocodingResultType.SECTOR_NEIGHBORHOOD),
    "kaushambi": (28.6454, 77.3241, "Kaushambi, Ghaziabad", GeocodingResultType.SECTOR_NEIGHBORHOOD),
    "ghaziabad": (28.6692, 77.4538, "Ghaziabad, Uttar Pradesh", GeocodingResultType.CITY_LOCALITY),
    "faridabad": (28.4089, 77.3178, "Faridabad, Haryana", GeocodingResultType.CITY_LOCALITY),
    "delhi": (28.6139, 77.2090, "Delhi, National Capital Territory of Delhi", GeocodingResultType.CITY_LOCALITY),
    "new delhi": (28.6139, 77.2090, "New Delhi, Delhi", GeocodingResultType.CITY_LOCALITY),
}


def _normalize_key(text: str) -> str:
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return " ".join(cleaned.split())


class CuratedGazetteerGeocodingProvider(GeocodingProvider):
    """
    Offline, in-memory gazetteer for major Delhi-NCR transport corridors.
    Guarantees deterministic resolution for local testing and offline execution.
    Matches are explicitly marked with OFFLINE_CURATED provenance.
    """

    @property
    def provider_name(self) -> str:
        return "curated-gazetteer"

    async def geocode(self, query: str) -> Optional[GeocodingResult]:
        normalized = _normalize_key(query)

        # 1. Exact lookup
        if normalized in CURATED_NCR_LOCATIONS:
            lat, lng, display, res_type = CURATED_NCR_LOCATIONS[normalized]
            return GeocodingResult(
                query=query,
                lat=lat,
                lng=lng,
                display_name=display,
                provider=self.provider_name,
                result_type=res_type,
                confidence=0.95,
                is_exact=(res_type in (GeocodingResultType.EXACT_LANDMARK, GeocodingResultType.SECTOR_NEIGHBORHOOD, GeocodingResultType.STREET)),
                timestamp=datetime.now(timezone.utc),
                provenance=GeocodingProvenance.OFFLINE_CURATED,
                raw_metadata={"curated_key": normalized},
            )

        # 2. Substring / Token matching for common aliases
        for key, (lat, lng, display, res_type) in CURATED_NCR_LOCATIONS.items():
            # If the user query exactly contains the curated key as a phrase or vice versa
            if key in normalized or normalized in key:
                # Require substantial match to avoid false positive short substrings
                if len(key) >= 4 and (key in normalized.split() or len(normalized) <= len(key) + 6):
                    return GeocodingResult(
                        query=query,
                        lat=lat,
                        lng=lng,
                        display_name=display,
                        provider=self.provider_name,
                        result_type=res_type,
                        confidence=0.90,
                        is_exact=(res_type in (GeocodingResultType.EXACT_LANDMARK, GeocodingResultType.SECTOR_NEIGHBORHOOD)),
                        timestamp=datetime.now(timezone.utc),
                        provenance=GeocodingProvenance.OFFLINE_CURATED,
                        raw_metadata={"curated_match": key},
                    )

        return None
