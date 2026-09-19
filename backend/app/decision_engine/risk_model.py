from typing import List, Tuple, Optional, Any
from datetime import datetime

from app.models.enums import RiskLevel, TransportMode, HazardType
from app.decision_engine.normalized_models import NormalizedRouteSegment, NormalizedWeatherPoint, NormalizedHazard, HazardRelevanceResult
from app.decision_engine.exposure import get_mode_exposure_multiplier
from app.models.risk import RiskFactor
from app.decision_engine.spatial import point_to_segment_distance_km

# Engineering assumption for MVP: Hazard affects segment if within this radius
HAZARD_PROXIMITY_RADIUS_KM = 2.0


def _calculate_precipitation_score(weather: NormalizedWeatherPoint) -> int:
    """
    Isolated precipitation scoring function with deterministic probability weighting.
    
    ENGINEERING ASSUMPTION (Phase 20):
    Precipitation risk is scaled by precipitation_probability (0-100%) when present.
    If precipitation_probability is < 20%, precipitation risk is bounded to <= 10
    to avoid false alarms for passing drizzles.
    If probability is missing/None, falls back to legacy linear scalar of accumulation.
    """
    if weather.precipitation_probability is None:
        return min(100, int(weather.precipitation_mm * 3.0))

    prob_factor = max(0.20, weather.precipitation_probability / 100.0)
    effective_mm = weather.precipitation_mm * prob_factor
    raw_score = min(100, int(effective_mm * 3.0))

    if weather.precipitation_probability < 20.0:
        return min(10, raw_score)
    return raw_score


def calculate_aqi_risk_score(
    aqi: int,
    pm2_5: float,
    mode: TransportMode,
) -> Tuple[int, Optional[RiskFactor]]:
    """
    Calculates deterministic, bounded Air Quality risk contribution.
    - US EPA Breakpoint harmonization with PM2.5 precedence
    - Mode exposure multipliers:
      - walk: 1.0
      - bicycle / bike: 1.0
      - car: 0.15
      - metro: 0.10
    - Base score mapping:
      - <= 100: 0 (Good / Moderate)
      - 101-150: 25 (Low)
      - 151-200: 45 (Moderate)
      - 201-300: 70 (Moderate)
      - 301-400: 85 (High)
      - > 400: 100 (Critical)
    """
    from app.providers.air_quality.base import calculate_us_aqi_from_pm25, classify_aqi_category

    # PM2.5 precedence harmonization
    pm25_aqi = calculate_us_aqi_from_pm25(pm2_5) if pm2_5 > 0 else 0
    effective_aqi = max(aqi, pm25_aqi)

    if effective_aqi <= 100:
        s_raw = 0
    elif effective_aqi <= 150:
        s_raw = 25
    elif effective_aqi <= 200:
        s_raw = 45
    elif effective_aqi <= 300:
        s_raw = 70
    elif effective_aqi <= 400:
        s_raw = 85
    else:
        s_raw = 100

    # Transport Mode Exposure Multipliers
    if mode in (TransportMode.bike, TransportMode.walk):
        m_mode = 1.0
    elif mode == TransportMode.car:
        m_mode = 0.15
    elif mode == TransportMode.metro:
        m_mode = 0.10
    else:
        m_mode = 1.0

    final_aqi_score = min(100, int(round(s_raw * m_mode)))

    if final_aqi_score < 20:
        return 0, None

    category = classify_aqi_category(effective_aqi)
    level = _score_to_level(final_aqi_score)
    advice = (
        "N95 mask advised for two-wheelers and pedestrians."
        if mode in (TransportMode.bike, TransportMode.walk)
        else "Cabin air filtration recommended."
    )
    desc = f"{category} air quality (AQI {effective_aqi}, PM2.5: {pm2_5:.1f} µg/m³). {advice}"

    factor = RiskFactor(
        name="Air Quality",
        description=desc,
        score=final_aqi_score,
        level=level,
        weight=0.15,
    )
    return final_aqi_score, factor


def calculate_segment_risk(
    segment: NormalizedRouteSegment,
    weather: NormalizedWeatherPoint,
    hazards: List[NormalizedHazard],
    mode: TransportMode,
    traffic_delay_seconds: float = 0.0,
    air_quality: Optional[Any] = None,
) -> Tuple[int, RiskLevel, List[RiskFactor], str, List[HazardRelevanceResult]]:
    """
    Calculates risk for a specific segment.
    Explicitly separates:
    - user exposure (mode_multiplier)
    - temporal exposure (duration, including traffic delay)
    - route exposure (hazards on segment)
    - hazard severity (weather conditions, air quality)
    """
    factors = []
    
    # 1. User Exposure (Mode)
    mode_multiplier = get_mode_exposure_multiplier(mode)
    
    # 2. Temporal Exposure (Duration relative to a base of 10 mins, accounting for traffic delay)
    effective_duration_seconds = segment.estimated_duration.total_seconds() + max(0.0, traffic_delay_seconds)
    duration_mins = effective_duration_seconds / 60.0
    temporal_multiplier = min(2.0, max(0.5, duration_mins / 10.0))
    
    # 3. Hazard Severity (Weather)
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

    # 4. Air Quality Evaluation (Deterministic & Bounded)
    aqi_score = 0
    if air_quality:
        aqi_val = air_quality.get("aqi", 0) if isinstance(air_quality, dict) else getattr(air_quality, "aqi", 0)
        pm25_val = air_quality.get("pm2_5", 0.0) if isinstance(air_quality, dict) else getattr(air_quality, "pm2_5", 0.0)
        aqi_score, aqi_factor = calculate_aqi_risk_score(aqi_val, pm25_val, mode)
        if aqi_factor:
            factors.append(aqi_factor)
        
    # 5. Route Exposure (Hazards intersecting this segment)
    segment_hazards_score = 0
    relevance_results = []
    
    for h in hazards:
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
            if h.trigger_precipitation_mm is not None and weather.precipitation_mm >= h.trigger_precipitation_mm:
                weather_triggered = True
            elif h.trigger_condition is not None and h.trigger_condition.lower() in weather.condition.lower():
                weather_triggered = True
                
            if weather_triggered:
                if mode == TransportMode.metro and h.type == HazardType.waterlogging:
                    currently_relevant = False
                    hazard_contribution = 0
                    relevance_reason = "Metro transit network is unaffected by street-surface waterlogging."
                else:
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
            temporally_relevant=currently_relevant,
            currently_relevant=currently_relevant,
            relevance_reason=relevance_reason,
            contribution_score=hazard_contribution
        ))

    # Combine: precipitation (0.40) + visibility (0.20) + hazards (0.30) + aqi (0.15)
    base_environmental_risk = (
        (precip_score * 0.4)
        + ((60 if weather.is_poor_visibility else 0) * 0.2)
        + (segment_hazards_score * 0.3)
        + (aqi_score * 0.15)
    )
    
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

