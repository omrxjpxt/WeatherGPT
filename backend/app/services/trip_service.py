from datetime import datetime, timezone, timedelta
import uuid
from typing import List, Tuple, Optional

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
        secondary_weather_provider: Optional[WeatherProvider] = None,
        secondary_alert_provider: Optional[AlertProvider] = None,
    ):
        self.weather_provider = weather_provider
        self.routing_provider = routing_provider
        self.alert_provider = alert_provider
        self.secondary_weather_provider = secondary_weather_provider
        self.secondary_alert_provider = secondary_alert_provider
        
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

    def _evaluate_alert_policy(self, alerts: List['NormalizedAlert']) -> List['NormalizedAlert']:
        """
        Evaluates the source class of each alert against WeatherGPT's override policy.
        - authoritative: eligible
        - secondary: not eligible (contributes to risk only)
        - demo: eligible ONLY if demo_mode is enabled
        """
        from app.core.config import settings
        from app.models.enums import AlertSourceClass
        
        for alert in alerts:
            if alert.source_class == AlertSourceClass.authoritative:
                alert.is_override_eligible = True
            elif alert.source_class == AlertSourceClass.secondary:
                alert.is_override_eligible = False
            elif alert.source_class == AlertSourceClass.demo:
                alert.is_override_eligible = settings.demo_mode
            else:
                alert.is_override_eligible = False
        return alerts

    async def analyze_trip(self, request: TripRequest) -> TripResponse:
        origin_lat, origin_lng = self._mock_geocode(request.origin)
        dest_lat, dest_lng = self._mock_geocode(request.destination)
        
        active_routing_provider = self._metro_provider if request.mode == TransportMode.metro else self.routing_provider
        routing_provider_name = active_routing_provider.provider_name
        if request.mode == TransportMode.metro:
            routing_provider_name = f"{routing_provider_name} (Demo Transit)"
            
        import asyncio
        from app.decision_engine.source_comparison import compare_weather_sources
        
        # We wrap in exceptions to ensure isolated failure
        async def fetch_primary_weather():
            try:
                return await self.weather_provider.get_forecast(origin_lat, origin_lng, request.departure_time, 12)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Primary weather failed: {e}")
                return None
                
        async def fetch_secondary_weather():
            if not self.secondary_weather_provider:
                return None
            try:
                return await self.secondary_weather_provider.get_forecast(origin_lat, origin_lng, request.departure_time, 12)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Secondary weather failed: {e}")
                return None
                
        async def fetch_alerts():
            alerts_gathered = []
            
            async def _fetch_single(p):
                if not p: return []
                try:
                    return await p.get_active_alerts(origin_lat, origin_lng)
                except Exception:
                    return []
                    
            res = await asyncio.gather(
                _fetch_single(self.alert_provider),
                _fetch_single(self.secondary_alert_provider)
            )
            alerts_gathered.extend(res[0])
            alerts_gathered.extend(res[1])
            return alerts_gathered
            
        weather_p, weather_s, raw_alerts = await asyncio.gather(
            fetch_primary_weather(),
            fetch_secondary_weather(),
            fetch_alerts()
        )
        
        comparison = compare_weather_sources(weather_p, weather_s)
        
        # 1.1 If both weather sources are unavailable, fallback gracefully.
        if not comparison.primary_timeline:
            from app.models.risk import RiskAssessment, Confidence, RiskFactor
            from app.models.enums import RiskLevel, ConfidenceLevel
            return TripResponse(
                analysis_id=str(uuid.uuid4()),
                request=request,
                risk=RiskAssessment(
                    overall_score=100,
                    level=RiskLevel.severe,
                    confidence=Confidence(level=ConfidenceLevel.low, explanation="Weather data unavailable"),
                    factors=[RiskFactor(name="Weather Error", description="Could not fetch weather data", score=100, level=RiskLevel.severe, weight=1.0)],
                    summary="Weather Unavailable"
                ),
                route=[],
                recommendation=Recommendation(
                    headline="Weather Unavailable",
                    body="Could not fetch weather data from any source.",
                    suggested_mode=None,
                    suggested_departure_time=None,
                ),
                mode_options=[],
                hazards=[],
                sources=[],
                estimated_duration=timedelta(0),
                distance_km=0.0
            )
            
        # Fetch and evaluate alerts against WeatherGPT override policy
        alerts = self._evaluate_alert_policy(raw_alerts)
        
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
            weather_timeline=comparison.primary_timeline,
            hazards=hazards,
            alerts=alerts,
            agreement_status=comparison.agreement_status.value
        )
        
        # 3. Evaluate Engine
        result = self.engine.evaluate(ctx)
        
        # 4. Mock alternative modes (in reality, run engine for each mode)
        mode_options = []
        
        sources = [
            DataSource(name=self.weather_provider.provider_name, type="Weather (Primary)", last_updated=datetime.now(timezone.utc)),
            DataSource(name=routing_provider_name, type=f"Routing [{routing_status}]", last_updated=datetime.now(timezone.utc)),
            DataSource(name=self.alert_provider.provider_name, type=f"Alerts [{self.alert_provider.provider_class.value}]", last_updated=datetime.now(timezone.utc)),
        ]
        
        if self.secondary_weather_provider and comparison.secondary_timeline:
            sources.append(DataSource(name=self.secondary_weather_provider.provider_name, type="Weather (Secondary)", last_updated=datetime.now(timezone.utc)))
            
        if self.secondary_alert_provider:
             sources.append(DataSource(name=self.secondary_alert_provider.provider_name, type=f"Alerts [{self.secondary_alert_provider.provider_class.value}]", last_updated=datetime.now(timezone.utc)))
             
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
            sources=sources,
            estimated_duration=result.total_duration,
            distance_km=result.total_distance_km
        )
