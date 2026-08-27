import logging
from typing import List

from app.providers.routing.base import RoutingProvider
from app.models.enums import TransportMode, RouteStatus
from app.decision_engine.normalized_models import NormalizedRoute
from app.providers.routing.errors import RoutingError

logger = logging.getLogger(__name__)

class FallbackRoutingProvider(RoutingProvider):
    """
    Tries the primary routing provider. If it fails, checks for cached routes (not implemented).
    If no cached route is available, returns an unavailable status rather than silently falling back to a mock.
    """
    def __init__(self, primary: RoutingProvider):
        self.primary = primary
        self._last_status = RouteStatus.unavailable
        self._last_provider_name = primary.provider_name

    @property
    def provider_name(self) -> str:
        return self._last_provider_name
        
    @property
    def route_status(self) -> RouteStatus:
        return self._last_status

    async def get_route(self, origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float, mode: TransportMode) -> List[NormalizedRoute]:
        self._last_provider_name = self.primary.provider_name
        
        try:
            routes = await self.primary.get_route(origin_lat, origin_lng, dest_lat, dest_lng, mode)
            self._last_status = self.primary.route_status
            return routes
        except RoutingError as e:
            logger.error(f"Primary routing provider ({self.primary.provider_name}) failed: {e}")
            # Cache check would go here. Since we don't have caching for this milestone:
            logger.info("No cached route available. Route is unavailable.")
            self._last_status = RouteStatus.unavailable
            raise e
        except Exception as e:
            logger.error(f"Unexpected error in primary routing provider ({self.primary.provider_name}): {e}")
            self._last_status = RouteStatus.unavailable
            raise RoutingError(f"Unexpected error: {e}") from e
