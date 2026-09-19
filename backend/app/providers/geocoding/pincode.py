import re
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import httpx

from app.providers.geocoding.base import (
    GeocodingProvider,
    GeocodingResult,
    GeocodingResultType,
    GeocodingProvenance,
)

logger = logging.getLogger(__name__)

DEFAULT_PINCODE_DATASET = Path(__file__).parent.parent.parent / "data" / "ncr_pincodes.json"
PINCODE_REGEX = re.compile(r"\b(\d{6})\b")

class NcrPincodeGeocodingProvider(GeocodingProvider):
    """
    Geocoding Provider for 6-digit Indian Postal PIN Codes.

    ===========================================================================
    DATA PROVENANCE & ARCHITECTURAL SPECIFICATION:
    ===========================================================================
    - Authority: Survey of India & India Post All-India Pincode Directory (data.gov.in)
      with dynamic fallback to api.postalpincode.in for out-of-NCR PINs.
    - Scope: Instant offline resolution for core Delhi-NCR commuter delivery zones
      (Delhi 110xxx, Noida/Gr. Noida 2013xx, Gurgaon 122xxx, Ghaziabad 2010xx, Faridabad 121xxx).
    - Accuracy Guarantee: A PIN code represents an area delivery centroid, NOT an
      exact rooftop building. Therefore, is_exact is strictly False, result_type is
      'locality', and confidence is capped at 0.90 to preserve semantic precision.
    ===========================================================================
    """

    def __init__(self, dataset_path: Optional[Path] = None, enable_live_fallback: bool = True):
        self.dataset_path = dataset_path or DEFAULT_PINCODE_DATASET
        self.enable_live_fallback = enable_live_fallback
        self.pincodes: Dict[str, Dict[str, Any]] = {}
        self._load_dataset()

    @property
    def provider_name(self) -> str:
        return "NCR Postal PIN Directory (India Post / Survey of India)"

    def _load_dataset(self) -> None:
        if not self.dataset_path.exists():
            logger.warning(f"NCR PIN code dataset not found at {self.dataset_path}. In-memory PIN resolution disabled.")
            return

        try:
            with open(self.dataset_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.pincodes = data.get("pincodes", {})
            logger.info(f"Loaded {len(self.pincodes)} Delhi-NCR PIN codes into memory.")
        except Exception as e:
            logger.error(f"Failed to load NCR PIN codes from {self.dataset_path}: {e}")

    async def geocode(self, query: str) -> Optional[GeocodingResult]:
        if not query or not query.strip():
            return None

        # Detect 6-digit PIN code in query
        match = PINCODE_REGEX.search(query.strip())
        if not match:
            return None

        pin = match.group(1)

        # Architectural Guard: Do not let a low-confidence PIN centroid override a
        # higher-confidence exact street/rooftop address result.
        tokens = query.strip().split()
        lower_q = query.lower()
        street_markers = ["road", "rd", "street", "st", "lane", "house", "flat", "plot", "floor", "tower", "building", "marg", "gali"]
        if any(marker in lower_q for marker in street_markers) and len(tokens) > 3:
            # Let downstream exact geocoders resolve street-level coordinates
            return None

        # 1. Fast-path: Check curated NCR postal dataset
        if pin in self.pincodes:
            entry = self.pincodes[pin]
            return GeocodingResult(
                query=query,
                lat=float(entry["lat"]),
                lng=float(entry["lng"]),
                display_name=f"{entry['name']}, {entry['district']}, {entry['state']} ({pin})",
                provider=self.provider_name,
                result_type=GeocodingResultType.POSTAL_CODE,
                confidence=0.90, # Postal delivery centroid confidence
                is_exact=False,  # PIN code is an area centroid, NOT rooftop
                timestamp=datetime.now(timezone.utc),
                provenance=GeocodingProvenance.OFFLINE_CURATED,
            )

        # 2. Out-of-NCR fallback: Query api.postalpincode.in if enabled
        if self.enable_live_fallback:
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    resp = await client.get(f"https://api.postalpincode.in/pincode/{pin}")
                    if resp.status_code == 200:
                        data = resp.json()
                        if isinstance(data, list) and data and data[0].get("Status") == "Success":
                            post_offices = data[0].get("PostOffice", [])
                            if post_offices:
                                po = post_offices[0]
                                po_name = po.get("Name", "")
                                district = po.get("District", "")
                                state = po.get("State", "")
                                display_name = f"{po_name}, {district}, {state} ({pin})"

                                # Note: postalpincode.in does not always return lat/lng directly.
                                # If coordinates are missing, return None to let downstream geocoders resolve.
                                lat = po.get("Latitude")
                                lng = po.get("Longitude")
                                if lat and lng:
                                    return GeocodingResult(
                                        query=query,
                                        lat=float(lat),
                                        lng=float(lng),
                                        display_name=display_name,
                                        provider="India Post API (postalpincode.in)",
                                        result_type=GeocodingResultType.POSTAL_CODE,
                                        confidence=0.85,
                                        is_exact=False,
                                        timestamp=datetime.now(timezone.utc),
                                        provenance=GeocodingProvenance.LIVE_PROVIDER,
                                    )
            except Exception as e:
                logger.debug(f"Live postal PIN code fallback failed for {pin}: {e}")

        # If not resolved, return None to allow the rest of the fallback chain to resolve
        return None
