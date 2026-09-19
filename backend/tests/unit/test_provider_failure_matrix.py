import pytest
from datetime import datetime, timezone, timedelta
from app.services.trip_service import TripService
from app.services.assistant_service import AssistantService
from app.models.trip import TripRequest
from app.models.assistant import AssistantChatRequest
from app.models.enums import TransportMode, TripStatus, TrafficStatus, RouteStatus
from app.providers.weather.base import WeatherProvider
from app.providers.routing.base import RoutingProvider
from app.providers.alerts.base import AlertProvider
from app.providers.traffic.base import TrafficProvider
from app.providers.llm.base import LLMProvider
from app.providers.weather.mock import MockWeatherProvider
from app.providers.routing.mock import MockRoutingProvider
from app.providers.alerts.mock import MockAlertProvider
from app.providers.traffic.mock import MockTrafficProvider
from app.repositories.interfaces.hazard_repository import HazardRepository


class BrokenWeatherProvider(WeatherProvider):
    provider_name = "Broken Weather Provider"
    async def get_forecast(self, lat, lng, start_time, hours):
        raise ConnectionResetError("Weather service down")


class BrokenRoutingProvider(RoutingProvider):
    provider_name = "Broken Routing Provider"
    route_status = RouteStatus.unavailable
    async def get_route(self, origin_lat, origin_lng, dest_lat, dest_lng, mode):
        raise TimeoutError("Routing provider gateway timed out")


class BrokenTrafficProvider(TrafficProvider):
    provider_name = "Broken Traffic Provider"
    traffic_status = TrafficStatus.unavailable

    async def get_traffic_for_route(self, route, departure_time, mode):
        raise RuntimeError("Traffic telemetry service down")


class BrokenHazardRepository(HazardRepository):
    async def save_hazard(self, hazard):
        pass

    async def get_nearby_hazards(self, lat, lng, radius_km):
        raise RuntimeError("Spatial database unreachable")

    async def get_hazards_in_region(self, min_lat, min_lng, max_lat, max_lng):
        raise RuntimeError("Spatial database unreachable")


class BrokenLLMProvider(LLMProvider):
    provider_name = "Broken LLM Provider"
    provenance = "mock/broken"

    async def extract_intent(self, text, reference_time=None):
        return {
            "origin": "Noida Sector 62",
            "destination": "Gurgaon Cyber Hub",
            "departure_time": reference_time or datetime.now(timezone.utc),
            "mode": "bike",
            "user_intent": "trip_decision",
            "raw_query": text
        }

    async def generate_explanation(self, decision_facts):
        raise RuntimeError("LLM API endpoint unavailable")


@pytest.mark.asyncio
async def test_degraded_routing_unavailable():
    service = TripService(
        weather_provider=MockWeatherProvider(),
        routing_provider=BrokenRoutingProvider(),
        alert_provider=MockAlertProvider(),
        traffic_provider=MockTrafficProvider()
    )
    req = TripRequest(
        origin="Noida Sector 62",
        destination="Gurgaon Cyber Hub",
        departure_time=datetime(2026, 8, 27, 8, 0, tzinfo=timezone.utc),
        mode=TransportMode.car
    )
    res = await service.analyze_trip(req)
    assert res.status == TripStatus.routing_unavailable
    assert res.risk is None
    assert res.route == []
    assert res.recommendation is None
    # Must report provider status explicitly in sources
    assert any("Routing [unavailable]" in s.type for s in res.sources)


@pytest.mark.asyncio
async def test_degraded_weather_unavailable():
    service = TripService(
        weather_provider=BrokenWeatherProvider(),
        routing_provider=MockRoutingProvider(),
        alert_provider=MockAlertProvider(),
        traffic_provider=MockTrafficProvider()
    )
    req = TripRequest(
        origin="Noida Sector 62",
        destination="Gurgaon Cyber Hub",
        departure_time=datetime(2026, 8, 27, 8, 0, tzinfo=timezone.utc),
        mode=TransportMode.car
    )
    res = await service.analyze_trip(req)
    assert res.status == TripStatus.weather_unavailable
    assert res.risk is None
    assert res.route == []
    assert res.recommendation is None


@pytest.mark.asyncio
async def test_degraded_traffic_unavailable():
    service = TripService(
        weather_provider=MockWeatherProvider(),
        routing_provider=MockRoutingProvider(),
        alert_provider=MockAlertProvider(),
        traffic_provider=BrokenTrafficProvider()
    )
    req = TripRequest(
        origin="Noida Sector 62",
        destination="Gurgaon Cyber Hub",
        departure_time=datetime(2026, 8, 27, 8, 0, tzinfo=timezone.utc),
        mode=TransportMode.car
    )
    res = await service.analyze_trip(req)
    assert res.status == TripStatus.success
    # Traffic is unavailable, but trip analysis proceeds using static baselines
    assert res.traffic is not None
    assert res.traffic.status == TrafficStatus.unavailable
    assert res.traffic.delay_seconds == 0.0
    assert res.traffic.traffic_aware_duration == res.traffic.static_duration


@pytest.mark.asyncio
async def test_degraded_hazards_unavailable():
    service = TripService(
        weather_provider=MockWeatherProvider(),
        routing_provider=MockRoutingProvider(),
        alert_provider=MockAlertProvider(),
        traffic_provider=MockTrafficProvider(),
        hazard_repository=BrokenHazardRepository()
    )
    req = TripRequest(
        origin="Noida Sector 62",
        destination="Gurgaon Cyber Hub",
        departure_time=datetime(2026, 8, 27, 8, 0, tzinfo=timezone.utc),
        mode=TransportMode.car
    )
    res = await service.analyze_trip(req)
    assert res.status == TripStatus.success
    # Hazards query failed, but trip proceeds with 0 active hazards
    assert res.hazards == []
    assert res.risk is not None


@pytest.mark.asyncio
async def test_llm_failure_triggers_deterministic_fallback():
    trip_service = TripService(
        weather_provider=MockWeatherProvider(),
        routing_provider=MockRoutingProvider(),
        alert_provider=MockAlertProvider(),
        traffic_provider=MockTrafficProvider()
    )
    assistant = AssistantService(
        llm_provider=BrokenLLMProvider(),
        trip_service=trip_service
    )
    chat_req = AssistantChatRequest(
        message="Route from Noida to Gurgaon by bike at 8 AM"
    )
    res = await assistant.chat(chat_req)
    assert res.status == "success"
    # Grounding fallback must activate cleanly
    assert res.grounding_fallback_used is True
    assert "route" in res.message.lower() or "risk" in res.message.lower()


@pytest.mark.asyncio
async def test_decision_engine_deterministic_repeated_evaluations():
    service = TripService(
        weather_provider=MockWeatherProvider(),
        routing_provider=MockRoutingProvider(),
        alert_provider=MockAlertProvider(),
        traffic_provider=MockTrafficProvider()
    )
    req = TripRequest(
        origin="Noida Sector 62",
        destination="Gurgaon Cyber Hub",
        departure_time=datetime(2026, 8, 27, 8, 0, tzinfo=timezone.utc),
        mode=TransportMode.car
    )

    baseline = await service.analyze_trip(req)
    for _ in range(10):
        iteration = await service.analyze_trip(req)
        assert iteration.risk.overall_score == baseline.risk.overall_score
        assert iteration.risk.level == baseline.risk.level
        assert len(iteration.risk.factors) == len(baseline.risk.factors)
        assert iteration.recommendation.headline == baseline.recommendation.headline
        assert iteration.estimated_duration == baseline.estimated_duration
        assert len(iteration.routes) == len(baseline.routes)
        
        # Check selected route matches
        baseline_sel = next(r for r in baseline.routes if r.evaluation.is_selected)
        iter_sel = next(r for r in iteration.routes if r.evaluation.is_selected)
        assert baseline_sel.route_id == iter_sel.route_id
        assert baseline_sel.evaluation.risk_score == iter_sel.evaluation.risk_score
