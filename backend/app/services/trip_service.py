from datetime import datetime, timezone, timedelta
import uuid
from typing import List, Tuple, Optional

from app.models.trip import TripRequest, TripResponse, ModeOption, Recommendation, DataSource
from app.models.enums import TransportMode
from app.decision_engine.engine import DecisionEngine
from app.decision_engine.route_evaluator import RouteEvaluator
from app.decision_engine.normalized_models import TripContext, NormalizedHazard
from app.providers.weather.base import WeatherProvider
from app.providers.routing.base import RoutingProvider
from app.providers.routing.mock import MockRoutingProvider
from app.providers.alerts.base import AlertProvider
from app.providers.traffic.base import TrafficProvider
from app.providers.traffic.fallback import UnavailableTrafficProvider
from app.models.hazard import Hazard
from app.models.enums import RiskLevel

class TripService:
    def __init__(
        self,
        weather_provider: WeatherProvider,
        routing_provider: RoutingProvider,
        alert_provider: AlertProvider,
        traffic_provider: Optional[TrafficProvider] = None,
        secondary_weather_provider: Optional[WeatherProvider] = None,
        secondary_alert_provider: Optional[AlertProvider] = None,
        hazard_repository: Optional['app.repositories.interfaces.hazard_repository.HazardRepository'] = None,
        trip_repository: Optional['app.repositories.interfaces.trip_repository.TripRepository'] = None,
    ):
        self.weather_provider = weather_provider
        self.routing_provider = routing_provider
        self.alert_provider = alert_provider
        self.traffic_provider = traffic_provider or UnavailableTrafficProvider()
        self.secondary_weather_provider = secondary_weather_provider
        self.secondary_alert_provider = secondary_alert_provider
        self.hazard_repository = hazard_repository
        self.trip_repository = trip_repository
        
        self.engine = DecisionEngine()
        self.route_evaluator = RouteEvaluator(self.engine)
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

    async def analyze_trip(self, request: TripRequest, uid: Optional[str] = None) -> TripResponse:
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
            from app.models.enums import TripStatus
            return TripResponse(
                analysis_id=str(uuid.uuid4()),
                status=TripStatus.weather_unavailable,
                request=request,
                risk=None,
                route=[],
                recommendation=None,
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
            routing_status = active_routing_provider.route_status.value
        except Exception as e:
            from app.models.enums import TripStatus
            return TripResponse(
                analysis_id=analysis_id,
                status=TripStatus.routing_unavailable,
                request=request,
                risk=None,
                route=[],
                recommendation=None,
                mode_options=[],
                hazards=[],
                sources=[
                    DataSource(name=self.weather_provider.provider_name, type="Weather", last_updated=datetime.now(timezone.utc)),
                    DataSource(name=routing_provider_name, type="Routing [unavailable]", last_updated=datetime.now(timezone.utc)),
                ],
                estimated_duration=timedelta(0),
                distance_km=0.0,
                routes=[]
            )

        from app.models.enums import TrafficStatus, TrafficCondition, CongestionLevel
        from app.models.traffic import TrafficSnapshot

        evaluated_routes = []
        for route in routes:
            # 1. Fetch or reuse Traffic Data (Prevent N+1 calls: reuse route.traffic if already present)
            traffic = None
            if route.traffic is not None and route.traffic.status != TrafficStatus.unavailable:
                traffic = route.traffic
            else:
                try:
                    traffic = await self.traffic_provider.get_traffic_for_route(route, request.departure_time, request.mode)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Traffic provider failed for route {route.route_id}: {e}")
                    traffic = TrafficSnapshot(
                        status=TrafficStatus.unavailable,
                        condition=TrafficCondition.unknown,
                        congestion_level=CongestionLevel.unknown,
                        delay_seconds=0.0,
                        static_duration=route.total_duration,
                        traffic_aware_duration=route.total_duration,
                        timestamp=datetime.now(timezone.utc),
                        source_name=self.traffic_provider.provider_name,
                        provenance="unavailable"
                    )

            # 2. Corridor-independent hazards query
            route_hazards = []
            if self.hazard_repository and route.segments:
                try:
                    min_lat = min(min(seg.start_lat, seg.end_lat) for seg in route.segments)
                    max_lat = max(max(seg.start_lat, seg.end_lat) for seg in route.segments)
                    min_lng = min(min(seg.start_lng, seg.end_lng) for seg in route.segments)
                    max_lng = max(max(seg.start_lng, seg.end_lng) for seg in route.segments)

                    route_hazards = await self.hazard_repository.get_hazards_in_region(
                        min_lat - 0.05, min_lng - 0.05,
                        max_lat + 0.05, max_lng + 0.05
                    )
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Hazard repository failed for route {route.route_id}: {e}")
                    route_hazards = []

            # 3. Independent evaluation through decision engine
            evaluated_route = self.route_evaluator.evaluate_route(
                route=route,
                request=request,
                weather_timeline=comparison.primary_timeline,
                hazards=route_hazards,
                alerts=alerts,
                traffic=traffic,
                agreement_status=comparison.agreement_status.value
            )
            evaluated_routes.append(evaluated_route)

        # 4. Deterministic selection & ranking
        selected_route, ranked_routes = self.route_evaluator.select_and_rank_routes(
            evaluated_routes,
            departure_time=request.departure_time,
            arrival_deadline=request.arrival_deadline
        )

        mode_options = []
        sources = [
            DataSource(name=self.weather_provider.provider_name, type="Weather (Primary)", last_updated=datetime.now(timezone.utc)),
            DataSource(name=routing_provider_name, type=f"Routing [{routing_status}]", last_updated=datetime.now(timezone.utc)),
            DataSource(name=self.alert_provider.provider_name, type=f"Alerts [{self.alert_provider.provider_class.value}]", last_updated=datetime.now(timezone.utc)),
        ]

        if selected_route.traffic:
            traffic = selected_route.traffic
            traffic_status_str = traffic.status.value if hasattr(traffic.status, "value") else str(traffic.status)
            sources.append(DataSource(name=traffic.source_name, type=f"Traffic [{traffic_status_str}]", last_updated=traffic.timestamp))

        if self.secondary_weather_provider and comparison.secondary_timeline:
            sources.append(DataSource(name=self.secondary_weather_provider.provider_name, type="Weather (Secondary)", last_updated=datetime.now(timezone.utc)))

        if self.secondary_alert_provider:
            sources.append(DataSource(name=self.secondary_alert_provider.provider_name, type=f"Alerts [{self.secondary_alert_provider.provider_class.value}]", last_updated=datetime.now(timezone.utc)))

        suggested_mode = None
        if selected_route.evaluation.suggested_mode:
            try:
                suggested_mode = TransportMode(selected_route.evaluation.suggested_mode)
            except ValueError:
                suggested_mode = None

        response = TripResponse(
            analysis_id=analysis_id,
            request=request,
            risk=selected_route.risk,
            route=selected_route.segments,
            recommendation=Recommendation(
                headline=selected_route.evaluation.recommendation_headline,
                body=selected_route.evaluation.recommendation_body,
                suggested_mode=suggested_mode,
                suggested_departure_time=selected_route.evaluation.suggested_departure_time,
            ),
            mode_options=mode_options,
            hazards=selected_route.hazards,
            sources=sources,
            estimated_duration=selected_route.static_duration,
            distance_km=selected_route.distance_km,
            traffic=selected_route.traffic,
            routes=ranked_routes
        )

        if uid and self.trip_repository:
            # Fire-and-forget to avoid blocking the user request
            async def _safe_persist():
                try:
                    await self.trip_repository.save_trip_decision(uid, response)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Background trip persistence failed for uid {uid}: {e}")
            asyncio.create_task(_safe_persist())

        return response
