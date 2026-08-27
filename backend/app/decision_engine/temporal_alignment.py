from typing import List, Tuple
from datetime import datetime
from app.decision_engine.normalized_models import NormalizedRoute, NormalizedWeatherPoint, NormalizedRouteSegment

def align_route_with_weather(
    route: NormalizedRoute,
    departure_time: datetime,
    weather_timeline: List[NormalizedWeatherPoint]
) -> List[Tuple[NormalizedRouteSegment, datetime, NormalizedWeatherPoint]]:
    """
    Given a route and departure time, estimates when the user reaches each segment.
    Associates the relevant weather data with each segment and time.
    
    MVP ENGINEERING ASSUMPTION (Forecast-bucket alignment):
    Currently uses nearest-weather-point logic. This matches segment arrival time
    to the nearest available forecast bucket in the timeline.
    
    LIMITATION:
    This does NOT imply exact weather certainty at every timestamp. 
    It is an approximation of expected conditions. Future versions may interpolate 
    between buckets or use probabilistic bands.
    
    Architected so future ETA uncertainty can be represented (currently using exact estimated_duration).
    """
    aligned_segments = []
    current_time = departure_time
    
    for segment in route.segments:
        # The arrival time for THIS segment is roughly the time we start it.
        # In a more advanced model, we'd use a probability distribution of arrival times.
        segment_arrival_time = current_time
        
        # Find the closest weather point in the timeline
        closest_weather = _get_closest_weather(segment_arrival_time, weather_timeline)
        
        aligned_segments.append((segment, segment_arrival_time, closest_weather))
        
        # Advance time by the estimated duration of this segment
        current_time += segment.estimated_duration
        
    return aligned_segments

def _get_closest_weather(target_time: datetime, timeline: List[NormalizedWeatherPoint]) -> NormalizedWeatherPoint:
    if not timeline:
        raise ValueError("Weather timeline cannot be empty")
        
    # Find the weather point with the minimum absolute time difference
    return min(timeline, key=lambda wp: abs((wp.time - target_time).total_seconds()))
