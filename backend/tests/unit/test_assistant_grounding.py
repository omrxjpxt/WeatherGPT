import pytest
from datetime import datetime, timezone, timedelta
from app.models.assistant import (
    DecisionFacts,
    ExtractedIntent,
    UserIntentEnum,
    AssistantChatRequest,
    AssistantParseRequest,
)
from app.models.enums import TransportMode, TripStatus, RiskLevel
from app.services.grounding_validator import GroundingValidator
from app.services.assistant_service import AssistantService
from app.providers.llm.mock import MockLLMProvider
from app.providers.llm.base import LLMProvider


class HallucinatingLLMProvider(LLMProvider):
    """Test LLM provider that intentionally attempts various hallucinations."""
    def __init__(self, hallucinated_text: str):
        self.hallucinated_text = hallucinated_text

    @property
    def provider_name(self) -> str:
        return "Hallucinating LLM"

    @property
    def provenance(self) -> str:
        return "demo/mock"

    async def extract_intent(self, text: str, reference_time=None):
        return {
            "origin": "Noida Sector 62",
            "destination": "Gurgaon Cyber Hub",
            "mode": "car",
            "user_intent": "trip_decision"
        }

    async def generate_explanation(self, decision_facts):
        return self.hallucinated_text


def make_sample_facts(status=TripStatus.success, risk_score=25, delay=5) -> DecisionFacts:
    return DecisionFacts(
        status=status,
        origin="Noida Sector 62",
        destination="Gurgaon Cyber Hub",
        mode=TransportMode.car,
        departure_time=datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc),
        selected_route_summary="Via Noida-Greater Noida Expy",
        static_duration_minutes=25,
        traffic_aware_duration_minutes=30,
        traffic_delay_minutes=delay,
        traffic_status="mock",
        traffic_condition="clear",
        risk_score=risk_score,
        risk_level=RiskLevel.low,
        risk_factors=["Rain: Light mist"],
        recommendation_headline="Favorable commute",
        recommendation_body="Optimal route",
        active_alerts=[],
        active_hazards=[],
        route_alternatives_summaries=["Via DND Flyway"],
        alternatives_count=2,
        is_feasible=True,
        provenance_sources=["Open-Meteo API", "Mock Routing API"]
    )


def test_mutable_list_defaults_are_isolated():
    """Verify mutable list defaults do not share state across instances."""
    i1 = ExtractedIntent()
    i2 = ExtractedIntent()
    i1.scenario_modifiers.append("avoid_toll")
    assert len(i2.scenario_modifiers) == 0

    f1 = DecisionFacts(
        status=TripStatus.success, origin="A", destination="B",
        mode=TransportMode.bike, departure_time=datetime.now(timezone.utc)
    )
    f2 = DecisionFacts(
        status=TripStatus.success, origin="A", destination="B",
        mode=TransportMode.bike, departure_time=datetime.now(timezone.utc)
    )
    f1.risk_factors.append("Fog")
    assert len(f2.risk_factors) == 0


def test_valid_grounded_explanation():
    """Valid explanation passing all grounding rules."""
    facts = make_sample_facts()
    good_text = (
        "Taking car via Via Noida-Greater Noida Expy has an overall Low risk score of 25/100. "
        "Estimated travel time is 30 minutes with a 5 min traffic delay. "
        "Recommendation: Favorable commute. Optimal route."
    )
    is_valid, reason = GroundingValidator.validate(good_text, facts)
    assert is_valid is True
    assert reason is None


def test_unsupported_numeric_risk_claim():
    """Validator rejects hallucinated risk score differing from DecisionFacts."""
    facts = make_sample_facts(risk_score=25)
    # Claims risk is 85 when actual is 25
    bad_text = "Your route has an extreme risk of 85/100 due to severe weather."
    is_valid, reason = GroundingValidator.validate(bad_text, facts)
    assert is_valid is False
    assert "Hallucinated risk score 85" in reason


def test_unsupported_traffic_delay_claim():
    """Validator rejects hallucinated traffic delay exceeding tolerance."""
    facts = make_sample_facts(delay=5)
    # Claims 45m traffic delay when actual is 5m
    bad_text = "Traffic is snarled with a 45 min traffic delay on the highway."
    is_valid, reason = GroundingValidator.validate(bad_text, facts)
    assert is_valid is False
    assert "Hallucinated traffic delay 45m" in reason


def test_unsupported_route_claim():
    """Validator rejects corridor corridor not present in DecisionFacts."""
    facts = make_sample_facts()
    # Mentions Outer Ring Road which is not evaluated
    bad_text = "We recommend taking Outer Ring Road instead of the expressway."
    is_valid, reason = GroundingValidator.validate(bad_text, facts)
    assert is_valid is False
    assert "outer ring road" in reason.lower()


def test_unsupported_alert_evacuation_claim():
    """Validator rejects emergency closures/evacuations when zero active alerts exist."""
    facts = make_sample_facts()
    bad_text = "State police closed the entire highway due to an evacuation order."
    is_valid, reason = GroundingValidator.validate(bad_text, facts)
    assert is_valid is False
    assert "evacuation" in reason.lower() or "closed" in reason.lower()


def test_routing_unavailable_grounding():
    """Validator enforces routing unavailability acknowledgement."""
    facts = make_sample_facts(status=TripStatus.routing_unavailable, risk_score=None)

    # Bad explanation claiming safe trip
    bad_text = "The road is completely safe and clear for your drive."
    is_valid, reason = GroundingValidator.validate(bad_text, facts)
    assert is_valid is False

    # Good explanation acknowledging unavailability
    good_text = (
        "Routing data is currently unavailable between Noida and Gurgaon. "
        "WeatherGPT cannot compute route risks without navigation geometry."
    )
    is_valid, reason = GroundingValidator.validate(good_text, facts)
    assert is_valid is True


def test_weather_unavailable_grounding():
    """Validator enforces weather unavailability acknowledgement."""
    facts = make_sample_facts(status=TripStatus.weather_unavailable, risk_score=None)

    # Bad text inventing weather
    bad_text = "The weather along the route is sunny and 30 degrees."
    is_valid, reason = GroundingValidator.validate(bad_text, facts)
    assert is_valid is False

    # Good text acknowledging weather data offline
    good_text = "Weather forecast data is currently unavailable for this corridor."
    is_valid, reason = GroundingValidator.validate(good_text, facts)
    assert is_valid is True


def test_fallback_generator_grounding():
    """Deterministic fallback generator produces valid, grounded text for any state."""
    # 1. Success state fallback
    facts_ok = make_sample_facts()
    fb_ok = GroundingValidator.generate_fallback(facts_ok)
    assert "25/100" in fb_ok
    assert "Via Noida-Greater Noida Expy" in fb_ok
    is_valid, _ = GroundingValidator.validate(fb_ok, facts_ok)
    assert is_valid is True

    # 2. Routing unavailable fallback
    facts_no_route = make_sample_facts(status=TripStatus.routing_unavailable, risk_score=None)
    fb_no_route = GroundingValidator.generate_fallback(facts_no_route)
    assert "Routing data is currently unavailable" in fb_no_route
    is_valid, _ = GroundingValidator.validate(fb_no_route, facts_no_route)
    assert is_valid is True


@pytest.mark.asyncio
async def test_assistant_rejection_triggers_fallback():
    """When LLM hallucinates, AssistantService catches it and returns grounded fallback."""
    hallucinating_provider = HallucinatingLLMProvider("Everything is fine, risk of 99/100!")
    facts = make_sample_facts(risk_score=25)

    # Mock trip service
    class DummyTripService:
        async def analyze_trip(self, req):
            from app.models.trip import TripResponse
            return TripResponse(
                status=TripStatus.success,
                request=req,
                route=[],
                mode_options=[],
                hazards=[],
                sources=[],
                estimated_duration=timedelta(minutes=30),
                distance_km=30.0,
                risk=None
            )

    service = AssistantService(llm_provider=hallucinating_provider, trip_service=DummyTripService())
    req = AssistantChatRequest(message="Noida to Gurgaon by car")
    res = await service.chat(req)

    # Must flag that fallback was used and message must NOT have the hallucinated 99/100
    assert res.grounding_fallback_used is True
    assert "99/100" not in res.message
