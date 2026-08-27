from typing import List, Optional, Tuple
from datetime import datetime
from app.decision_engine.normalized_models import NormalizedAlert, NormalizedRoute
from app.models.enums import AlertSeverity
from app.decision_engine.spatial import point_in_polygon

def check_alert_override(
    alerts: List[NormalizedAlert],
    route: NormalizedRoute,
    travel_start: datetime,
    travel_end: datetime
) -> Tuple[Optional[NormalizedAlert], bool]:
    """
    Deterministic spatial AND temporal matching for alert overrides.
    Filters by severity, checks temporal overlap, checks spatial applicability.
    Ranks applicable alerts by severity, returns the strongest.
    Tie-breaking: most recently issued wins.
    Returns: (alert, is_exact_match)
    """
    applicable_alerts = []
    
    for alert in alerts:
        # 1. Check severity/actionability criteria
        if alert.severity not in [AlertSeverity.warning, AlertSeverity.emergency] or not alert.requires_override:
            continue
            
        # 2. Temporal match (validity overlaps travel window)
        starts_before_end = alert.issued_at <= travel_end
        expires_after_start = alert.expires_at is None or alert.expires_at >= travel_start
        if not (starts_before_end and expires_after_start):
            continue
            
        # 3. Spatial match
        is_exact = _route_intersects_alert(route, alert)
        
        # We consider both exact and regional matches (regional = no geometry provided)
        # But we track if it was an exact route intersection.
        if is_exact or not alert.affected_areas_polygon or len(alert.affected_areas_polygon) < 3:
            applicable_alerts.append((alert, is_exact))
            
    if not applicable_alerts:
        return None, False
        
    # Rank by severity (emergency > warning), then by issued_at (newest first)
    def sort_key(item: Tuple[NormalizedAlert, bool]):
        alert, _ = item
        severity_score = 2 if alert.severity == AlertSeverity.emergency else 1
        return (severity_score, alert.issued_at)
        
    applicable_alerts.sort(key=sort_key, reverse=True)
    
    return applicable_alerts[0]

def _route_intersects_alert(route: NormalizedRoute, alert: NormalizedAlert) -> bool:
    """
    Checks if any segment start or end point is strictly inside the alert polygon.
    Only returns True if we have valid geometry and an exact spatial match occurs.
    """
    if not alert.affected_areas_polygon or len(alert.affected_areas_polygon) < 3:
        return False # No exact geometry available
        
    for seg in route.segments:
        if point_in_polygon(seg.start_lat, seg.start_lng, alert.affected_areas_polygon):
            return True
        if point_in_polygon(seg.end_lat, seg.end_lng, alert.affected_areas_polygon):
            return True
            
    return False
