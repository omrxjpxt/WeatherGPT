from datetime import datetime, timezone
from app.models.enums import ConfidenceLevel
from app.models.risk import Confidence

def calculate_confidence(forecast_time: datetime, data_sources_count: int) -> Confidence:
    """
    Treats uncertainty as a qualitative data/recommendation quality assessment.
    Returns High, Medium, or Low confidence.
    """
    now = datetime.now(timezone.utc)
    delta_hours = (forecast_time - now).total_seconds() / 3600.0
    
    # Qualitative logic:
    # 1. Forecast horizon (near-term vs long-range)
    # 2. Source corroboration (multiple sources vs single source)
    
    if delta_hours < 12 and data_sources_count >= 2:
        return Confidence(
            level=ConfidenceLevel.high,
            explanation="High confidence: Forecast is near-term with multiple corroborating data sources. High data freshness."
        )
    elif delta_hours < 48:
        return Confidence(
            level=ConfidenceLevel.medium,
            explanation="Medium confidence: Standard forecasting horizon. Missing some multi-source corroboration."
        )
    else:
        return Confidence(
            level=ConfidenceLevel.low,
            explanation="Low confidence: Long-range forecast subject to change. Limited data freshness."
        )
