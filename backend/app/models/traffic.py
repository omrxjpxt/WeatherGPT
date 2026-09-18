from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import model_validator

from app.models.base import WeatherBaseModel
from app.models.enums import CongestionLevel, TrafficStatus, TrafficCondition

class TrafficSegment(WeatherBaseModel):
    start_lat: float
    start_lng: float
    end_lat: float
    end_lng: float
    congestion_level: CongestionLevel = CongestionLevel.unknown
    delay_seconds: float = 0.0
    current_speed_kmh: Optional[float] = None
    free_flow_speed_kmh: Optional[float] = None

class TrafficSnapshot(WeatherBaseModel):
    status: TrafficStatus
    condition: TrafficCondition
    congestion_level: CongestionLevel
    delay_seconds: float = 0.0
    static_duration: timedelta
    traffic_aware_duration: timedelta
    current_speed_kmh: Optional[float] = None
    free_flow_speed_kmh: Optional[float] = None
    segments: List[TrafficSegment] = []
    timestamp: datetime
    source_name: str
    provenance: str

    @model_validator(mode="after")
    def validate_provenance_and_durations(self):
        # 1. Prevent contradictory status/provenance combinations
        if self.status == TrafficStatus.live and ("mock" in self.provenance.lower() or "demo" in self.provenance.lower()):
            raise ValueError("Contradictory traffic metadata: status='live' cannot have mock/demo provenance.")
        if self.status == TrafficStatus.mock and "live" in self.provenance.lower():
            raise ValueError("Contradictory traffic metadata: status='mock' cannot have live provenance.")
        
        # 2. Enforce trafficAwareDuration = staticDuration + trafficDelay
        expected_aware = self.static_duration + timedelta(seconds=max(0.0, self.delay_seconds))
        # Allow slight float precision difference up to 1 second if explicitly provided
        diff = abs((self.traffic_aware_duration - expected_aware).total_seconds())
        if diff > 1.0:
            self.traffic_aware_duration = expected_aware
            
        return self
