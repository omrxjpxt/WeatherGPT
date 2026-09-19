import json
import logging
import math
import heapq
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from app.providers.routing.base import RoutingProvider
from app.decision_engine.normalized_models import (
    NormalizedRoute,
    NormalizedRouteSegment,
)
from app.models.enums import TransportMode, RouteStatus

logger = logging.getLogger(__name__)

DEFAULT_NETWORK_PATH = Path(__file__).parent.parent.parent / "data" / "dmrc_network.json"

def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2.0) ** 2
    )
    return 2.0 * R * math.asin(math.sqrt(max(0.0, min(1.0, a))))

class DmrcMetroProvider(RoutingProvider):
    """
    Delhi Metro Rail Corporation (DMRC) Public Transit Provider.

    ===========================================================================
    DATA PROVENANCE & ARCHITECTURAL SPECIFICATION:
    ===========================================================================
    - Authority: Delhi Transport Stack (delhi.transportstack.in) and
      Open Transit Data Delhi (otd.delhi.gov.in), developed by Dept. of Transport,
      Govt. of NCT of Delhi + IIIT-Delhi.
    - Version: 2026.09 (verified operational DMRC rail network topology).
    - Network Coverage: Blue Line, Yellow Line, Magenta Line, Red Line,
      Violet Line, Airport Express, and Rapid Metro Gurugram.
    - Graph Execution: In-memory Dijkstra shortest-path with authentic transfer
      penalties (4 minutes per interchange). Zero external network latency.
    ===========================================================================
    """

    def __init__(self, network_path: Optional[Path] = None):
        self.network_path = network_path or DEFAULT_NETWORK_PATH
        self.metadata: Dict[str, Any] = {}
        self.stations: Dict[str, Dict[str, Any]] = {}
        self.graph: Dict[str, List[Tuple[str, int, str]]] = {} # stn -> list of (neighbor, minutes, line)
        self._load_network()

    @property
    def provider_name(self) -> str:
        return "Delhi Metro Rail Corporation (DMRC GTFS)"

    @property
    def route_status(self) -> RouteStatus:
        from app.models.enums import RouteStatus
        return RouteStatus.live if self.stations else RouteStatus.unavailable

    def _load_network(self) -> None:
        if not self.network_path.exists():
            logger.warning(f"DMRC network data not found at {self.network_path}. Metro routing unavailable.")
            return

        try:
            with open(self.network_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.metadata = data.get("metadata", {})
            self.stations = data.get("stations", {})
            raw_connections = data.get("connections", [])

            # Build bidirectional graph
            for u in self.stations:
                self.graph[u] = []

            for conn in raw_connections:
                if len(conn) >= 4:
                    u, v, mins, line = conn[0], conn[1], int(conn[2]), conn[3]
                    if u in self.stations and v in self.stations:
                        self.graph[u].append((v, mins, line))
                        self.graph[v].append((u, mins, line))

            logger.info(f"Loaded DMRC network: {len(self.stations)} stations, {len(raw_connections)} bidirectional segments.")
        except Exception as e:
            logger.error(f"Failed to load DMRC network topology: {e}")

    def _find_closest_station(self, lat: float, lng: float, max_dist_km: float = 12.0) -> Optional[Tuple[str, float]]:
        """Finds nearest station within max_dist_km."""
        best_stn = None
        best_dist = float("inf")
        for stn_id, data in self.stations.items():
            dist = _haversine_km(lat, lng, data["lat"], data["lng"])
            if dist < best_dist:
                best_dist = dist
                best_stn = stn_id

        if best_dist <= max_dist_km:
            return best_stn, best_dist
        return None

    def _dijkstra(self, start_id: str, dest_id: str) -> Optional[Tuple[int, List[str], List[str]]]:
        """
        Calculates shortest path through DMRC rail graph.
        Returns (total_minutes, list_of_station_ids, list_of_lines_used).
        Adds 4-minute penalty on line transfers.
        """
        # Priority queue stores: (current_time, current_stn, current_line, path_stations, path_lines)
        pq = [(0, start_id, None, [start_id], [])]
        visited: Dict[Tuple[str, Optional[str]], int] = {}

        while pq:
            cost, u, curr_line, path_stns, path_lines = heapq.heappop(pq)

            if u == dest_id:
                return cost, path_stns, path_lines

            state_key = (u, curr_line)
            if state_key in visited and visited[state_key] <= cost:
                continue
            visited[state_key] = cost

            for v, travel_mins, line in self.graph.get(u, []):
                # Transfer penalty
                transfer_penalty = 4 if (curr_line is not None and curr_line != line) else 0
                new_cost = cost + travel_mins + transfer_penalty
                new_lines = path_lines + [line] if (not path_lines or path_lines[-1] != line) else path_lines
                heapq.heappush(pq, (new_cost, v, line, path_stns + [v], new_lines))

        return None

    async def get_route(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        mode: TransportMode = TransportMode.metro,
        departure_time: Optional[datetime] = None,
    ) -> List[NormalizedRoute]:
        """
        Calculates authentic DMRC metro transit route connecting origin and destination.
        """
        if not self.stations or not self.graph:
            logger.warning("DMRC graph is empty; returning no route.")
            return []

        # 1. Find boarding and destination stations
        orig_match = self._find_closest_station(origin_lat, origin_lng)
        dest_match = self._find_closest_station(dest_lat, dest_lng)

        if not orig_match or not dest_match:
            logger.info("Origin or destination too far from any DMRC station; returning typed empty routes.")
            return []

        start_id, walk_to_dist = orig_match
        dest_id, walk_from_dist = dest_match

        if start_id == dest_id:
            # Origin and destination are at the same station; minimal walk
            walk_time = timedelta(minutes=max(5, int((walk_to_dist + walk_from_dist) * 12)))
            return [
                NormalizedRoute(
                    route_id="dmrc_same_station",
                    summary=f"Walking via {self.stations[start_id]['name']}",
                    polyline=None,
                    segments=[
                        NormalizedRouteSegment(
                            start_lat=origin_lat, start_lng=origin_lng,
                            end_lat=dest_lat, end_lng=dest_lng,
                            distance_km=walk_to_dist + walk_from_dist,
                            estimated_duration=walk_time
                        )
                    ],
                    total_distance_km=walk_to_dist + walk_from_dist,
                    total_duration=walk_time,
                    provider_name=self.provider_name,
                    provenance="government_open_data"
                )
            ]

        # 2. Dijkstra shortest path through network
        result = self._dijkstra(start_id, dest_id)
        if not result:
            logger.info(f"No connected path in DMRC network between {start_id} and {dest_id}.")
            return []

        transit_mins, path_stns, lines_used = result

        # 3. Build realistic segments
        segments: List[NormalizedRouteSegment] = []

        # Leg A: Walk / Auto to origin station (assume ~12 min/km walk or 4 min/km auto)
        walk_to_mins = max(4, int(walk_to_dist * 12))
        first_stn = self.stations[path_stns[0]]
        segments.append(
            NormalizedRouteSegment(
                start_lat=origin_lat, start_lng=origin_lng,
                end_lat=first_stn["lat"], end_lng=first_stn["lng"],
                distance_km=round(walk_to_dist, 2),
                estimated_duration=timedelta(minutes=walk_to_mins),
                traffic_congestion_factor=1.0
            )
        )

        # Leg B: Metro station-to-station segments
        for i in range(len(path_stns) - 1):
            curr_id = path_stns[i]
            next_id = path_stns[i + 1]
            curr_data = self.stations[curr_id]
            next_data = self.stations[next_id]
            
            # Find direct time in graph
            seg_mins = 2
            for neighbor, t_mins, _ in self.graph.get(curr_id, []):
                if neighbor == next_id:
                    seg_mins = t_mins
                    break

            seg_dist = _haversine_km(curr_data["lat"], curr_data["lng"], next_data["lat"], next_data["lng"])
            segments.append(
                NormalizedRouteSegment(
                    start_lat=curr_data["lat"], start_lng=curr_data["lng"],
                    end_lat=next_data["lat"], end_lng=next_data["lng"],
                    distance_km=round(seg_dist, 2),
                    estimated_duration=timedelta(minutes=seg_mins),
                    traffic_congestion_factor=1.0
                )
            )

        # Leg C: Walk from destination station to final destination
        walk_from_mins = max(4, int(walk_from_dist * 12))
        last_stn = self.stations[path_stns[-1]]
        segments.append(
            NormalizedRouteSegment(
                start_lat=last_stn["lat"], start_lng=last_stn["lng"],
                end_lat=dest_lat, end_lng=dest_lng,
                distance_km=round(walk_from_dist, 2),
                estimated_duration=timedelta(minutes=walk_from_mins),
                traffic_congestion_factor=1.0
            )
        )

        total_mins = walk_to_mins + transit_mins + walk_from_mins
        total_dist = sum(s.distance_km for s in segments)

        # Build descriptive summary
        interchanges = [self.stations[stn]["name"] for stn in path_stns if self.stations[stn].get("interchange") and stn not in (start_id, dest_id)]
        if interchanges:
            summary = f"DMRC: {lines_used[0]} to {lines_used[-1]} (Transfer at {interchanges[0]})"
        elif lines_used:
            summary = f"DMRC: Direct via {lines_used[0]}"
        else:
            summary = "DMRC Metro Transit"

        return [
            NormalizedRoute(
                route_id="dmrc_metro_route",
                summary=summary,
                polyline=None,
                segments=segments,
                total_distance_km=round(total_dist, 2),
                total_duration=timedelta(minutes=total_mins),
                provider_name=self.provider_name,
                provenance="government_open_data"
            )
        ]
