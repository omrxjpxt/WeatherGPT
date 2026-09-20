from datetime import datetime, timezone, timedelta
import uuid
from typing import List, Tuple, Optional

from app.models.trip import TripRequest, TripResponse, ModeOption, Recommendation, DataSource
from app.models.enums import TransportMode
from app.decision_engine.engine import DecisionEngine
from app.decision_engine.route_evaluator import RouteEvaluator
from app.decision_engine.normalized_models import (
    TripContext,
    NormalizedHazard,
    NormalizedRoute,
    NormalizedRouteSegment,
)
from app.providers.weather.base import WeatherProvider
from app.providers.routing.base import RoutingProvider
from app.providers.routing.mock import MockRoutingProvider


def _adapt_normalized_route(base_route: NormalizedRoute, target_mode: TransportMode) -> NormalizedRoute:
    dist_km = base_route.total_distance_km
    if target_mode == TransportMode.bike:
        speed_kmh = 18.0
    elif target_mode == TransportMode.walk:
        speed_kmh = 5.0
    else:  # car
        speed_kmh = 40.0

    target_total_secs = max(300, int((dist_km / speed_kmh) * 3600))
    target_duration = timedelta(seconds=target_total_secs)

    base_secs = max(1, int(base_route.total_duration.total_seconds()))
    scale = target_total_secs / base_secs

    new_segments = [
        NormalizedRouteSegment(
            start_lat=s.start_lat,
            start_lng=s.start_lng,
            end_lat=s.end_lat,
            end_lng=s.end_lng,
            distance_km=s.distance_km,
            estimated_duration=timedelta(seconds=max(10, int(s.estimated_duration.total_seconds() * scale))),
            traffic_congestion_factor=s.traffic_congestion_factor,
        )
        for s in base_route.segments
    ]

    return NormalizedRoute(
        route_id=f"{base_route.route_id}_{target_mode.value}",
        summary=f"{base_route.summary} ({target_mode.value.capitalize()})",
        polyline=base_route.polyline,
        segments=new_segments,
        total_distance_km=dist_km,
        total_duration=target_duration,
        provider_name=base_route.provider_name,
        provenance=base_route.provenance,
    )
from app.providers.alerts.base import AlertProvider
from app.providers.traffic.base import TrafficProvider
from app.providers.traffic.fallback import UnavailableTrafficProvider
from app.models.hazard import Hazard
from app.models.enums import RiskLevel

from app.providers.geocoding.base import GeocodingProvider, GeocodingResolutionError
from app.providers.geocoding.fallback import FallbackGeocodingProvider
from app.providers.geocoding.gazetteer import CuratedGazetteerGeocodingProvider
from app.providers.air_quality.base import AirQualityProvider, AirQualitySnapshot

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
        geocoding_provider: Optional[GeocodingProvider] = None,
        air_quality_provider: Optional[AirQualityProvider] = None,
        metro_provider: Optional[RoutingProvider] = None,
    ):
        self.weather_provider = weather_provider
        self.routing_provider = routing_provider
        self.alert_provider = alert_provider
        self.traffic_provider = traffic_provider or UnavailableTrafficProvider()
        self.secondary_weather_provider = secondary_weather_provider
        self.secondary_alert_provider = secondary_alert_provider
        self.hazard_repository = hazard_repository
        self.trip_repository = trip_repository
        self.geocoding_provider = geocoding_provider or FallbackGeocodingProvider(
            providers=[CuratedGazetteerGeocodingProvider()]
        )
        self.air_quality_provider = air_quality_provider
        
        self.engine = DecisionEngine()
        self.route_evaluator = RouteEvaluator(self.engine)
        self._metro_provider = metro_provider or MockRoutingProvider()

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
        import asyncio
        from app.decision_engine.source_comparison import compare_weather_sources

        # 1. Resolve Origin and Destination via Confidence-Aware Geocoder
        origin_res, dest_res = await asyncio.gather(
            self.geocoding_provider.geocode(request.origin),
            self.geocoding_provider.geocode(request.destination),
        )

        if not origin_res:
            raise GeocodingResolutionError(
                message=f"Could not resolve origin '{request.origin}' with sufficient confidence.",
                query=request.origin,
                status="unresolved_origin",
            )
        if not dest_res:
            raise GeocodingResolutionError(
                message=f"Could not resolve destination '{request.destination}' with sufficient confidence.",
                query=request.destination,
                status="unresolved_destination",
            )

        origin_lat, origin_lng = origin_res.lat, origin_res.lng
        dest_lat, dest_lng = dest_res.lat, dest_res.lng

        geocoding_provenance = {
            "origin_provider": origin_res.provider,
            "origin_provenance": origin_res.provenance.value if hasattr(origin_res.provenance, "value") else str(origin_res.provenance),
            "origin_confidence": str(origin_res.confidence),
            "destination_provider": dest_res.provider,
            "destination_provenance": dest_res.provenance.value if hasattr(dest_res.provenance, "value") else str(dest_res.provenance),
            "destination_confidence": str(dest_res.confidence),
        }
        
        active_routing_provider = self._metro_provider if request.mode == TransportMode.metro else self.routing_provider
        routing_provider_name = active_routing_provider.provider_name
        if request.mode == TransportMode.metro and isinstance(active_routing_provider, MockRoutingProvider):
            routing_provider_name = f"{routing_provider_name} (Demo Transit)"

        # 2. Concurrently fetch independent upstream provider data
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

        async def fetch_routing():
            primary_routes = None
            road_routes = None
            metro_routes = None
            routing_status = "ok"
            routing_err = None
            try:
                if request.mode == TransportMode.metro:
                    metro_routes = await self._metro_provider.get_route(
                        origin_lat, origin_lng, dest_lat, dest_lng, TransportMode.metro, departure_time=request.departure_time
                    )
                    routing_status = self._metro_provider.route_status.value
                    primary_routes = metro_routes
                    try:
                        road_routes = await self.routing_provider.get_route(
                            origin_lat, origin_lng, dest_lat, dest_lng, TransportMode.car, departure_time=request.departure_time
                        )
                    except Exception:
                        road_routes = None
                else:
                    road_routes = await self.routing_provider.get_route(
                        origin_lat, origin_lng, dest_lat, dest_lng, request.mode, departure_time=request.departure_time
                    )
                    routing_status = self.routing_provider.route_status.value
                    primary_routes = road_routes
                    try:
                        metro_routes = await self._metro_provider.get_route(
                            origin_lat, origin_lng, dest_lat, dest_lng, TransportMode.metro, departure_time=request.departure_time
                        )
                    except Exception:
                        metro_routes = None

                return primary_routes, road_routes, metro_routes, routing_status, None
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Routing failed: {e}")
                return None, None, None, "unavailable", e

        async def fetch_air_quality():
            if not self.air_quality_provider:
                return None
            try:
                return await self.air_quality_provider.get_air_quality(
                    origin_lat, origin_lng, request.departure_time, hours=6
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Air quality fetch failed: {e}")
                return None

        # Execute weather, secondary weather, alerts, routing, and air quality in parallel
        weather_p, weather_s, raw_alerts, (routes, road_routes, metro_routes, routing_status, routing_err), aqi_timeline = await asyncio.gather(
            fetch_primary_weather(),
            fetch_secondary_weather(),
            fetch_alerts(),
            fetch_routing(),
            fetch_air_quality(),
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

        if routes is None or routing_err is not None:
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

        # 2. Concurrently evaluate traffic and hazards for candidate routes
        async def evaluate_single_candidate(route):
            # A. Traffic evaluation (reuse existing if present)
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

            # B. Corridor hazards query
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

            # C. Independent evaluation through decision engine
            return self.route_evaluator.evaluate_route(
                route=route,
                request=request,
                weather_timeline=comparison.primary_timeline,
                hazards=route_hazards,
                alerts=alerts,
                traffic=traffic,
                agreement_status=comparison.agreement_status.value,
                air_quality_timeline=aqi_timeline,
            )

        # Preserve deterministic route ordering with asyncio.gather
        evaluated_routes = list(await asyncio.gather(*[evaluate_single_candidate(r) for r in routes]))

        # 4. Deterministic selection & ranking
        selected_route, ranked_routes = self.route_evaluator.select_and_rank_routes(
            evaluated_routes,
            departure_time=request.departure_time,
            arrival_deadline=request.arrival_deadline
        )

        # 5. Populate multi-mode options in a single pass using Decision Engine
        mode_options = []
        target_modes = [TransportMode.bike, TransportMode.car, TransportMode.metro]
        primary_norm_route = next((r for r in routes if r.route_id == selected_route.route_id), routes[0])

        for target_m in target_modes:
            if target_m == request.mode:
                mode_options.append(
                    ModeOption(
                        mode=request.mode,
                        estimated_duration=selected_route.static_duration,
                        risk=selected_route.risk,
                        distance_km=selected_route.distance_km,
                        recommendation=selected_route.evaluation.recommendation_headline,
                        highlights=[f"{f.name}: {f.description}" for f in selected_route.risk.factors] if selected_route.risk else [],
                    )
                )
            elif target_m == TransportMode.metro:
                if metro_routes and len(metro_routes) > 0:
                    try:
                        metro_req = TripRequest(
                            origin=request.origin,
                            destination=request.destination,
                            departure_time=request.departure_time,
                            mode=TransportMode.metro,
                        )
                        eval_metro = self.route_evaluator.evaluate_route(
                            route=metro_routes[0],
                            request=metro_req,
                            weather_timeline=comparison.primary_timeline,
                            hazards=selected_route.hazards,
                            alerts=alerts,
                            traffic=None,
                            agreement_status=comparison.agreement_status.value,
                            air_quality_timeline=aqi_timeline,
                        )
                        mode_options.append(
                            ModeOption(
                                mode=TransportMode.metro,
                                estimated_duration=eval_metro.static_duration,
                                risk=eval_metro.risk,
                                distance_km=eval_metro.distance_km,
                                recommendation=eval_metro.evaluation.recommendation_headline,
                                highlights=[f"{f.name}: {f.description}" for f in eval_metro.risk.factors] if eval_metro.risk else [],
                            )
                        )
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).warning(f"Metro mode evaluation failed: {e}")
            else:  # bike or car
                base_road = primary_norm_route if request.mode != TransportMode.metro else (road_routes[0] if road_routes else None)
                if base_road:
                    try:
                        adapted_road = _adapt_normalized_route(base_road, target_m)
                        road_req = TripRequest(
                            origin=request.origin,
                            destination=request.destination,
                            departure_time=request.departure_time,
                            mode=target_m,
                        )
                        traffic_for_mode = selected_route.traffic if target_m == TransportMode.car else None
                        eval_road = self.route_evaluator.evaluate_route(
                            route=adapted_road,
                            request=road_req,
                            weather_timeline=comparison.primary_timeline,
                            hazards=selected_route.hazards,
                            alerts=alerts,
                            traffic=traffic_for_mode,
                            agreement_status=comparison.agreement_status.value,
                            air_quality_timeline=aqi_timeline,
                        )
                        mode_options.append(
                            ModeOption(
                                mode=target_m,
                                estimated_duration=eval_road.static_duration,
                                risk=eval_road.risk,
                                distance_km=eval_road.distance_km,
                                recommendation=eval_road.evaluation.recommendation_headline,
                                highlights=[f"{f.name}: {f.description}" for f in eval_road.risk.factors] if eval_road.risk else [],
                            )
                        )
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).warning(f"Road mode evaluation failed for {target_m}: {e}")

        mode_order = {TransportMode.bike: 0, TransportMode.car: 1, TransportMode.metro: 2}
        mode_options.sort(key=lambda opt: mode_order.get(opt.mode, 99))
        sources = [
            DataSource(name=self.weather_provider.provider_name, type="Weather (Primary)", last_updated=datetime.now(timezone.utc)),
            DataSource(name=routing_provider_name, type=f"Routing [{routing_status}]", last_updated=datetime.now(timezone.utc)),
            DataSource(name=self.alert_provider.provider_name, type=f"Alerts [{self.alert_provider.provider_class.value}]", last_updated=datetime.now(timezone.utc)),
        ]

        if selected_route.traffic:
            traffic = selected_route.traffic
            traffic_status_str = traffic.status.value if hasattr(traffic.status, "value") else str(traffic.status)
            sources.append(DataSource(name=traffic.source_name, type=f"Traffic [{traffic_status_str}]", last_updated=traffic.timestamp))

        # Build Air Quality Snapshot & Provenance
        air_quality_snapshot = None
        if aqi_timeline:
            dep_utc = request.departure_time if request.departure_time.tzinfo else request.departure_time.replace(tzinfo=timezone.utc)
            rep_pt = min(aqi_timeline, key=lambda pt: abs((pt.time - dep_utc).total_seconds()))
            air_quality_snapshot = AirQualitySnapshot(
                aqi=rep_pt.aqi,
                pm2_5=rep_pt.pm2_5,
                pm10=rep_pt.pm10,
                category=rep_pt.category,
                source_name=rep_pt.source_name,
                is_available=True,
                is_stale=rep_pt.is_stale,
                observation_time=rep_pt.observation_time,
                provenance="live_provider",
            )
            sources.append(DataSource(name=rep_pt.source_name, type="Air Quality [CAMS]", last_updated=datetime.now(timezone.utc)))
        elif self.air_quality_provider:
            # Truthful degraded representation when provider fails or returns empty
            air_quality_snapshot = AirQualitySnapshot(
                aqi=0,
                pm2_5=0.0,
                pm10=0.0,
                category="Unavailable",
                source_name=self.air_quality_provider.provider_name,
                is_available=False,
                is_stale=False,
                observation_time=None,
                provenance="degraded",
            )

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
            routes=ranked_routes,
            air_quality=air_quality_snapshot,
            geocoding_provenance=geocoding_provenance,
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
