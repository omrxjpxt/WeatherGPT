import math
from typing import List

# Earth radius in kilometers (Engineering Assumption for MVP)
EARTH_RADIUS_KM = 6371.0

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on the earth in km.
    """
    # Convert latitude and longitude from degrees to radians
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_KM * c

def point_to_segment_distance_km(pt_lat: float, pt_lng: float, seg_start_lat: float, seg_start_lng: float, seg_end_lat: float, seg_end_lng: float) -> float:
    """
    Lightweight approximation for minimum distance from a point to a geographic line segment.
    Uses equirectangular projection for local planar approximation.
    This is an MVP engineering assumption, accurate enough for short route segments (< 10km).
    """
    # Convert to radians
    lat_p, lng_p = math.radians(pt_lat), math.radians(pt_lng)
    lat_a, lng_a = math.radians(seg_start_lat), math.radians(seg_start_lng)
    lat_b, lng_b = math.radians(seg_end_lat), math.radians(seg_end_lng)
    
    # Average latitude for longitude scaling (equirectangular projection)
    avg_lat = (lat_a + lat_b) / 2.0
    
    # Convert to local Cartesian coordinates centered at start point A
    x_a, y_a = 0.0, 0.0
    x_b = (lng_b - lng_a) * math.cos(avg_lat)
    y_b = lat_b - lat_a
    x_p = (lng_p - lng_a) * math.cos(avg_lat)
    y_p = lat_p - lat_a
    
    # Vector AB
    dx_ab = x_b - x_a
    dy_ab = y_b - y_a
    
    len_sq_ab = dx_ab**2 + dy_ab**2
    
    if len_sq_ab == 0.0:
        # Start and end points are the same
        # Return haversine distance to start point
        return haversine_distance(pt_lat, pt_lng, seg_start_lat, seg_start_lng)
        
    # Project vector AP onto vector AB
    t = ((x_p - x_a) * dx_ab + (y_p - y_a) * dy_ab) / len_sq_ab
    
    # Clamp t to [0, 1] to restrict to segment
    t_clamped = max(0.0, min(1.0, t))
    
    # Find closest point on segment in local coordinates
    x_closest = x_a + t_clamped * dx_ab
    y_closest = y_a + t_clamped * dy_ab
    
    # Convert local closest point back to geographic coordinates
    lng_closest = lng_a + (x_closest / math.cos(avg_lat))
    lat_closest = lat_a + y_closest
    
    return haversine_distance(
        pt_lat, pt_lng,
        math.degrees(lat_closest), math.degrees(lng_closest)
    )

def point_in_polygon(lat: float, lng: float, polygon: List[List[float]]) -> bool:
    """
    Determines if a point is inside a geographic polygon using Ray Casting.
    Polygon is a list of [lat, lng] pairs.
    """
    n = len(polygon)
    if n < 3:
        return False
        
    inside = False
    
    p1x, p1y = polygon[0][1], polygon[0][0] # lng, lat
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n][1], polygon[i % n][0]
        
        # Ray casting horizontally
        if lng > min(p1x, p2x):
            if lng <= max(p1x, p2x):
                if lat <= max(p1y, p2y):
                    if p1x != p2x:
                        xints = (lng - p1x) * (p2y - p1y) / (p2x - p1x) + p1y
                    if p1x == p2x or lat <= xints:
                        inside = not inside
        p1x, p1y = p2x, p2y
        
    return inside
