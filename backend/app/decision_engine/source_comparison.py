from typing import List, Optional, Dict, Tuple
from pydantic import BaseModel
from app.decision_engine.normalized_models import NormalizedWeatherPoint
from enum import Enum
from app.core.config import settings

class AgreementStatus(str, Enum):
    high = "high"
    mild_disagreement = "mild_disagreement"
    significant_disagreement = "significant_disagreement"
    missing_secondary = "missing_secondary"
    missing_primary = "missing_primary"
    both_unavailable = "both_unavailable"

class WeatherConditionCategory(str, Enum):
    clear = "clear"
    cloudy = "cloudy"
    rain = "rain"
    snow = "snow"
    storm = "storm"
    fog = "fog"
    unknown = "unknown"

class SourceComparisonResult(BaseModel):
    primary_timeline: List[NormalizedWeatherPoint]
    secondary_timeline: Optional[List[NormalizedWeatherPoint]] = None
    agreement_status: AgreementStatus
    comparison_factors: List[str] = []
    
def _map_condition_to_category(condition: str) -> WeatherConditionCategory:
    c = condition.lower()
    if "clear" in c or "sunny" in c:
        return WeatherConditionCategory.clear
    if "cloud" in c or "overcast" in c:
        return WeatherConditionCategory.cloudy
    if "thunder" in c or "storm" in c:
        return WeatherConditionCategory.storm
    if "rain" in c or "drizzle" in c or "shower" in c:
        return WeatherConditionCategory.rain
    if "snow" in c or "ice" in c or "sleet" in c:
        return WeatherConditionCategory.snow
    if "fog" in c or "mist" in c or "haze" in c:
        return WeatherConditionCategory.fog
    return WeatherConditionCategory.unknown

def compare_weather_sources(
    primary: Optional[List[NormalizedWeatherPoint]],
    secondary: Optional[List[NormalizedWeatherPoint]]
) -> SourceComparisonResult:
    """
    Compares primary and secondary weather timelines and determines agreement.
    """
    if not primary and not secondary:
        return SourceComparisonResult(primary_timeline=[], agreement_status=AgreementStatus.both_unavailable, comparison_factors=["Both sources unavailable"])
        
    if not primary and secondary:
        return SourceComparisonResult(primary_timeline=secondary, secondary_timeline=secondary, agreement_status=AgreementStatus.missing_primary, comparison_factors=["Primary unavailable, using secondary"])
        
    if primary and not secondary:
        return SourceComparisonResult(primary_timeline=primary, agreement_status=AgreementStatus.missing_secondary, comparison_factors=["Secondary source unavailable"])
        
    # Both available - compare them
    min_len = min(len(primary), len(secondary))
    factors = []
    status = AgreementStatus.high
    
    for i in range(min_len):
        p = primary[i]
        s = secondary[i]
        
        # 1. Semantic Condition Match
        p_cat = _map_condition_to_category(p.condition)
        s_cat = _map_condition_to_category(s.condition)
        
        if p_cat != s_cat:
            # Significant if rain/storm vs clear
            if (p_cat in [WeatherConditionCategory.rain, WeatherConditionCategory.storm] and s_cat in [WeatherConditionCategory.clear, WeatherConditionCategory.cloudy]) or \
               (s_cat in [WeatherConditionCategory.rain, WeatherConditionCategory.storm] and p_cat in [WeatherConditionCategory.clear, WeatherConditionCategory.cloudy]):
                status = AgreementStatus.significant_disagreement
                factors.append(f"Significant condition mismatch at {p.time}: {p.condition} vs {s.condition}")
            else:
                if status == AgreementStatus.high:
                    status = AgreementStatus.mild_disagreement
                
        # 2. Temperature Check
        if abs(p.temperature - s.temperature) > settings.temperature_diff_threshold_c:
            status = AgreementStatus.significant_disagreement
            factors.append(f"Temperature difference > {settings.temperature_diff_threshold_c}C at {p.time}")
            
        # 3. Precipitation Check
        if abs(p.precipitation_mm - s.precipitation_mm) > settings.precipitation_diff_threshold_mm:
            status = AgreementStatus.significant_disagreement
            factors.append(f"Precipitation difference > {settings.precipitation_diff_threshold_mm}mm at {p.time}")
            
        # 4. Wind Check
        if abs(p.wind_speed - s.wind_speed) > settings.wind_diff_threshold_kmh:
            if status == AgreementStatus.high:
                status = AgreementStatus.mild_disagreement
                
    return SourceComparisonResult(
        primary_timeline=primary,
        secondary_timeline=secondary,
        agreement_status=status,
        comparison_factors=factors
    )
