from typing import List, Tuple
from datetime import datetime

from app.models.enums import RiskLevel, TransportMode
from app.decision_engine.normalized_models import NormalizedRouteSegment, NormalizedWeatherPoint, NormalizedHazard
from app.decision_engine.exposure import get_mode_exposure_multiplier
from app.models.risk import RiskFactor

def calculate_segment_risk(
    segment: NormalizedRouteSegment,
    weather: NormalizedWeatherPoint,
    hazards: List[NormalizedHazard],
    mode: TransportMode
) -> Tuple[int, RiskLevel, List[RiskFactor], str]:
    """
    Calculates risk for a specific segment.
    Explicitly separates:
    - user exposure (mode_multiplier)
    - temporal exposure (duration)
    - route exposure (hazards on segment)
    - hazard severity (weather conditions)
    """
    factors = []
    
    # 1. User Exposure (Mode)
    mode_multiplier = get_mode_exposure_multiplier(mode)
    
    # 2. Temporal Exposure (Duration relative to a base of 10 mins)
    duration_mins = segment.estimated_duration.total_seconds() / 60.0
    temporal_multiplier = min(2.0, max(0.5, duration_mins / 10.0))
    
    # 3. Hazard Severity (Weather)
    # Precipitation risk (0-100)
    precip_score = min(100.0, weather.precipitation * 3.0) 
    if precip_score > 10:
        factors.append(RiskFactor(
            name="Precipitation",
            description=f"Rainfall of {weather.precipitation} mm/hr expected.",
            score=int(precip_score),
            level=_score_to_level(int(precip_score)),
            weight=0.4
        ))
        
    # Visibility risk
    if weather.is_poor_visibility:
        factors.append(RiskFactor(
            name="Visibility",
            description="Poor visibility conditions.",
            score=60,
            level=RiskLevel.moderate,
            weight=0.2
        ))
        
    # 4. Route Exposure (Hazards intersecting this segment)
    # Mock simple spatial intersection (using bounding box of segment start/end)
    segment_hazards_score = 0
    for h in hazards:
        lat_min, lat_max = min(segment.start_lat, segment.end_lat), max(segment.start_lat, segment.end_lat)
        lng_min, lng_max = min(segment.start_lng, segment.end_lng), max(segment.start_lng, segment.end_lng)
        # Expand bbox slightly for matching
        if (lat_min - 0.05) <= h.lat <= (lat_max + 0.05) and (lng_min - 0.05) <= h.lng <= (lng_max + 0.05):
            segment_hazards_score = max(segment_hazards_score, h.severity_score)
            factors.append(RiskFactor(
                name="Local Hazard",
                description=f"Route intersects hazard: {h.type.value}",
                score=h.severity_score,
                level=_score_to_level(h.severity_score),
                weight=0.3
            ))

    # Combine
    base_environmental_risk = (precip_score * 0.4) + (60 if weather.is_poor_visibility else 0) * 0.2 + (segment_hazards_score * 0.3)
    
    # Apply exposure multipliers
    final_score = int(base_environmental_risk * mode_multiplier * temporal_multiplier)
    final_score = min(100, max(0, final_score))
    
    level = _score_to_level(final_score)
    reason = "Safe" if level == RiskLevel.low else "Elevated risk due to environmental factors."
    
    return final_score, level, factors, reason

def _score_to_level(score: int) -> RiskLevel:
    if score >= 75: return RiskLevel.severe
    if score >= 50: return RiskLevel.high
    if score >= 25: return RiskLevel.moderate
    return RiskLevel.low
