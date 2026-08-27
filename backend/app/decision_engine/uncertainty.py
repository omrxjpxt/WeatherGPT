from datetime import datetime, timezone
from app.models.enums import ConfidenceLevel
from app.models.risk import Confidence

def calculate_confidence(forecast_time: datetime, data_sources_count: int) -> Confidence:
    """
    Treats uncertainty as a data/recommendation quality assessment.
    Returns High, Moderate, or Low confidence.
    """
    now = datetime.now(timezone.utc)
    delta_hours = (forecast_time - now).total_seconds() / 3600.0
    
    # Simple logic: further in future = lower confidence. More sources = higher.
    # In mock, we assume high confidence for near-term.
    if delta_hours < 12 and data_sources_count >= 2:
        return Confidence(
            level=ConfidenceLevel.high,
            percentage=85,
            explanation="High confidence: Forecast is near-term with multiple corroborating data sources."
        )
    elif delta_hours < 48:
        return Confidence(
            level=ConfidenceLevel.medium,
            percentage=60,
            explanation="Moderate confidence: Standard forecasting horizon."
        )
    else:
        return Confidence(
            level=ConfidenceLevel.low,
            percentage=35,
            explanation="Low confidence: Long-range forecast subject to change."
        )
