import httpx
import logging
from datetime import timedelta
from typing import List

from app.core.config import settings
from app.providers.routing.base import RoutingProvider
from app.models.enums import TransportMode, RouteStatus
from app.decision_engine.normalized_models import NormalizedRoute, NormalizedRouteSegment
from app.providers.routing.errors import (
    RoutingError, ConfigurationError, UnsupportedModeError, NoRouteFoundError,
    ProviderRateLimitError, ProviderTimeoutError, MalformedResponseError
)

logger = logging.getLogger(__name__)

class GoogleRoutesProvider(RoutingProvider):
    API_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
    
    # Define mapping from our internal modes to Google Routes travel modes
    MODE_MAPPING = {
        TransportMode.bike: "TWO_WHEELER",
        TransportMode.car: "DRIVE",
        TransportMode.walk: "WALK",
    }
    
    FIELD_MASK = "routes.distanceMeters,routes.duration,routes.polyline.encodedPolyline,routes.legs.distanceMeters,routes.legs.duration,routes.legs.steps.distanceMeters,routes.legs.steps.duration,routes.legs.steps.startLocation,routes.legs.steps.endLocation,routes.legs.steps.polyline.encodedPolyline"

    def __init__(self):
        self._last_status = RouteStatus.live
        
    @property
    def provider_name(self) -> str:
        return "Google Routes API"
        
    @property
    def route_status(self) -> RouteStatus:
        return self._last_status

    def _get_api_key(self) -> str:
        api_key = settings.google_maps_api_key
        if not api_key:
            raise ConfigurationError("GOOGLE_MAPS_API_KEY is not configured in the environment.")
        return api_key

    async def get_route(self, origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float, mode: TransportMode) -> List[NormalizedRoute]:
        if mode == TransportMode.metro:
            raise UnsupportedModeError("Google Routes API does not support our required public transit metro routes.")
            
        if mode not in self.MODE_MAPPING:
            raise UnsupportedModeError(f"Transport mode {mode} is not mapped for Google Routes API.")

        api_key = self._get_api_key()
        travel_mode = self.MODE_MAPPING[mode]
        
        request_body = self._build_request(origin_lat, origin_lng, dest_lat, dest_lng, travel_mode)
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": self.FIELD_MASK
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.API_URL, json=request_body, headers=headers)
                
                if response.status_code == 429:
                    raise ProviderRateLimitError("Google Routes API rate limit exceeded.")
                elif response.status_code >= 500:
                    # In a real system, we might retry here. For now, we raise a transient error.
                    raise RoutingError(f"Transient Google API error: {response.status_code}")
                elif response.status_code >= 400:
                    raise RoutingError(f"Google API client error {response.status_code}: {response.text}")
                    
                data = response.json()
                
        except httpx.TimeoutException:
            raise ProviderTimeoutError("Request to Google Routes API timed out.")
        except httpx.RequestError as e:
            raise RoutingError(f"HTTP error communicating with Google Routes API: {e}")
            
        if not data.get("routes"):
            raise NoRouteFoundError("Google Routes API returned no routes.")
            
        return self._parse_response(data)

    def _build_request(self, origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float, travel_mode: str) -> dict:
        return {
            "origin": {
                "location": {
                    "latLng": {
                        "latitude": origin_lat,
                        "longitude": origin_lng
                    }
                }
            },
            "destination": {
                "location": {
                    "latLng": {
                        "latitude": dest_lat,
                        "longitude": dest_lng
                    }
                }
            },
            "travelMode": travel_mode,
            "computeAlternativeRoutes": True
        }

    def _parse_duration(self, duration_str: str) -> timedelta:
        # Google returns duration as "345s"
        try:
            seconds = int(duration_str.rstrip("s"))
            return timedelta(seconds=seconds)
        except (ValueError, TypeError):
            return timedelta(seconds=0)

    def _parse_response(self, data: dict) -> List[NormalizedRoute]:
        normalized_routes = []
        try:
            for route_data in data.get("routes", []):
                total_distance_km = route_data.get("distanceMeters", 0) / 1000.0
                total_duration = self._parse_duration(route_data.get("duration", "0s"))
                
                segments = []
                for leg in route_data.get("legs", []):
                    for step in leg.get("steps", []):
                        start_loc = step.get("startLocation", {}).get("latLng", {})
                        end_loc = step.get("endLocation", {}).get("latLng", {})
                        
                        start_lat = start_loc.get("latitude", 0.0)
                        start_lng = start_loc.get("longitude", 0.0)
                        end_lat = end_loc.get("latitude", 0.0)
                        end_lng = end_loc.get("longitude", 0.0)
                        
                        step_dist = step.get("distanceMeters", 0) / 1000.0
                        step_dur = self._parse_duration(step.get("duration", "0s"))
                        
                        segments.append(NormalizedRouteSegment(
                            start_lat=start_lat,
                            start_lng=start_lng,
                            end_lat=end_lat,
                            end_lng=end_lng,
                            distance_km=step_dist,
                            estimated_duration=step_dur,
                            traffic_congestion_factor=1.0 # default for MVP without live traffic
                        ))
                
                normalized_routes.append(NormalizedRoute(
                    segments=segments,
                    total_distance_km=total_distance_km,
                    total_duration=total_duration
                ))
            return normalized_routes
        except Exception as e:
            raise MalformedResponseError(f"Failed to parse Google Routes API response: {e}")
