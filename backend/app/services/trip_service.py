from datetime import datetime, timezone, timedelta
import uuid
from typing import List, Tuple

from app.models.trip import TripRequest, TripResponse, ModeOption, Recommendation, DataSource
from app.models.enums import TransportMode
from app.decision_engine.engine import DecisionEngine
from app.decision_engine.normalized_models import TripContext, NormalizedHazard
from app.providers.weather.base import WeatherProvider
from app.providers.routing.base import RoutingProvider
from app.providers.routing.mock import MockRoutingProvider
from app.providers.alerts.base import AlertProvider

class TripService:
    def __init__(
        self,
        weather_provider: WeatherProvider,
        routing_provider: RoutingProvider,
        alert_provider: AlertProvider,
    ):
        self.weather_provider = weather_provider
        self.routing_provider = routing_provider
        self.alert_provider = alert_provider
        self.engine = DecisionEngine()
        self._metro_provider = MockRoutingProvider()

    def _mock_geocode(self, location: str) -> Tuple[float, float]:
        """
        Temporary development resolver. 
        In the future, this will be replaced by a GeocodingProvider.
        """
        location = location.lower()
        if "gurgaon" in location or "cyber hub" in location:
            return 28.4942, 77.0860
        # Default to Noida Sector 62
        return 28.6270, 77.3650

    async def analyze_trip(self, request: TripRequest) -> TripResponse:
        origin_lat, origin_lng = self._mock_geocode(request.origin)
        dest_lat, dest_lng = self._mock_geocode(request.destination)
        
        active_routing_provider = self._metro_provider if request.mode == TransportMode.metro else self.routing_provider
        routing_provider_name = active_routing_provider.provider_name
        if request.mode == TransportMode.metro:
            routing_provider_name = f"{routing_provider_name} (Demo Transit)"
            
        weather = await self.weather_provider.get_forecast(origin_lat, origin_lng, request.departure_time, 12)
        alerts = await self.alert_provider.get_active_alerts(origin_lat, origin_lng)
        
        analysis_id = str(uuid.uuid4())
        
        try:
            routes = await active_routing_provider.get_route(origin_lat, origin_lng, dest_lat, dest_lng, request.mode)
            route = routes[0]  # Take the primary route for the decision engine
            routing_status = active_routing_provider.route_status.value
        except Exception as e:
            from app.models.risk import RiskAssessment, Confidence, RiskFactor
            from app.models.enums import RiskLevel, ConfidenceLevel
            return TripResponse(
                analysis_id=analysis_id,
                request=request,
                risk=RiskAssessment(
                    overall_score=100,
                    level=RiskLevel.severe,
                    confidence=Confidence(level=ConfidenceLevel.high, explanation="Routing unavailable"),
                    factors=[RiskFactor(name="Routing Error", description="Could not calculate route", score=100, level=RiskLevel.severe, weight=1.0)],
                    summary="Routing Unavailable"
                ),
                route=[],
                recommendation=Recommendation(
                    headline="Routing Unavailable",
                    body=f"Could not calculate route: {str(e)}",
                    suggested_mode=None,
                    suggested_departure_time=None,
                ),
                mode_options=[],
                hazards=[],
                sources=[
                    DataSource(name=self.weather_provider.provider_name, type="Weather", last_updated=datetime.now(timezone.utc)),
                    DataSource(name=routing_provider_name, type="Routing [unavailable]", last_updated=datetime.now(timezone.utc)),
                ],
                estimated_duration=timedelta(0),
                distance_km=0.0
            )
            
        hazards: List[NormalizedHazard] = [] # Mock empty hazards for now
        
        # 2. Build Context
        ctx = TripContext(
            origin=request.origin,
            destination=request.destination,
            departure_time=request.departure_time,
            mode=request.mode,
            route=route,
            weather_timeline=weather,
            hazards=hazards,
            alerts=alerts
        )
        
        # 3. Evaluate Engine
        result = self.engine.evaluate(ctx)
        
        # 4. Mock alternative modes (in reality, run engine for each mode)
        mode_options = []
        
        return TripResponse(
            analysis_id=analysis_id,
            request=request,
            risk=result.overall_risk,
            route=result.route_segments_with_weather,
            recommendation=Recommendation(
                headline=result.recommendation_headline,
                body=result.recommendation_body,
                suggested_mode=result.suggested_mode,
                suggested_departure_time=result.suggested_time,
            ),
            mode_options=mode_options,
            hazards=[],
            sources=[
                DataSource(name=self.weather_provider.provider_name, type="Weather", last_updated=datetime.now(timezone.utc)),
                DataSource(name=routing_provider_name, type=f"Routing [{routing_status}]", last_updated=datetime.now(timezone.utc)),
            ],
            estimated_duration=result.total_duration,
            distance_km=result.total_distance_km
        )
