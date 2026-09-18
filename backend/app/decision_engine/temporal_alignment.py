from typing import List, Tuple, Optional
from datetime import datetime, timedelta
from app.decision_engine.normalized_models import NormalizedRoute, NormalizedWeatherPoint, NormalizedRouteSegment
from app.models.traffic import TrafficSnapshot

def align_route_with_weather(
    route: NormalizedRoute,
    departure_time: datetime,
    weather_timeline: List[NormalizedWeatherPoint],
    traffic: Optional[TrafficSnapshot] = None
) -> List[Tuple[NormalizedRouteSegment, datetime, NormalizedWeatherPoint]]:
    """
    Given a route and departure time, estimates when the user reaches each segment.
    Associates the relevant weather data with each segment and time.
    
    If traffic is provided with delay, advances current_time accounting for traffic delay,
    implementing the temporal exposure shift effect.
    """
    aligned_segments = []
    current_time = departure_time
    
    traffic_segments = traffic.segments if (traffic and traffic.segments) else []
    
    for idx, segment in enumerate(route.segments):
        segment_arrival_time = current_time
        
        closest_weather = _get_closest_weather(segment_arrival_time, weather_timeline)
        aligned_segments.append((segment, segment_arrival_time, closest_weather))
        
        # Advance time: base static duration + segment traffic delay (if present)
        seg_delay_sec = 0.0
        if idx < len(traffic_segments):
            seg_delay_sec = max(0.0, traffic_segments[idx].delay_seconds)
        elif traffic and traffic.delay_seconds > 0 and len(route.segments) > 0:
            # Distribute evenly if segments array not populated
            seg_delay_sec = max(0.0, traffic.delay_seconds / len(route.segments))
            
        current_time += segment.estimated_duration + timedelta(seconds=seg_delay_sec)
        
    return aligned_segments

def _get_closest_weather(target_time: datetime, timeline: List[NormalizedWeatherPoint]) -> NormalizedWeatherPoint:
    if not timeline:
        raise ValueError("Weather timeline cannot be empty")
        
    # Find the weather point with the minimum absolute time difference
    return min(timeline, key=lambda wp: abs((wp.time - target_time).total_seconds()))
