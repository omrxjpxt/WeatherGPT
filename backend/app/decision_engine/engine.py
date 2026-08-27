from typing import List, Optional
from datetime import timedelta
from app.decision_engine.models import EngineDecisionResult, SegmentRisk
from app.decision_engine.normalized_models import TripContext, NormalizedWeatherPoint
from app.decision_engine.temporal_alignment import align_route_with_weather
from app.decision_engine.risk_model import calculate_segment_risk, _score_to_level
from app.decision_engine.alert_override import check_alert_override
from app.decision_engine.uncertainty import calculate_confidence
from app.decision_engine.scenario_ranker import get_best_alternative
from app.models.risk import RiskAssessment, RiskFactor
from app.models.enums import RiskLevel, TransportMode
from app.models.route import RouteSegment
from app.models.weather import WeatherPoint

# MVP Engineering Assumptions for Risk Aggregation
BOTTLENECK_WEIGHT = 0.6
EXPOSURE_WEIGHT = 0.4
SEARCH_OFFSETS_MINS = [-30, -15, 15, 30, 45]

class DecisionEngine:
    """
    Pure, deterministic, side-effect free decision engine.
    No I/O. Normalized input -> identical output.
    """
    
    def evaluate(self, ctx: TripContext) -> EngineDecisionResult:
        """
        Evaluates the trip and searches for better alternatives if applicable.
        """
        current_result = self._evaluate_core(ctx)
        
        # Search for a better departure time
        candidates = []
        for offset in SEARCH_OFFSETS_MINS:
            cand_time = ctx.departure_time + timedelta(minutes=offset)
            # Create a shallow copy and update departure time
            # In a real system, the weather timeline should be sufficiently large
            cand_ctx = TripContext(
                origin=ctx.origin,
                destination=ctx.destination,
                departure_time=cand_time,
                mode=ctx.mode,
                route=ctx.route,
                weather_timeline=ctx.weather_timeline,
                hazards=ctx.hazards,
                alerts=ctx.alerts,
                arrival_deadline=ctx.arrival_deadline
            )
            # We don't want the core evaluation to recurse
            try:
                cand_res = self._evaluate_core(cand_ctx)
                candidates.append((cand_time, cand_res))
            except ValueError:
                # E.g. if weather timeline doesn't cover this offset
                continue
                
        best_alt_time = get_best_alternative(current_result, candidates, ctx.arrival_deadline, ctx.departure_time)
        
        if best_alt_time:
            current_result.suggested_time = best_alt_time
            
        return current_result
        

    def _evaluate_core(self, ctx: TripContext) -> EngineDecisionResult:
        # 1. Temporal Alignment
        aligned = align_route_with_weather(ctx.route, ctx.departure_time, ctx.weather_timeline)
        
        # 2. Risk Calculation per segment
        segment_risks = []
        route_segments_with_weather = []
        all_factors_dict = {}
        max_risk_score = 0
        
        for idx, (seg, arrival_time, weather) in enumerate(aligned):
            score, level, factors, reason = calculate_segment_risk(
                segment=seg,
                weather=weather,
                hazards=ctx.hazards,
                mode=ctx.mode
            )
            
            segment_risks.append(SegmentRisk(
                segment_index=idx,
                risk_score=score,
                risk_level=level,
                reason=reason
            ))
            
            route_segments_with_weather.append(RouteSegment(
                start_lat=seg.start_lat,
                start_lng=seg.start_lng,
                end_lat=seg.end_lat,
                end_lng=seg.end_lng,
                risk_level=level,
                description=f"Segment {idx+1}",
                weather=WeatherPoint(
                    time=weather.time,
                    temperature=weather.temperature,
                    precipitation_mm=weather.precipitation_mm,
                    humidity=weather.humidity,
                    wind_speed=weather.wind_speed,
                    wind_gusts=weather.wind_gusts,
                    visibility=weather.visibility,
                    condition=weather.condition,
                    icon="🌧️" if weather.precipitation_mm > 0 else "⛅"
                )
            ))
            
            max_risk_score = max(max_risk_score, score)
            for f in factors:
                if f.name not in all_factors_dict or all_factors_dict[f.name].score < f.score:
                    all_factors_dict[f.name] = f
                    
        # 3. Overall Risk aggregation
        bottleneck_score = max_risk_score
        
        total_time = sum([seg.estimated_duration.total_seconds() for seg, _, _ in aligned])
        if total_time > 0:
            weighted_sum = sum([r.risk_score * (seg.estimated_duration.total_seconds()) for r, (seg, _, _) in zip(segment_risks, aligned)])
            exposure_score = weighted_sum / total_time
        else:
            exposure_score = bottleneck_score
            
        overall_score = int((bottleneck_score * BOTTLENECK_WEIGHT) + (exposure_score * EXPOSURE_WEIGHT))
        
        # Absolute severity guardrail: don't let exposure weight hide a severe bottleneck
        if bottleneck_score >= 75:
            overall_score = max(overall_score, 75)
            
        overall_level = _score_to_level(overall_score)
        
        # 4. Uncertainty / Confidence
        confidence = calculate_confidence(ctx.departure_time, data_sources_count=3)
        
        # 5. Alert Override
        end_time = ctx.departure_time + ctx.route.total_duration
        override_alert, is_exact_match = check_alert_override(ctx.alerts, ctx.route, ctx.departure_time, end_time)
        
        alert_override_applied = False
        if override_alert:
            alert_override_applied = True
            overall_score = max(overall_score, 85) # Override pushes to high/severe
            overall_level = _score_to_level(overall_score)
            match_type = "Exact Route Match" if is_exact_match else "Regional Match"
            all_factors_dict["Official Alert"] = RiskFactor(
                name="Official Alert",
                description=f"{override_alert.severity.value.upper()} ({match_type}): Check details.",
                score=100,
                level=RiskLevel.severe,
                weight=1.0
            )

        # 6. Recommendation Logic
        if alert_override_applied:
            rec_head = f"Official {override_alert.severity.value.capitalize()} Alert active"
            rec_body = "An official alert covers your route during travel time. Reconsider travel."
            suggested_mode = None
            suggested_time = None
        elif overall_score >= 70:
            rec_head = "Switch mode or delay departure"
            rec_body = "High environmental exposure detected on route."
            suggested_mode = TransportMode.metro if ctx.mode != TransportMode.metro else None
            suggested_time = None
        elif overall_score >= 40:
            rec_head = "Proceed with caution"
            rec_body = "Moderate conditions detected. Be prepared."
            suggested_mode = None
            suggested_time = None
        else:
            rec_head = "Clear conditions"
            rec_body = "Good to go!"
            suggested_mode = None
            suggested_time = None
            
        return EngineDecisionResult(
            overall_risk=RiskAssessment(
                overall_score=overall_score,
                level=overall_level,
                confidence=confidence,
                factors=list(all_factors_dict.values()),
                summary=rec_body
            ),
            segment_risks=segment_risks,
            route_segments_with_weather=route_segments_with_weather,
            recommendation_headline=rec_head,
            recommendation_body=rec_body,
            suggested_mode=suggested_mode,
            suggested_time=suggested_time,
            alert_override_applied=alert_override_applied,
            active_override_alert=override_alert,
            total_duration=ctx.route.total_duration,
            total_distance_km=ctx.route.total_distance_km
        )
