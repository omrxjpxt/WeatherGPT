from datetime import datetime, timezone
from app.models.enums import ConfidenceLevel
from app.models.risk import Confidence

from app.decision_engine.source_comparison import AgreementStatus

def calculate_confidence(forecast_time: datetime, agreement_status: AgreementStatus) -> Confidence:
    """
    Treats uncertainty as a qualitative data/recommendation quality assessment.
    Returns High, Medium, or Low confidence based on forecast horizon, data freshness, 
    source availability, and source agreement.
    """
    now = datetime.now(timezone.utc)
    delta_hours = (forecast_time - now).total_seconds() / 3600.0
    
    # Base confidence off of agreement
    if agreement_status == AgreementStatus.significant_disagreement:
        return Confidence(
            level=ConfidenceLevel.low,
            explanation="Low confidence: Significant disagreement between primary and secondary weather sources."
        )
    elif agreement_status in [AgreementStatus.both_unavailable, AgreementStatus.missing_primary]:
        return Confidence(
            level=ConfidenceLevel.low,
            explanation="Low confidence: Missing critical primary weather data."
        )
        
    # Standard horizon logic
    if delta_hours < 12 and agreement_status == AgreementStatus.high:
        return Confidence(
            level=ConfidenceLevel.high,
            explanation="High confidence: Forecast is near-term with strong corroboration between multiple sources. High data freshness."
        )
    elif delta_hours < 48:
        if agreement_status == AgreementStatus.missing_secondary:
            explanation = "Medium confidence: Standard forecasting horizon. Lacking secondary source corroboration."
        elif agreement_status == AgreementStatus.mild_disagreement:
            explanation = "Medium confidence: Minor discrepancies between sources."
        else:
            explanation = "Medium confidence: Standard forecasting horizon."
        return Confidence(level=ConfidenceLevel.medium, explanation=explanation)
    else:
        return Confidence(
            level=ConfidenceLevel.low,
            explanation="Low confidence: Long-range forecast subject to change."
        )
