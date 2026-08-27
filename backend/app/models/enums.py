from enum import Enum

class TransportMode(str, Enum):
    bike = "bike"
    car = "car"
    metro = "metro"
    walk = "walk"

class RiskLevel(str, Enum):
    low = "low"
    moderate = "moderate"
    high = "high"
    severe = "severe"

class HazardType(str, Enum):
    waterlogging = "waterlogging"
    fog = "fog"
    heavyRain = "heavyRain"
    storm = "storm"
    heatwave = "heatwave"
    construction = "construction"

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
