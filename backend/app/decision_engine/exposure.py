from app.models.enums import TransportMode

def get_mode_exposure_multiplier(mode: TransportMode) -> float:
    """
    Returns the exposure multiplier for a given transport mode.
    
    ENGINEERING ASSUMPTIONS (MVP):
    These multipliers are conceptual heuristics, not scientifically calibrated constants.
    - bike: 1.0 (baseline, fully exposed)
    - car: 0.4 (protected but affected by traffic/waterlogging)
    - metro: 0.15 (highly protected)
    - walk: 1.1 (fully exposed + physical exertion)
    
    FUTURE SCALING:
    This model should be extended to explicitly account for:
    - Last-mile walking exposure for public transit
    - Station/platform exposure
    - Transit disruptions (e.g. metro flooding)
    Do not assume any mode is universally risk-free.
    """
    if mode == TransportMode.bike:
        return 1.0
    elif mode == TransportMode.car:
        return 0.4
    elif mode == TransportMode.metro:
        return 0.15
    elif mode == TransportMode.walk:
        return 1.1
    return 1.0
