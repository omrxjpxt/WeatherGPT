# Decision Engine

The WeatherGPT Decision Engine is a pure, deterministic, side-effect-free module. Identical normalized inputs always produce identical risk scores, recommendations, and alert overrides.

## Hazard vs. Exposure
Risk calculation explicitly separates:
- **Hazard Severity**: Environmental conditions (e.g., precipitation rate, poor visibility).
- **Route Exposure**: The intersection of the geographic route with known localized hazards (e.g., a specific waterlogged underpass).
- **Temporal Exposure**: The duration spent in the hazard zone.
- **User Exposure (Mode)**: The degree to which the user's transport mode protects them (Bike = 1.0, Car = 0.4, Metro = 0.15).

## Route / Time Alignment
The engine maps the user's route segments to a weather timeline based on estimated segment durations. While arrival times are estimated using standard durations, the architecture allows for future ETA uncertainty representations.

## Official Alert Override
The engine deterministically overrides normal risk calculation if an official alert meets three conditions:
1. **Severity Criteria**: The alert is a warning or emergency requiring action.
2. **Temporal Match**: The alert's validity period overlaps the user's travel window.
3. **Spatial Match**: The alert's affected area geometry intersects the user's route.

## Uncertainty Terminology
Uncertainty is treated as a data/recommendation quality assessment rather than a statistically calibrated probability. The engine exposes `High`, `Moderate`, or `Low` confidence based on data source freshness and forecast horizon.
