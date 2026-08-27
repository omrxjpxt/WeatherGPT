# Decision Engine

The WeatherGPT Decision Engine is a pure, deterministic, side-effect-free module. Identical normalized inputs always produce identical risk scores, recommendations, and alert overrides.

## Hazard vs. Exposure
Risk calculation explicitly separates:
- **Hazard Severity**: Environmental conditions (e.g., precipitation rate, poor visibility).
- **Route Exposure**: The intersection of the geographic route with known localized hazards using a lightweight spatial proximity check.
- **Temporal Exposure**: The duration spent in the hazard zone.
- **User Exposure (Mode)**: The degree to which the user's transport mode protects them. 

> [!NOTE]
> **Engineering Assumption:** Mode multipliers (Bike = 1.0, Car = 0.4, Metro = 0.15, Walk = 1.1) are MVP heuristics, not scientifically calibrated constants. Future iterations will explicitly model last-mile walking, station exposure, and transit disruption.

## Overall Risk Aggregation
The overall trip risk is an aggregation of two components:
1. **Bottleneck Risk**: The maximum risk score of any single segment.
2. **Exposure Risk**: The time-weighted average risk across all segments.

> [!NOTE]
> **Configurable Parameters:** 
> - `BOTTLENECK_WEIGHT` (MVP Default: 0.6)
> - `EXPOSURE_WEIGHT` (MVP Default: 0.4)
>
> **Engineering Assumption:** A severe short bottleneck shouldn't be averaged away. A hard guardrail ensures that if the bottleneck is "Severe", the overall score remains "Severe" regardless of the exposure weight.

## Spatial Matching (Hazards & Alerts)

### Hazard Proximity
> [!NOTE]
> **Engineering Assumption:** Minimum distance from a hazard point to a route segment is calculated using a lightweight planar approximation (equirectangular projection) followed by a geographic Haversine check. This is an MVP approximation for short segments (<10km) assuming a spherical earth (`EARTH_RADIUS_KM=6371.0`).
>
> **Configurable Parameter:** `HAZARD_PROXIMITY_RADIUS_KM` (MVP Default: 2.0km).

### Official Alert Override
The engine deterministically overrides normal risk calculation if an official alert meets three conditions:
1. **Severity Criteria**: The alert is a warning or emergency requiring action.
2. **Temporal Match**: The alert's validity period overlaps the user's travel window.
3. **Spatial Match**: The alert's geometry matches the route.

> [!NOTE]
> **MVP Limitation:** If an alert lacks geometry (polygon), it is treated as a **Regional Match** (still applying the override if temporal bounds match), rather than an **Exact Route Match**.

## Route / Time Alignment
The engine maps the user's route segments to a weather timeline based on estimated segment durations. 

> [!NOTE]
> **MVP Limitation (Forecast-bucket alignment):** The system snaps segment arrival times to the nearest available forecast bucket. This does NOT imply exact weather certainty at every timestamp.

## Uncertainty Terminology
Uncertainty is a qualitative data/recommendation quality assessment rather than a statistically calibrated probability. The engine exposes `high`, `medium`, or `low` confidence based on data source freshness, forecast horizon, and source corroboration.

## 6. Local Hazard Intelligence
The engine calculates relevance for curated historical hazards. A hazard is only relevant if it matches temporally, spatially, and is triggered by the weather.

### Relevance Logic:
1. **Spatial Proximity:** The minimum distance from the hazard point to the route segment must be `<= radius_meters / 1000.0` km.
2. **Weather Trigger:** The expected weather at the segment's passage time must meet `trigger_precipitation_mm` OR `trigger_condition`.
3. **Temporal Match:** Implicitly met because the weather condition used for the trigger is taken at the aligned passage time.

### Hazard Contribution:
Active hazards contribute to the segment risk using the formula:
`contribution = base_severity * hazard_influence_factor`

Where `hazard_influence_factor` is a configurable engineering assumption (default 0.5) designed to scale historical susceptibility into a current trip penalty.

---

## 7. Configuration & Tuningsibility Scoring

> **Engineering Assumption:** Open-Meteo returns hourly accumulation in `mm`. We use `precipitation_mm` as a proxy for intensity, scoring risk as a linear scalar `3.0 * precipitation_mm`, capped at 100. This is isolated and ready to be replaced with a scientifically supported threshold-based intensity model in the future.

> **Visibility:** The engine uses explicit `visibility` (meters) returned by the provider. If `visibility < 1000m`, a moderate risk penalty is applied.
