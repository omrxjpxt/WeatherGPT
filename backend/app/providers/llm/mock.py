import re
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from app.providers.llm.base import LLMProvider


class MockLLMProvider(LLMProvider):
    """
    Deterministic Mock LLM provider for WeatherGPT prototype.
    Explicitly labeled as demo/mock provenance.
    Parsing is deterministic, rule-assisted, and limited to documented English & Hinglish patterns.
    """

    @property
    def provider_name(self) -> str:
        return "Mock LLM Provider"

    @property
    def provenance(self) -> str:
        return "demo/mock"

    async def extract_intent(self, text: str, reference_time: Optional[datetime] = None) -> Dict[str, Any]:
        ref_time = reference_time or datetime.now(timezone.utc)
        text_lower = text.lower()

        # 1. Determine User Intent
        intent = "trip_decision"
        if any(w in text_lower for w in ["alert", "warning", "red alert", "warning feed"]):
            intent = "alert_question"
        elif any(w in text_lower for w in ["compare", "vs", "versus", "which mode"]):
            intent = "route_comparison"
        elif any(w in text_lower for w in ["what if", "delay by", "leave later", "what-if"]):
            intent = "what_if"
        elif any(w in text_lower for w in ["weather today", "forecast", "mausam kaisa", "baarish hogi kya", "temperature kya hai"]) and not any(w in text_lower for w in ["jaana", "reach", "travel", "commute", "drive", "trip"]):
            intent = "weather_question"

        # 2. Extract Origin and Destination
        origin = None
        destination = None

        # Pattern: "... se ... [tak / ko]" (Hinglish: Noida se Gurgaon / Noida se Gurgaon tak)
        se_match = re.search(r"([a-zA-Z0-9\s]+?)\s+se\s+([a-zA-Z0-9\s]+?)(?:\s+(?:tak|jaana|bike|car|metro|walk|me)|$|,|\?)", text, re.IGNORECASE)
        if se_match:
            cand_origin = se_match.group(1).strip()
            cand_dest = se_match.group(2).strip()
            # Clean common words
            cand_origin = re.sub(r"^(kal\s+|aaj\s+|\d+\s*baje\s+)", "", cand_origin, flags=re.IGNORECASE).strip()
            origin = self._canonical_location(cand_origin)
            destination = self._canonical_location(cand_dest)

        # Pattern: "... to ..." (English: from Noida to Gurgaon / Noida to Gurgaon)
        if not origin or not destination:
            to_match = re.search(r"(?:from\s+)?([a-zA-Z0-9\s]+?)\s+to\s+([a-zA-Z0-9\s]+?)(?:\s+(?:by|via|at|for|tomorrow|today)|$|,|\?)", text, re.IGNORECASE)
            if to_match:
                origin = self._canonical_location(to_match.group(1).strip())
                destination = self._canonical_location(to_match.group(2).strip())

        # Explicit preposition extraction
        in_match = re.search(r"(?:in|at|from)\s+([a-zA-Z0-9\s]+?)(?:,|\?|\s+can|\s+to|\s+by|\s+how|$)", text, re.IGNORECASE)
        if in_match and not origin:
            cand = in_match.group(1).strip()
            if any(k in cand.lower() for k in ["noida", "delhi", "gurgaon", "cp"]):
                origin = self._canonical_location(cand)

        to_place_match = re.search(r"(?:to|reach)\s+([a-zA-Z0-9\s]+?)(?:,|\?|\s+by|\s+from|\s+at|$)", text, re.IGNORECASE)
        if to_place_match and not destination:
            cand = to_place_match.group(1).strip()
            if any(k in cand.lower() for k in ["noida", "delhi", "gurgaon", "cyber", "dtu", "college"]):
                destination = self._canonical_location(cand)

        # Fallback keyword extraction for common Delhi-NCR spots
        if not destination and not origin:
            if "gurgaon" in text_lower or "cyber hub" in text_lower:
                destination = "Gurgaon Cyber Hub"
            elif "college" in text_lower or "dtu" in text_lower:
                destination = "Delhi Technological University (DTU)"
            elif "noida" in text_lower:
                origin = "Noida Sector 62"
            elif "delhi" in text_lower or "connaught place" in text_lower or "cp" in text_lower:
                destination = "Connaught Place, Delhi"

        # 3. Extract Transport Mode
        mode = None
        if any(w in text_lower for w in ["bike", "motorcycle", "two-wheeler", "scooter", "two wheeler"]):
            mode = "bike"
        elif any(w in text_lower for w in ["car", "cab", "drive", "driving", "four-wheeler"]):
            mode = "car"
        elif any(w in text_lower for w in ["metro", "train", "subway"]):
            mode = "metro"
        elif any(w in text_lower for w in ["walk", "walking", "foot"]):
            mode = "walk"

        # 4. Extract Date / Departure Time
        departure_time = None
        trip_date = None

        is_tomorrow = any(w in text_lower for w in ["kal", "tomorrow"])
        is_today = any(w in text_lower for w in ["aaj", "today"])

        target_date = ref_time.date()
        if is_tomorrow:
            target_date = ref_time.date() + timedelta(days=1)
            trip_date = "tomorrow"
        elif is_today:
            trip_date = "today"

        # Hour extraction (e.g., "8 baje", "8 am", "8:00", "08:00")
        hour_match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(?:baje|am|pm|hrs|h)?", text_lower)
        if hour_match:
            raw_hour = int(hour_match.group(1))
            minute = int(hour_match.group(2)) if hour_match.group(2) else 0
            # Handle PM logic
            if "pm" in text_lower or "shaam" in text_lower or "raat" in text_lower:
                if raw_hour < 12:
                    raw_hour += 12
            elif "am" in text_lower or "subah" in text_lower:
                if raw_hour == 12:
                    raw_hour = 0
            elif raw_hour < 6 and not is_tomorrow:
                # Ambiguous e.g. 8 -> assume 8 AM or 8 PM
                raw_hour = raw_hour + 12 if raw_hour < 6 else raw_hour

            try:
                departure_time = datetime(
                    target_date.year, target_date.month, target_date.day,
                    raw_hour, minute, tzinfo=timezone.utc
                )
            except ValueError:
                departure_time = None

        # 5. Extract Weather Concerns
        weather_concern = None
        if any(w in text_lower for w in ["baarish", "rain", "raining", "shower", "waterlogging", "flood"]):
            weather_concern = "rain"
        elif any(w in text_lower for w in ["fog", "smog", "visibility", "dhund"]):
            weather_concern = "fog"
        elif any(w in text_lower for w in ["heat", "garmi", "loo"]):
            weather_concern = "heat"
        elif any(w in text_lower for w in ["wind", "storm", "toofan"]):
            weather_concern = "wind"

        return {
            "origin": origin,
            "destination": destination,
            "departure_time": departure_time,
            "arrival_deadline": None,
            "mode": mode,
            "trip_date": trip_date,
            "user_intent": intent,
            "weather_concern": weather_concern,
            "scenario_modifiers": [],
            "raw_query": text
        }

    def _canonical_location(self, loc: str) -> str:
        loc_clean = loc.strip().title()
        if "noida" in loc_clean.lower():
            return "Noida Sector 62"
        if "gurgaon" in loc_clean.lower() or "cyber" in loc_clean.lower():
            return "Gurgaon Cyber Hub"
        if "delhi" in loc_clean.lower():
            return "Connaught Place, Delhi"
        return loc_clean

    async def generate_explanation(self, decision_facts: Dict[str, Any]) -> str:
        status = decision_facts.get("status", "success")

        # 1. Handle Degraded States Grounded in DecisionFacts
        if status == "routing_unavailable":
            origin = decision_facts.get("origin", "origin")
            destination = decision_facts.get("destination", "destination")
            return (
                f"Routing data is currently unavailable between {origin} and {destination}. "
                "WeatherGPT cannot reliably compare routes or compute travel risk without route geometry."
            )

        if status == "weather_unavailable":
            return (
                "Weather forecast data is currently unavailable for this corridor. "
                "Environmental exposure along the route cannot be evaluated right now."
            )

        # 2. Grounded Explanation for Successful Decision
        route = decision_facts.get("selected_route_summary") or "Primary Route"
        risk_score = decision_facts.get("risk_score", 0)
        risk_level = decision_facts.get("risk_level", "low").capitalize()
        duration = decision_facts.get("traffic_aware_duration_minutes") or decision_facts.get("static_duration_minutes") or 30
        delay = decision_facts.get("traffic_delay_minutes", 0)
        mode = decision_facts.get("mode", "travel")
        headline = decision_facts.get("recommendation_headline", "Travel Advisory")
        body = decision_facts.get("recommendation_body", "")
        alerts = decision_facts.get("active_alerts", [])
        hazards = decision_facts.get("active_hazards", [])
        alts_count = decision_facts.get("alternatives_count", 0)

        explanation = (
            f"Taking {mode} via {route} has an overall {risk_level} risk score of {risk_score}/100. "
            f"Expected travel time is approximately {duration} minutes"
        )
        if delay and delay > 0:
            explanation += f" with a {delay} min traffic delay."
        else:
            explanation += " with free-flowing traffic."

        if headline:
            explanation += f" Recommendation: {headline}."
            if body:
                explanation += f" {body}."

        if alerts:
            explanation += f" Note active alert: {alerts[0]}."
        elif hazards:
            explanation += f" Watch for corridor hazard: {hazards[0]}."

        if alts_count > 1:
            explanation += f" {alts_count} alternative routes were evaluated and ranked deterministically."

        return explanation
