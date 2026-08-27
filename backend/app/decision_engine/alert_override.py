from typing import List, Optional
from datetime import datetime
from app.decision_engine.normalized_models import NormalizedAlert, NormalizedRoute
from app.models.enums import AlertSeverity

def check_alert_override(
    alerts: List[NormalizedAlert],
    route: NormalizedRoute,
    travel_start: datetime,
    travel_end: datetime
) -> Optional[NormalizedAlert]:
    """
    Deterministic spatial AND temporal matching for alert overrides.
    Returns the overriding alert if one applies, else None.
    """
    for alert in alerts:
        # 1. Check severity/actionability criteria
        if alert.severity not in [AlertSeverity.warning, AlertSeverity.emergency] or not alert.requires_override:
            continue
            
        # 2. Temporal match (validity overlaps travel window)
        # Alert is valid if it starts before travel_end and (expires after travel_start or has no expiry)
        starts_before_end = alert.issued_at <= travel_end
        expires_after_start = alert.expires_at is None or alert.expires_at >= travel_start
        if not (starts_before_end and expires_after_start):
            continue
            
        # 3. Spatial match (alert geometry intersects route)
        # For MVP/mock, we assume the normalized alert polygon is a bounding box [lat, lng]
        # and we do a simple AABB check against the route's bounding box.
        if _route_intersects_alert(route, alert):
            return alert
            
    return None

def _route_intersects_alert(route: NormalizedRoute, alert: NormalizedAlert) -> bool:
    if not alert.affected_areas_polygon or len(alert.affected_areas_polygon) < 3:
        return True # Fallback if no polygon but passed temporal
        
    lats = [pt[0] for pt in alert.affected_areas_polygon]
    lngs = [pt[1] for pt in alert.affected_areas_polygon]
    min_alat, max_alat = min(lats), max(lats)
    min_alng, max_alng = min(lngs), max(lngs)
    
    for seg in route.segments:
        # Simple point-in-bbox check for start/end points
        if min_alat <= seg.start_lat <= max_alat and min_alng <= seg.start_lng <= max_alng:
            return True
        if min_alat <= seg.end_lat <= max_alat and min_alng <= seg.end_lng <= max_alng:
            return True
            
    return False
