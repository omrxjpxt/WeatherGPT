from typing import List
from app.decision_engine.models import EngineDecisionResult, SegmentRisk
from app.decision_engine.normalized_models import TripContext, NormalizedWeatherPoint
from app.decision_engine.temporal_alignment import align_route_with_weather
from app.decision_engine.risk_model import calculate_segment_risk, _score_to_level
from app.decision_engine.alert_override import check_alert_override
from app.decision_engine.uncertainty import calculate_confidence
from app.models.risk import RiskAssessment, RiskFactor
from app.models.enums import RiskLevel, TransportMode
from app.models.route import RouteSegment
from app.models.weather import WeatherPoint

class DecisionEngine:
    """
    Pure, deterministic, side-effect free decision engine.
    No I/O. Normalized input -> identical output.
    """
    def evaluate(self, ctx: TripContext) -> EngineDecisionResult:
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
                    precipitation=weather.precipitation,
                    humidity=weather.humidity,
                    wind_speed=weather.wind_speed,
                    condition=weather.condition,
                    icon="🌧️" if weather.precipitation > 0 else "⛅"
                )
            ))
            
            max_risk_score = max(max_risk_score, score)
            for f in factors:
                # keep highest score for each factor type
                if f.name not in all_factors_dict or all_factors_dict[f.name].score < f.score:
                    all_factors_dict[f.name] = f
                    
        # 3. Overall Risk aggregation
        # Simplified: max segment risk is overall risk
        overall_score = max_risk_score
        overall_level = _score_to_level(overall_score)
        
        # 4. Uncertainty / Confidence
        # In a real app we'd pass data_sources_count
        confidence = calculate_confidence(ctx.departure_time, data_sources_count=3)
        
        # 5. Alert Override
        end_time = ctx.departure_time + ctx.route.total_duration
        override_alert = check_alert_override(ctx.alerts, ctx.route, ctx.departure_time, end_time)
        
        alert_override_applied = False
        if override_alert:
            alert_override_applied = True
            overall_score = max(overall_score, 85) # Override pushes to high/severe
            overall_level = _score_to_level(overall_score)
            all_factors_dict["Official Alert"] = RiskFactor(
                name="Official Alert",
                description=f"{override_alert.severity.value.upper()}: Check details.",
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
            suggested_time = ctx.departure_time # Simplified
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
