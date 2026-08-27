from typing import List
from app.repositories.hazard_repository import HazardRepository
from app.decision_engine.normalized_models import NormalizedHazard
from app.models.enums import HazardType, HazardSourceClass

class MockHazardRepository(HazardRepository):
    def __init__(self):
        self.hazards = [
            NormalizedHazard(
                id="minto-bridge-delhi",
                type=HazardType.waterlogging,
                lat=28.6327,
                lng=77.2220,
                radius_meters=300.0,
                base_severity=90,
                source_name="Delhi MCD Historical List",
                source_class=HazardSourceClass.government_open_data,
                trigger_precipitation_mm=5.0,
            ),
            NormalizedHazard(
                id="hindmata-mumbai",
                type=HazardType.waterlogging,
                lat=19.0163,
                lng=72.8436,
                radius_meters=400.0,
                base_severity=100,
                source_name="Mumbai BMC Hotspots",
                source_class=HazardSourceClass.government_open_data,
                trigger_precipitation_mm=10.0,
            ),
            NormalizedHazard(
                id="demo-landslide",
                type=HazardType.waterlogging, # No landslide enum yet, using waterlogging for demo
                lat=28.6,
                lng=77.3,
                radius_meters=1000.0,
                base_severity=70,
                source_name="Demo Generator",
                source_class=HazardSourceClass.demo,
                trigger_condition="Heavy Rain",
            )
        ]
        
    async def get_hazards_in_region(self, min_lat: float, min_lng: float, max_lat: float, max_lng: float) -> List[NormalizedHazard]:
        # Simple bounding box filter
        result = []
        for h in self.hazards:
            if min_lat <= h.lat <= max_lat and min_lng <= h.lng <= max_lng:
                result.append(h)
        return result
