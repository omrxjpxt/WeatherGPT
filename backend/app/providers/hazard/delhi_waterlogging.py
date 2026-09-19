import json
import logging
from pathlib import Path
from typing import List, Optional

from app.repositories.hazard_repository import HazardRepository
from app.decision_engine.normalized_models import NormalizedHazard
from app.models.enums import HazardType, HazardSourceClass

logger = logging.getLogger(__name__)

# Default path to the curated hotspots JSON asset
DEFAULT_DATASET_PATH = Path(__file__).parent.parent.parent / "data" / "delhi_waterlogging_hotspots.json"

class DelhiWaterloggingHazardRepository(HazardRepository):
    """
    Authoritative Curated Hazard Repository for Delhi-NCR Waterlogging & Flood Vulnerability.

    ===========================================================================
    DATA PROVENANCE & ARCHITECTURAL SEPARATION:
    ===========================================================================
    A. VERIFIED PUBLIC-SOURCE FACTS:
       - Hotspot names, geographic coordinates, and underpass status sourced directly
         from official Delhi Public Works Department (PWD) Annual Monsoon Preparedness
         Action Plans and Delhi Traffic Police Priority Inundation Bulletins.
       - Chronic underpasses: Minto Bridge, Zakhira, Pul Prahlad Pur, Moolchand,
         Dwarka, Ram Bagh, Okhla, Sarita Vihar, Pandav Nagar.
       - Primary arterial corridors: ITO, Pragati Maidan tunnel, Mathura Road,
         Punjabi Bagh, Mehrauli-Badarpur Road, MG Road, IFFCO Chowk, Noida Sec 62.

    B. WEATHER / RISK MODELING ASSUMPTIONS:
       - 15.0 mm/hr rainfall activation threshold for chronic underpasses (represents
         rainfall intensity where subterranean sump and dewatering pumps exceed capacity).
       - 35.0 mm/hr rainfall activation threshold for surface arterial corridors.
       * Note: These are hydrologic modeling assumptions, NOT government decrees.

    C. OPERATIONAL WATER-DEPTH ASSUMPTIONS:
       - ~15 cm water depth: Traffic diversion / high risk of loss of traction for
         pedestrians and two-wheelers (bicycles, motorcycles).
       - ~30 cm water depth: Engine hydro-lock / stalling threshold for private cars.
       - TransportMode.metro: Elevated or subterranean tracks completely unaffected
         by street-level waterlogging.
    ===========================================================================
    """

    def __init__(self, dataset_path: Optional[Path] = None):
        self.dataset_path = dataset_path or DEFAULT_DATASET_PATH
        self.metadata = {}
        self.hazards: List[NormalizedHazard] = []
        self._load_dataset()

    def _load_dataset(self) -> None:
        """Loads curated hotspots from JSON asset into in-memory spatial index."""
        if not self.dataset_path.exists():
            logger.warning(f"Delhi waterlogging dataset not found at {self.dataset_path}. Falling back to baseline hotspots.")
            self._load_fallback_baseline()
            return

        try:
            with open(self.dataset_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.metadata = data.get("metadata", {})
            hotspots_raw = data.get("hotspots", [])
            loaded_hazards: List[NormalizedHazard] = []

            for h in hotspots_raw:
                loaded_hazards.append(
                    NormalizedHazard(
                        id=h.get("id"),
                        type=HazardType.waterlogging,
                        lat=float(h.get("lat")),
                        lng=float(h.get("lng")),
                        radius_meters=float(h.get("radius_meters", 350.0)),
                        base_severity=int(h.get("base_severity", 80)),
                        source_name="Delhi PWD / Traffic Police Priority Monsoon List",
                        source_class=HazardSourceClass.government_open_data,
                        source_url="https://pwd.delhi.gov.in/",
                        source_reference=h.get("jurisdiction", "Delhi PWD"),
                        trigger_precipitation_mm=float(h.get("rainfall_trigger_mm", 35.0)),
                        is_underpass=bool(h.get("is_underpass", False)),
                        water_depth_threshold_cm=float(h.get("water_depth_cm", 15.0)),
                        impassable_modes=h.get("impassable_modes", ["walk", "bike"]),
                        chronic=True,
                        location_name=h.get("name")
                    )
                )

            self.hazards = loaded_hazards
            logger.info(f"Loaded {len(self.hazards)} verified Delhi-NCR waterlogging hazards into memory.")
        except Exception as e:
            logger.error(f"Failed to load Delhi waterlogging dataset from {self.dataset_path}: {e}. Using fallback baseline.")
            self._load_fallback_baseline()

    def _load_fallback_baseline(self) -> None:
        """Fallback to core verified underpasses if JSON file cannot be read."""
        self.hazards = [
            NormalizedHazard(
                id="pwd-minto-bridge-underpass",
                type=HazardType.waterlogging,
                lat=28.6327,
                lng=77.2220,
                radius_meters=250.0,
                base_severity=95,
                source_name="Delhi PWD / Traffic Police Priority Monsoon List",
                source_class=HazardSourceClass.government_open_data,
                trigger_precipitation_mm=15.0,
                is_underpass=True,
                water_depth_threshold_cm=20.0,
                impassable_modes=["walk", "bike", "car"],
                chronic=True,
                location_name="Minto Bridge Underpass"
            ),
            NormalizedHazard(
                id="pwd-zakhira-underpass",
                type=HazardType.waterlogging,
                lat=28.6678,
                lng=77.1534,
                radius_meters=300.0,
                base_severity=90,
                source_name="Delhi PWD / Traffic Police Priority Monsoon List",
                source_class=HazardSourceClass.government_open_data,
                trigger_precipitation_mm=15.0,
                is_underpass=True,
                water_depth_threshold_cm=18.0,
                impassable_modes=["walk", "bike", "car"],
                chronic=True,
                location_name="Zakhira Underpass (Rohtak Road)"
            ),
            NormalizedHazard(
                id="pwd-pul-prahladpur-underpass",
                type=HazardType.waterlogging,
                lat=28.5032,
                lng=77.2882,
                radius_meters=350.0,
                base_severity=95,
                source_name="Delhi PWD / Traffic Police Priority Monsoon List",
                source_class=HazardSourceClass.government_open_data,
                trigger_precipitation_mm=15.0,
                is_underpass=True,
                water_depth_threshold_cm=25.0,
                impassable_modes=["walk", "bike", "car"],
                chronic=True,
                location_name="Pul Prahlad Pur Underpass (MB Road)"
            )
        ]

    async def get_hazards_in_region(
        self, min_lat: float, min_lng: float, max_lat: float, max_lng: float
    ) -> List[NormalizedHazard]:
        """
        Filters hazards within a geographical bounding box.
        Operates entirely in-memory with zero network overhead.
        """
        matching: List[NormalizedHazard] = []
        for h in self.hazards:
            if min_lat <= h.lat <= max_lat and min_lng <= h.lng <= max_lng:
                matching.append(h)
        return matching

    def get_all_hazards(self) -> List[NormalizedHazard]:
        return list(self.hazards)
