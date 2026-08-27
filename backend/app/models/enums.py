from enum import Enum

class TransportMode(str, Enum):
    bike = "bike"
    car = "car"
    metro = "metro"
    walk = "walk"

class TripStatus(str, Enum):
    success = "success"
    routing_unavailable = "routing_unavailable"
    weather_unavailable = "weather_unavailable"
    degraded = "degraded"

class RiskLevel(str, Enum):
    low = "low"
    moderate = "moderate"
    high = "high"
    severe = "severe"

class HazardType(str, Enum):
    waterlogging = "waterlogging"
    visibility = "visibility"
    wind = "wind"
    heat = "heat"

class HazardSourceClass(str, Enum):
    authoritative = "authoritative"
    government_open_data = "government_open_data"
    secondary = "secondary"
    demo = "demo"

class AlertSeverity(str, Enum):
    advisory = "advisory"
    watch = "watch"
    warning = "warning"
    emergency = "emergency"

class ConfidenceLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    veryHigh = "veryHigh"

class RecommendationAction(str, Enum):
    go = "go"
    go_with_caution = "go_with_caution"
    leave_earlier = "leave_earlier"
    change_route = "change_route"
    change_mode = "change_mode"
    delay = "delay"
    avoid = "avoid"

class RouteStatus(str, Enum):
    live = "live"
    cached = "cached"
    mock = "mock"
    unavailable = "unavailable"

class AlertSourceClass(str, Enum):
    authoritative = "authoritative"
    secondary = "secondary"
    demo = "demo"
