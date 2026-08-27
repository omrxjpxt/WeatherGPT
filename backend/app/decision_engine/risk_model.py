from typing import List, Tuple
from datetime import datetime

from app.models.enums import RiskLevel, TransportMode
from app.decision_engine.normalized_models import NormalizedRouteSegment, NormalizedWeatherPoint, NormalizedHazard
from app.decision_engine.exposure import get_mode_exposure_multiplier
from app.models.risk import RiskFactor
from app.decision_engine.spatial import point_to_segment_distance_km

# Engineering assumption for MVP: Hazard affects segment if within this radius
HAZARD_PROXIMITY_RADIUS_KM = 2.0

def _calculate_precipitation_score(weather: NormalizedWeatherPoint) -> int:
    """
    Isolated precipitation scoring function.
    
    ENGINEERING ASSUMPTION (MVP):
    Precipitation risk is scored as a linear scalar of hourly accumulation (mm).
    This assumes `precipitation_mm` acts as a proxy for intensity over the hour.
    """
    return min(100, int(weather.precipitation_mm * 3.0))

from app.decision_engine.normalized_models import NormalizedRouteSegment, NormalizedWeatherPoint, NormalizedHazard, HazardRelevanceResult

def calculate_segment_risk(
    segment: NormalizedRouteSegment,
    weather: NormalizedWeatherPoint,
    hazards: List[NormalizedHazard],
    mode: TransportMode
) -> Tuple[int, RiskLevel, List[RiskFactor], str, List[HazardRelevanceResult]]:
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
    precip_score = _calculate_precipitation_score(weather)
    
    if precip_score > 0:
        factors.append(RiskFactor(
            name="Precipitation",
            description=f"Rainfall of {weather.precipitation_mm} mm expected in this hour.",
            score=precip_score,
            level=_score_to_level(precip_score),
            weight=0.4
        ))
        
    vis_score = 0
    if weather.is_poor_visibility or weather.visibility < 1000.0:
        vis_score = 60
        factors.append(RiskFactor(
            name="Visibility",
            description=f"Poor visibility expected ({weather.visibility} m).",
            score=vis_score,
            level=RiskLevel.moderate,
            weight=0.2
        ))
        
    # 4. Route Exposure (Hazards intersecting this segment)
    segment_hazards_score = 0
    relevance_results = []
    
    for h in hazards:
        # Spatial match using existing Haversine point-to-segment distance
        dist_km = point_to_segment_distance_km(
            h.lat, h.lng,
            segment.start_lat, segment.start_lng,
            segment.end_lat, segment.end_lng
        )
        
        spatially_relevant = dist_km <= (h.radius_meters / 1000.0)
        weather_triggered = False
        currently_relevant = False
        hazard_contribution = 0
        relevance_reason = None
        
        if spatially_relevant:
            # Weather trigger
            if h.trigger_precipitation_mm is not None and weather.precipitation_mm >= h.trigger_precipitation_mm:
                weather_triggered = True
            elif h.trigger_condition is not None and h.trigger_condition.lower() in weather.condition.lower():
                weather_triggered = True
                
            if weather_triggered:
                # Temporal overlap is implicitly true because we're evaluating the weather AT the passage time
                currently_relevant = True
                from app.core.config import settings
                hazard_contribution = int(h.base_severity * settings.hazard_influence_factor)
                segment_hazards_score = max(segment_hazards_score, hazard_contribution)
                relevance_reason = f"Route near active {h.type.value} hotspot ({h.source_name}). Triggered by {weather.condition}."
                factors.append(RiskFactor(
                    name="Historical Hazard Risk",
                    description=relevance_reason,
                    score=hazard_contribution,
                    level=_score_to_level(hazard_contribution),
                    weight=0.3
                ))
            else:
                relevance_reason = "Near route, but weather triggers not met."
        
        relevance_results.append(HazardRelevanceResult(
            hazard_id=h.id,
            spatially_relevant=spatially_relevant,
            weather_triggered=weather_triggered,
            temporally_relevant=currently_relevant, # Temporal implies current passage overlap
            currently_relevant=currently_relevant,
            relevance_reason=relevance_reason,
            contribution_score=hazard_contribution
        ))

    # Combine
    base_environmental_risk = (precip_score * 0.4) + (60 if weather.is_poor_visibility else 0) * 0.2 + (segment_hazards_score * 0.3)
    
    # Apply exposure multipliers
    final_score = int(base_environmental_risk * mode_multiplier * temporal_multiplier)
    final_score = min(100, max(0, final_score))
    
    level = _score_to_level(final_score)
    reason = "Safe" if level == RiskLevel.low else "Elevated risk due to environmental factors."
    
    return final_score, level, factors, reason, relevance_results

def _score_to_level(score: int) -> RiskLevel:
    if score >= 75: return RiskLevel.severe
    if score >= 50: return RiskLevel.high
    if score >= 25: return RiskLevel.moderate
    return RiskLevel.low
