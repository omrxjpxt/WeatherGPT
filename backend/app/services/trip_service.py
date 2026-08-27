from datetime import datetime, timezone
import uuid
from typing import List

from app.models.trip import TripRequest, TripResponse, ModeOption, Recommendation, DataSource
from app.models.enums import TransportMode
from app.decision_engine.engine import DecisionEngine
from app.decision_engine.normalized_models import TripContext, NormalizedHazard
from app.providers.weather.base import WeatherProvider
from app.providers.routing.base import RoutingProvider
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
        
    async def analyze_trip(self, request: TripRequest) -> TripResponse:
        # For MVP, assume origin is roughly lat/lng to fetch weather/alerts
        lat, lng = 28.6270, 77.3650
        
        # 1. Fetch normalized data
        route = await self.routing_provider.get_route(request.origin, request.destination, request.mode)
        weather = await self.weather_provider.get_forecast(lat, lng, request.departure_time, 12)
        alerts = await self.alert_provider.get_active_alerts(lat, lng)
        hazards: List[NormalizedHazard] = [] # Mock empty hazards for now, could be added to provider
        
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
        
        # 5. Build TripResponse
        analysis_id = str(uuid.uuid4())
        
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
                DataSource(name="Mock Weather API", type="Weather", last_updated=datetime.now(timezone.utc)),
                DataSource(name="Mock Routing API", type="Routing", last_updated=datetime.now(timezone.utc)),
            ],
            estimated_duration=result.total_duration,
            distance_km=result.total_distance_km
        )
