import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from app.providers.llm.base import LLMProvider
from app.models.assistant import (
    AssistantParseRequest,
    AssistantParseResponse,
    AssistantChatRequest,
    AssistantChatResponse,
    ExtractedIntent,
    DecisionFacts,
    UserIntentEnum,
)
from app.models.trip import TripRequest, TripResponse
from app.models.enums import TransportMode, TripStatus
from app.services.trip_service import TripService
from app.services.grounding_validator import GroundingValidator

logger = logging.getLogger(__name__)


class AssistantService:
    """
    Orchestrator for natural language intent extraction and grounded decision explanations.
    Strictly preserves the architectural boundary:
    - LLM extracts intent and converts structured facts to natural language.
    - Deterministic DecisionEngine / TripService remains the single source of truth for risk and decisions.
    - GroundingValidator prevents hallucinations and guarantees adherence to DecisionFacts.
    """

    def __init__(self, llm_provider: LLMProvider, trip_service: Optional[TripService] = None, conversation_repository: Optional['app.repositories.interfaces.conversation_repository.ConversationRepository'] = None):
        self.llm_provider = llm_provider
        self.trip_service = trip_service
        self.conversation_repository = conversation_repository

    async def parse_intent(self, request: AssistantParseRequest) -> AssistantParseResponse:
        """
        Parses free-form user query into structured ExtractedIntent.
        Completeness is evaluated deterministically by the backend.
        """
        try:
            raw_dict = await self.llm_provider.extract_intent(
                request.query, reference_time=request.reference_time
            )
            intent = ExtractedIntent(**raw_dict)
        except Exception as e:
            logger.warning(f"Malformed LLM intent response: {e}. Falling back to safe defaults.")
            intent = ExtractedIntent(
                raw_query=request.query,
                user_intent=UserIntentEnum.trip_decision
            )

        missing_fields: List[str] = []
        clarification_prompt: Optional[str] = None

        # Deterministic completeness check based on intent
        if intent.user_intent == UserIntentEnum.trip_decision:
            if not intent.origin:
                missing_fields.append("origin")
            if not intent.destination:
                missing_fields.append("destination")

            if "destination" in missing_fields and "origin" in missing_fields:
                clarification_prompt = "Where would you like to travel from and to?"
            elif "destination" in missing_fields:
                clarification_prompt = f"Where are you traveling to from {intent.origin}?"
            elif "origin" in missing_fields:
                clarification_prompt = f"Where are you starting your trip to {intent.destination} from?"

        is_complete = len(missing_fields) == 0

        return AssistantParseResponse(
            intent=intent,
            is_complete=is_complete,
            missing_fields=missing_fields,
            clarification_prompt=clarification_prompt
        )

    async def chat(self, request: AssistantChatRequest, uid: Optional[str] = None, conversation_id: Optional[str] = None) -> AssistantChatResponse:
        """
        Full end-to-end assistant interaction flow:
        User message -> Intent Extraction -> Backend Validation -> TripService -> Grounding Validator -> Explanation.
        """
        # 1. Extract Intent
        parse_res = await self.parse_intent(
            AssistantParseRequest(
                query=request.message,
                reference_time=request.context_time
            )
        )
        intent = parse_res.intent

        # Apply context fallbacks if extracted intent fields are empty
        if not intent.origin and request.context_origin:
            intent.origin = request.context_origin
        if not intent.destination and request.context_destination:
            intent.destination = request.context_destination
        if not intent.mode and request.context_mode:
            intent.mode = request.context_mode

        # 2. Handle Non-Trip Queries (Do NOT force non-trip questions through TripService)
        if intent.user_intent in [UserIntentEnum.weather_question, UserIntentEnum.general_weather]:
            return AssistantChatResponse(
                message="I can check the weather along any travel route. Please tell me your origin and destination (for example: 'Noida to Gurgaon by bike') to analyze commute weather and road risks.",
                intent=intent,
                trip_request=None,
                trip_response=None,
                status="info",
                provenance=self.llm_provider.provenance,
                grounding_fallback_used=False,
                conversation_id=conversation_id
            )

        if intent.user_intent == UserIntentEnum.alert_question:
            return AssistantChatResponse(
                message="Active official advisories and monitored flood/waterlogging hazards are evaluated whenever you plan a route. Where are you traveling today?",
                intent=intent,
                trip_request=None,
                trip_response=None,
                status="info",
                provenance=self.llm_provider.provenance,
                grounding_fallback_used=False,
                conversation_id=conversation_id
            )

        # 3. Deterministic Trip Request Validation
        missing_fields = []
        if not intent.origin:
            missing_fields.append("origin")
        if not intent.destination:
            missing_fields.append("destination")

        if missing_fields:
            prompt = parse_res.clarification_prompt or "Please provide your starting point and destination."
            return AssistantChatResponse(
                message=prompt,
                intent=intent,
                trip_request=None,
                trip_response=None,
                status="need_clarification",
                clarification_prompt=prompt,
                provenance=self.llm_provider.provenance,
                grounding_fallback_used=False,
                conversation_id=conversation_id
            )

        if not self.trip_service:
            return AssistantChatResponse(
                message="Trip analysis service is currently offline.",
                intent=intent,
                trip_request=None,
                trip_response=None,
                status="error",
                provenance=self.llm_provider.provenance,
                grounding_fallback_used=True,
                conversation_id=conversation_id
            )

        # 4. Construct Validated TripRequest
        mode = intent.mode or TransportMode.car
        dep_time = intent.departure_time or (
            request.context_time or (datetime.now(timezone.utc) + timedelta(minutes=15))
        )

        trip_req = TripRequest(
            origin=intent.origin,
            destination=intent.destination,
            departure_time=dep_time,
            arrival_deadline=intent.arrival_deadline,
            mode=mode
        )

        # 5. Authoritative Deterministic Execution
        trip_res: TripResponse = await self.trip_service.analyze_trip(trip_req)

        # 6. Extract DecisionFacts
        facts = self._build_decision_facts(trip_req, trip_res)

        # 7. Generate Candidate Explanation from LLM
        fallback_used = False
        try:
            candidate_explanation = await self.llm_provider.generate_explanation(facts.model_dump())
            # 8. Grounding & Safety Validation
            is_valid, reject_reason = GroundingValidator.validate(candidate_explanation, facts)
            if is_valid:
                final_explanation = candidate_explanation
            else:
                logger.warning(f"LLM explanation rejected by GroundingValidator ({reject_reason}). Using deterministic fallback.")
                final_explanation = GroundingValidator.generate_fallback(facts)
                fallback_used = True
        except Exception as e:
            logger.error(f"Error during LLM explanation generation: {e}. Using deterministic fallback.")
            final_explanation = GroundingValidator.generate_fallback(facts)
            fallback_used = True

        # 9. Determine Status Semantics
        if trip_res.status == TripStatus.success:
            chat_status = "success"
        elif trip_res.status in [TripStatus.routing_unavailable, TripStatus.weather_unavailable, TripStatus.degraded]:
            chat_status = "degraded"
        else:
            chat_status = "error"

        response = AssistantChatResponse(
            message=final_explanation,
            intent=intent,
            trip_request=trip_req,
            trip_response=trip_res,
            status=chat_status,
            provenance=self.llm_provider.provenance,
            grounding_fallback_used=fallback_used,
            conversation_id=conversation_id
        )

        if uid and conversation_id and self.conversation_repository:
            import asyncio
            async def _safe_save_message():
                try:
                    await self.conversation_repository.save_message(uid, conversation_id, request, response)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Background conversation persistence failed for conv {conversation_id}: {e}")
            asyncio.create_task(_safe_save_message())

        return response

    def _build_decision_facts(self, req: TripRequest, res: TripResponse) -> DecisionFacts:
        """Extracts strictly authoritative fields from TripResponse into DecisionFacts."""
        selected_route = None
        if res.routes:
            for r in res.routes:
                if r.evaluation and r.evaluation.is_selected:
                    selected_route = r
                    break
            if not selected_route and res.routes:
                selected_route = res.routes[0]

        summary = selected_route.summary if selected_route else (res.route[0].summary if res.route else None)
        route_id = selected_route.route_id if selected_route else None
        
        static_mins = None
        if selected_route and selected_route.static_duration:
            static_mins = int(selected_route.static_duration.total_seconds() // 60)
        elif res.estimated_duration:
            static_mins = int(res.estimated_duration.total_seconds() // 60)

        traffic_aware_mins = None
        delay_mins = None
        traffic_status = None
        traffic_cond = None
        if res.traffic:
            traffic_status = res.traffic.status.value if hasattr(res.traffic.status, "value") else str(res.traffic.status)
            traffic_cond = res.traffic.condition.value if hasattr(res.traffic.condition, "value") else str(res.traffic.condition)
            delay_mins = int(res.traffic.delay_seconds // 60)
            traffic_aware_mins = int(res.traffic.traffic_aware_duration.total_seconds() // 60)

        risk_score = res.risk.overall_score if res.risk else None
        risk_level = res.risk.level if res.risk else None
        risk_factors = [f"{f.name}: {f.description}" for f in res.risk.factors] if res.risk else []

        active_alerts = []
        active_hazards = []
        if res.hazards:
            for h in res.hazards:
                h_type_str = h.type.value if hasattr(h.type, "value") else str(h.type)
                active_hazards.append(f"{h.title} ({h_type_str})")

        alternatives_summaries = [r.summary for r in res.routes if r.summary] if res.routes else []

        is_feasible = True
        feasibility_reason = None
        if selected_route and selected_route.evaluation:
            is_feasible = selected_route.evaluation.is_feasible
            feasibility_reason = selected_route.evaluation.feasibility_reason

        rec_headline = res.recommendation.headline if res.recommendation else None
        rec_body = res.recommendation.body if res.recommendation else None

        provenance_sources = [s.name for s in res.sources]

        return DecisionFacts(
            status=res.status,
            origin=req.origin,
            destination=req.destination,
            mode=req.mode,
            departure_time=req.departure_time,
            arrival_deadline=req.arrival_deadline,
            selected_route_summary=summary,
            selected_route_id=route_id,
            distance_km=res.distance_km,
            static_duration_minutes=static_mins,
            traffic_aware_duration_minutes=traffic_aware_mins,
            traffic_delay_minutes=delay_mins,
            traffic_status=traffic_status,
            traffic_condition=traffic_cond,
            risk_score=risk_score,
            risk_level=risk_level,
            risk_factors=risk_factors,
            recommendation_headline=rec_headline,
            recommendation_body=rec_body,
            active_alerts=active_alerts,
            active_hazards=active_hazards,
            route_alternatives_summaries=alternatives_summaries,
            alternatives_count=len(res.routes),
            is_feasible=is_feasible,
            feasibility_reason=feasibility_reason,
            provenance_sources=provenance_sources
        )
