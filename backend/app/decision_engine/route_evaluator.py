import functools
from datetime import datetime, timedelta
from typing import List, Tuple, Optional

from app.decision_engine.engine import DecisionEngine
from app.decision_engine.models import EngineDecisionResult
from app.decision_engine.normalized_models import (
    TripContext,
    NormalizedRoute,
    NormalizedWeatherPoint,
    NormalizedHazard,
    NormalizedAlert,
)
from app.models.enums import RiskLevel, AlertSeverity
from app.models.route import EvaluatedRoute, RouteEvaluation
from app.models.hazard import Hazard
from app.models.traffic import TrafficSnapshot
from app.models.trip import TripRequest

"""
DETERMINISTIC ROUTE SELECTION POLICY ORDERING:
================================================
1. Feasibility Filtering:
   a. Routes exceeding arrival_deadline (departure_time + traffic_aware_duration > arrival_deadline)
      are marked is_feasible=False with an explicit feasibility_reason.
   b. If at least one route is feasible, infeasible routes are excluded from selection.
   c. If ALL routes violate arrival_deadline, all routes remain in consideration (with is_feasible=False).

2. Hard Alert Avoidance:
   a. Distinguish hard avoidance/closures (active emergency alert or closure/evacuation action)
      vs general advisory/warning alerts.
   b. If some candidate routes are free of hard avoidance alerts and others are affected,
      routes with hard avoidance alerts are excluded from selection.
   c. If ALL routes are affected by hard avoidance alerts, all are retained (regional alert condition).

3. Risk Tier Comparison:
   a. Compare risk levels: Low (1) < Moderate (2) < High (3) < Severe (4).
   b. If risk tiers differ, the route with the lower risk tier is selected.

4. Same Risk Tier & Large Score Difference (>= 15 points):
   a. If routes share the same risk tier and |risk_score_A - risk_score_B| >= 15,
      the route with the strictly lower raw risk score is selected.

5. Same Risk Tier & Small Score Difference (< 15 points):
   a. If routes share the same risk tier and |risk_score_A - risk_score_B| < 15,
      the route with the shorter traffic-aware duration (effective travel time) is selected.

6. Tie-Breaking:
   a. Lower exposure score.
   b. Shorter total distance.
   c. Lexicographical route_id comparison for absolute determinism.
"""

RISK_TIER_ORDER = {
    RiskLevel.low: 1,
    RiskLevel.moderate: 2,
    RiskLevel.high: 3,
    RiskLevel.severe: 4,
    "low": 1,
    "moderate": 2,
    "high": 3,
    "severe": 4,
}

def get_risk_tier(level) -> int:
    val = level.value if hasattr(level, "value") else str(level)
    order = {"low": 1, "moderate": 2, "high": 3, "severe": 4}
    return order.get(val.lower(), 99)

def format_risk_level(level) -> str:
    val = level.value if hasattr(level, "value") else str(level)
    return str(val).capitalize()

def is_hard_alert_avoidance(engine_result: EngineDecisionResult) -> bool:
    """
    Determines if a route is subject to a hard avoidance or closure order.
    Preserves alert policy semantics: advisory alerts inform risk, while emergency/evacuation/closure
    actions represent hard avoidance conditions.
    """
    if not engine_result.alert_override_applied or not engine_result.active_override_alert:
        return False
    
    alert = engine_result.active_override_alert
    if alert.severity == AlertSeverity.emergency:
        return True
    
    # Check for hard avoidance / closure keywords in action text
    if alert.action:
        action_lower = alert.action.lower()
        hard_keywords = ["avoid", "close", "closed", "closure", "evacuate", "halt", "stop", "prohibited", "danger"]
        if any(kw in action_lower for kw in hard_keywords):
            return True
            
    return False

class RouteEvaluator:
    """
    Orchestration layer for evaluating multiple route alternatives.
    Does NOT duplicate DecisionEngine / risk-model logic.
    Each route is evaluated independently through DecisionEngine.evaluate_route_core.
    """

    def __init__(self, engine: Optional[DecisionEngine] = None):
        self.engine = engine or DecisionEngine()

    def evaluate_route(
        self,
        route: NormalizedRoute,
        request: TripRequest,
        weather_timeline: List[NormalizedWeatherPoint],
        hazards: List[NormalizedHazard],
        alerts: List[NormalizedAlert],
        traffic: Optional[TrafficSnapshot],
        agreement_status: str = "high"
    ) -> EvaluatedRoute:
        """
        Evaluates a single route independently through the deterministic decision engine.
        """
        ctx = TripContext(
            origin=request.origin,
            destination=request.destination,
            departure_time=request.departure_time,
            mode=request.mode,
            route=route,
            weather_timeline=weather_timeline,
            hazards=hazards,
            alerts=alerts,
            arrival_deadline=request.arrival_deadline,
            agreement_status=agreement_status,
            traffic=traffic
        )

        engine_res = self.engine.evaluate_route_core(ctx)

        static_dur = route.total_duration
        traffic_aware_dur = traffic.traffic_aware_duration if traffic else static_dur
        traffic_delay_sec = traffic.delay_seconds if traffic else 0.0

        # Calculate exposure score from engine segment risks if available
        exposure_score = float(engine_res.overall_risk.overall_score)
        bottleneck_score = max([r.risk_score for r in engine_res.segment_risks], default=engine_res.overall_risk.overall_score)

        # Check deadline feasibility
        is_feasible = True
        feasibility_reason = None
        if request.arrival_deadline:
            arrival_time = request.departure_time + traffic_aware_dur
            if arrival_time > request.arrival_deadline:
                is_feasible = False
                feasibility_reason = (
                    f"Arrival at {arrival_time.strftime('%H:%M')} exceeds requested deadline "
                    f"{request.arrival_deadline.strftime('%H:%M')}."
                )

        relevant_hazards_list = []
        for th in engine_res.hazards:
            if th.relevance.spatially_relevant and th.relevance.weather_triggered:
                relevant_hazards_list.append(Hazard(
                    id=th.hazard.id,
                    type=th.hazard.type,
                    title=f"Hazard {th.hazard.id}",
                    description=th.relevance.relevance_reason or "Route hazard active",
                    lat=th.hazard.lat,
                    lng=th.hazard.lng,
                    severity=engine_res.overall_risk.level,
                    source_name=th.hazard.source_name,
                    source_class=th.hazard.source_class.value
                ))

        evaluation = RouteEvaluation(
            route_id=route.route_id,
            risk_score=engine_res.overall_risk.overall_score,
            risk_level=engine_res.overall_risk.level,
            static_duration=static_dur,
            traffic_aware_duration=traffic_aware_dur,
            traffic_delay_seconds=traffic_delay_sec,
            exposure_score=exposure_score,
            bottleneck_score=bottleneck_score,
            hazard_count=len(relevant_hazards_list),
            is_feasible=is_feasible,
            feasibility_reason=feasibility_reason,
            recommendation_headline=engine_res.recommendation_headline,
            recommendation_body=engine_res.recommendation_body,
            suggested_mode=engine_res.suggested_mode.value if engine_res.suggested_mode else None,
            suggested_departure_time=engine_res.suggested_time,
            is_selected=False,
            selection_reason=None,
            provenance=route.provenance
        )

        return EvaluatedRoute(
            route_id=route.route_id,
            summary=route.summary,
            distance_km=route.total_distance_km,
            static_duration=static_dur,
            polyline=route.polyline,
            segments=engine_res.route_segments_with_weather,
            traffic=traffic,
            evaluation=evaluation,
            hazards=relevant_hazards_list,
            source_name=route.provider_name,
            provenance=route.provenance,
            risk=engine_res.overall_risk
        )

    def select_and_rank_routes(
        self,
        evaluated_routes: List[EvaluatedRoute],
        departure_time: datetime,
        arrival_deadline: Optional[datetime] = None
    ) -> Tuple[EvaluatedRoute, List[EvaluatedRoute]]:
        """
        Applies the deterministic 6-step route selection policy.
        Returns: (selected_route, ranked_routes_list)
        """
        if not evaluated_routes:
            raise ValueError("Cannot select from an empty list of evaluated routes.")

        if len(evaluated_routes) == 1:
            single = evaluated_routes[0]
            single.evaluation.is_selected = True
            single.evaluation.selection_reason = "Primary route evaluated."
            return single, [single]

        # Step 1: Feasibility filtering
        feasible_routes = [r for r in evaluated_routes if r.evaluation.is_feasible]

        candidate_pool = feasible_routes if feasible_routes else evaluated_routes

        # Step 2: Hard alert avoidance
        def has_hard_avoidance(r: EvaluatedRoute) -> bool:
            body = r.evaluation.recommendation_body.lower()
            headline = r.evaluation.recommendation_headline.lower()
            return "emergency" in headline or "avoid" in body or "closure" in body or "halt" in body

        non_hard_avoidance = [r for r in candidate_pool if not has_hard_avoidance(r)]
        if non_hard_avoidance:
            active_pool = non_hard_avoidance
        else:
            active_pool = candidate_pool  # All routes affected by regional alert

        # Comparator implementing steps 3, 4, 5, 6
        def compare_routes(r1: EvaluatedRoute, r2: EvaluatedRoute) -> int:
            # Step 3: Risk tier comparison
            tier1 = get_risk_tier(r1.evaluation.risk_level)
            tier2 = get_risk_tier(r2.evaluation.risk_level)
            if tier1 != tier2:
                return -1 if tier1 < tier2 else 1

            # Same tier: check risk score difference
            diff = r1.evaluation.risk_score - r2.evaluation.risk_score
            # Step 4: If |diff| >= 15, lower risk wins
            if abs(diff) >= 15:
                return -1 if diff < 0 else 1

            # Step 5: If |diff| < 15, shorter traffic-aware duration wins
            dur1 = r1.evaluation.traffic_aware_duration.total_seconds()
            dur2 = r2.evaluation.traffic_aware_duration.total_seconds()
            if abs(dur1 - dur2) > 1.0:
                return -1 if dur1 < dur2 else 1

            # Step 6: Tie-breaking
            # a. Lower exposure score
            if abs(r1.evaluation.exposure_score - r2.evaluation.exposure_score) > 0.1:
                return -1 if r1.evaluation.exposure_score < r2.evaluation.exposure_score else 1

            # b. Shorter distance
            if abs(r1.distance_km - r2.distance_km) > 0.1:
                return -1 if r1.distance_km < r2.distance_km else 1

            # c. Lexicographical route_id for strict determinism
            return -1 if r1.route_id < r2.route_id else 1

        # Sort candidate pool
        sorted_candidates = sorted(active_pool, key=functools.cmp_to_key(compare_routes))
        selected = sorted_candidates[0]

        # Construct full ranked list: sorted_candidates + any routes filtered out
        remaining = [r for r in evaluated_routes if r.route_id != selected.route_id]
        sorted_remaining = sorted(remaining, key=functools.cmp_to_key(compare_routes))
        full_ranked = [selected] + sorted_remaining

        # Annotate selection reasons
        selected.evaluation.is_selected = True
        dur_mins = int(selected.evaluation.traffic_aware_duration.total_seconds() // 60)
        delay_mins = int(selected.evaluation.traffic_delay_seconds // 60)
        delay_str = f" (+{delay_mins}m traffic)" if delay_mins > 0 else ""

        selected.evaluation.selection_reason = (
            f"Recommended: {format_risk_level(selected.evaluation.risk_level)} risk ({selected.evaluation.risk_score}/100) "
            f"with {dur_mins} min travel time{delay_str}."
        )

        for alt in full_ranked[1:]:
            alt.evaluation.is_selected = False
            alt_dur_mins = int(alt.evaluation.traffic_aware_duration.total_seconds() // 60)
            dur_diff = alt_dur_mins - dur_mins

            if not alt.evaluation.is_feasible:
                alt.evaluation.selection_reason = f"Infeasible: {alt.evaluation.feasibility_reason}"
            elif has_hard_avoidance(alt) and not has_hard_avoidance(selected):
                alt.evaluation.selection_reason = "Alternative route subject to active emergency alert/closure."
            elif get_risk_tier(alt.evaluation.risk_level) > get_risk_tier(selected.evaluation.risk_level):
                alt.evaluation.selection_reason = (
                    f"Higher risk tier ({format_risk_level(alt.evaluation.risk_level)} vs "
                    f"{format_risk_level(selected.evaluation.risk_level)})."
                )
            elif alt.evaluation.risk_score >= selected.evaluation.risk_score + 15:
                alt.evaluation.selection_reason = (
                    f"+{alt.evaluation.risk_score - selected.evaluation.risk_score} higher risk score."
                )
            elif dur_diff > 0:
                alt.evaluation.selection_reason = (
                    f"{dur_diff} min slower effective travel time ({alt_dur_mins} min vs {dur_mins} min)."
                )
            elif dur_diff < 0 and alt.evaluation.risk_score > selected.evaluation.risk_score:
                alt.evaluation.selection_reason = (
                    f"{abs(dur_diff)} min faster, but +{alt.evaluation.risk_score - selected.evaluation.risk_score} higher risk."
                )
            else:
                alt.evaluation.selection_reason = "Alternative route evaluated."

        return selected, full_ranked

