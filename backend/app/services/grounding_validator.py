import re
from typing import Tuple, Optional
from app.models.assistant import DecisionFacts
from app.models.enums import TripStatus


class GroundingValidator:
    """
    Deterministic safety and grounding validator for LLM-generated explanations.
    Guarantees that the natural language explanation does not introduce hallucinations,
    invented numeric values, or claims contradicting TripStatus.
    """

    @classmethod
    def validate(cls, explanation: str, facts: DecisionFacts) -> Tuple[bool, Optional[str]]:
        text_lower = explanation.lower()

        # 1. Contradiction of Degraded TripStatus
        if facts.status == TripStatus.routing_unavailable:
            # Must acknowledge routing unavailability, not claim routes or clear travel
            if not any(phrase in text_lower for phrase in ["routing", "navigation", "route data", "direction"]):
                return False, "Failed to mention routing data context when routing is unavailable"
            if not any(phrase in text_lower for phrase in ["unavailable", "offline", "cannot", "can't", "unable", "not available"]):
                return False, "Contradicts TripStatus.routing_unavailable by not stating unavailability"
            # Must not claim a definitive low/safe risk score
            if any(term in text_lower for term in ["is completely safe", "risk is low", "no risk", "0/100"]):
                return False, "Claims safe route when routing is unavailable"

        if facts.status == TripStatus.weather_unavailable:
            if not any(phrase in text_lower for phrase in ["weather data", "forecast", "weather service"]):
                return False, "Failed to mention weather context when weather is unavailable"
            if not any(phrase in text_lower for phrase in ["unavailable", "offline", "cannot", "unable", "not available"]):
                return False, "Contradicts TripStatus.weather_unavailable by not stating unavailability"

        # 2. Unsupported Numeric Risk Score
        if facts.risk_score is not None:
            # Match patterns like "risk of 85", "risk score 85", "85/100", "score: 85"
            score_matches = re.findall(r"(?:risk\s*(?:score)?\s*(?:of|is|:)?\s*|\bscore\s*:\s*)(\d{1,3})", text_lower)
            score_matches += re.findall(r"(\d{1,3})\s*(?:/100|out of 100)", text_lower)
            for sm in score_matches:
                val = int(sm)
                # Allow a tight tolerance of +/- 2 points, otherwise reject hallucination
                if abs(val - facts.risk_score) > 2:
                    return False, f"Hallucinated risk score {val} does not match authoritative score {facts.risk_score}"
        else:
            # If risk_score is None, the explanation must not claim a specific numeric risk score
            score_matches = re.findall(r"(?:risk\s*(?:score)?\s*(?:of|is|:)?\s*|\bscore\s*:\s*)(\d{1,3})", text_lower)
            score_matches += re.findall(r"(\d{1,3})\s*(?:/100|out of 100)", text_lower)
            if score_matches:
                return False, f"Claims specific numeric risk score {score_matches[0]} when risk calculation is absent"

        # 3. Unsupported Traffic Delay
        delay_matches = re.findall(r"(\d+)\s*(?:min|minute)s?\s*(?:delay|traffic delay)", text_lower)
        delay_matches += re.findall(r"(?:\+|\bplus\s*)(\d+)\s*(?:m\b|min)", text_lower)
        if delay_matches:
            actual_delay = facts.traffic_delay_minutes or 0
            for dm in delay_matches:
                val = int(dm)
                if abs(val - actual_delay) > 5:
                    return False, f"Hallucinated traffic delay {val}m does not match authoritative delay {actual_delay}m"

        # 4. Invented Emergency Closure / Evacuation Alerts
        if len(facts.active_alerts) == 0:
            if any(term in text_lower for term in ["evacuate", "evacuation order", "police closed", "expressway closed", "emergency shutdown"]):
                return False, "Claims emergency evacuation or road closure when zero active alerts exist"

        # 5. Invented Routes
        known_routes = [r.lower() for r in ([facts.selected_route_summary] + facts.route_alternatives_summaries) if r]
        # If explanation mentions a specific corridor that is completely absent from DecisionFacts
        all_candidate_corridors = ["dnd flyway", "noida-greater noida", "outer ring road", "nh-48", "mehrauli-gurgaon"]
        for corridor in all_candidate_corridors:
            if corridor in text_lower:
                if not any(corridor in r for r in known_routes):
                    return False, f"Mentions route corridor '{corridor}' not present in evaluated route facts"

        return True, None

    @classmethod
    def generate_fallback(cls, facts: DecisionFacts) -> str:
        """
        Generates a 100% deterministic, grounded fallback explanation from DecisionFacts.
        """
        if facts.status == TripStatus.routing_unavailable:
            return (
                f"Routing data is currently unavailable between {facts.origin} and {facts.destination}. "
                "WeatherGPT cannot reliably compare routes or compute risk without route geometry. "
                "Please check back when navigation services are restored."
            )

        if facts.status == TripStatus.weather_unavailable:
            return (
                f"Weather forecast data is currently unavailable for your trip from {facts.origin} to {facts.destination}. "
                "Environmental exposure cannot be evaluated at this time."
            )

        # Successful trip analysis
        route_str = f" via {facts.selected_route_summary}" if facts.selected_route_summary else ""
        time_str = f"{facts.traffic_aware_duration_minutes or facts.static_duration_minutes or 30} minutes"
        delay_str = f" (+{facts.traffic_delay_minutes}m delay)" if (facts.traffic_delay_minutes and facts.traffic_delay_minutes > 0) else ""
        level_val = facts.risk_level.value if hasattr(facts.risk_level, "value") else str(facts.risk_level or "low")
        risk_str = f"{level_val.capitalize()} risk ({facts.risk_score}/100)" if (facts.risk_score is not None and facts.risk_level) else "Risk assessment unavailable"
        
        mode_str = facts.mode.value if hasattr(facts.mode, "value") else str(facts.mode)
        parts = [
            f"For your {mode_str} trip from {facts.origin} to {facts.destination}{route_str}:",
            f"• Assessment: {risk_str} with an estimated travel time of {time_str}{delay_str}."
        ]

        if facts.recommendation_headline:
            body = f" - {facts.recommendation_body}" if facts.recommendation_body else ""
            parts.append(f"• Recommendation: {facts.recommendation_headline}{body}")

        if facts.risk_factors:
            parts.append(f"• Key Factors: {', '.join(facts.risk_factors[:3])}.")

        if facts.active_alerts:
            parts.append(f"• Active Alerts: {facts.active_alerts[0]}.")

        if not facts.is_feasible and facts.feasibility_reason:
            parts.append(f"• Feasibility Warning: {facts.feasibility_reason}.")

        if facts.traffic_status == "mock" or any("mock" in s.lower() for s in facts.provenance_sources):
            parts.append("(Source Note: Traffic conditions and alerts evaluated using demo/mock models).")

        return "\n".join(parts)
