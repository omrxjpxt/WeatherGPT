from typing import List, Optional
from datetime import datetime
from app.decision_engine.models import EngineDecisionResult

# Engineering assumptions for MVP
UNACCEPTABLE_RISK_THRESHOLD = 75 # Severe

def _is_feasible(scenario: EngineDecisionResult, deadline: Optional[datetime], departure_time: datetime) -> bool:
    if scenario.overall_risk.overall_score >= UNACCEPTABLE_RISK_THRESHOLD:
        return False
        
    if deadline:
        arrival_time = departure_time + scenario.total_duration
        if arrival_time > deadline:
            return False
            
    return True

def get_best_alternative(
    current_scenario: EngineDecisionResult,
    candidates: List[tuple[datetime, EngineDecisionResult]],
    deadline: Optional[datetime],
    current_departure: datetime
) -> Optional[datetime]:
    """
    Finds the strictly better feasible departure time from candidates.
    candidates is a list of (departure_time, evaluation_result)
    """
    # 1 & 2. Filter unacceptable and infeasible
    feasible_candidates = [
        (t, res) for t, res in candidates 
        if _is_feasible(res, deadline, t)
    ]
    
    current_is_feasible = _is_feasible(current_scenario, deadline, current_departure)
    
    if not feasible_candidates:
        return None
        
    # 3. Utility ranking (lower score = better)
    def utility_score(res: EngineDecisionResult):
        # Primary: risk level
        # Secondary: exact risk score
        # Tertiary: duration
        return (res.overall_risk.overall_score, res.total_duration.total_seconds())
        
    feasible_candidates.sort(key=lambda x: utility_score(x[1]))
    
    best_candidate_time, best_candidate_res = feasible_candidates[0]
    
    # Must be strictly better than current if current is feasible
    if current_is_feasible:
        if utility_score(best_candidate_res) >= utility_score(current_scenario):
            return None
            
    return best_candidate_time

def rank_scenarios(scenarios: List[tuple[EngineDecisionResult, datetime, Optional[datetime]]]) -> List[EngineDecisionResult]:
    """
    Rank multiple scenarios based on explicit policy.
    scenarios: List of (result, departure_time, deadline)
    """
    feasible = []
    unfeasible = []
    
    for res, t, deadline in scenarios:
        if _is_feasible(res, deadline, t):
            feasible.append(res)
        else:
            unfeasible.append(res)
            
    def utility_score(res: EngineDecisionResult):
        return (res.overall_risk.overall_score, res.total_duration.total_seconds())
        
    feasible.sort(key=utility_score)
    unfeasible.sort(key=utility_score)
    
    return feasible + unfeasible
