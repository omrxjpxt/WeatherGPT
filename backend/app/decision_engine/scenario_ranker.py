from typing import List
from app.decision_engine.models import EngineDecisionResult

def rank_scenarios(scenarios: List[EngineDecisionResult]) -> List[EngineDecisionResult]:
    """
    Rank multiple scenario results based on risk, travel time, and exposure.
    Lowest risk is preferred. If risk is equal, lowest duration is preferred.
    """
    return sorted(scenarios, key=lambda s: (s.overall_risk.overall_score, s.total_duration.total_seconds()))
