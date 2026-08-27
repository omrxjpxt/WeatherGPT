from app.models.enums import TransportMode

def get_mode_exposure_multiplier(mode: TransportMode) -> float:
    """
    Returns the exposure multiplier for a given transport mode.
    
    Assumptions:
    - bike: 1.0 (fully exposed to elements)
    - car: 0.4 (protected from rain/wind, but affected by traffic/waterlogging)
    - metro: 0.15 (minimal exposure, only last-mile/station access)
    - walk: 1.1 (fully exposed + longer duration + exertion)
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
