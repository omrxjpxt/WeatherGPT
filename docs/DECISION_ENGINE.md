# Decision Engine

The WeatherGPT Decision Engine is a pure, deterministic, side-effect-free module. Identical normalized inputs always produce identical risk scores, recommendations, and alert overrides.

## Base Environmental Weights & Mathematical Formulations

The segment environmental risk model uses normalized weights summing to 1.00:
- **Precipitation ($P_{\text{eff}}$)**: Weight **0.35**
- **Visibility ($V$)**: Weight **0.20**
- **Hazard Contribution ($H$)**: Weight **0.30**
- **Air Quality Index ($A$)**: Weight **0.15**
- **Total Base Weights**: $0.35 + 0.20 + 0.30 + 0.15 = 1.00$

### Mathematical Formulations:
1. **Precipitation Probability Scaling**:
   $$P_{\text{eff}} = \text{precipitation\_mm} \times \max(0.20, \text{probability} / 100)$$
   If precipitation probability is $< 20\%$, the precipitation intensity score is bounded to $\le 10$ to prevent drizzle false alarms.
2. **Air Quality Index (AQI) Piecewise Linear Interpolation**:
   Calculated from $PM_{2.5}$ concentration using US EPA 7-breakpoint linear interpolation on a 0–500 scale.
3. **AQI Mode Exposure**:
   Applied to AQI risk contribution according to cabin/vehicle protection:
   - Bike / Walk: $1.0\times$
   - Car: $0.15\times$
   - Metro: $0.10\times$
4. **Temporal Exposure Multiplier**:
   $$M_{\text{temp}} = \min(2.0, \max(0.5, \text{segment\_duration\_minutes} / 10.0))$$
   Scales risk contribution between $0.5\times$ and $2.0\times$ based on dwell time in the segment.
5. **Overall Route Risk Aggregation**:
   $$\text{Route Risk} = 0.60 \times \text{Bottleneck} + 0.40 \times \text{Exposure}$$
   *Guardrail:* If Bottleneck risk score is $\ge 75$ (Severe), the overall route risk score is clamped to $\ge 75$.
6. **Scenario Simulation Single-Pass Architecture**:
   To prevent $13\times$ N+1 external API call explosions during multi-departure scenario simulations, `TripService.resolve_corridor_context` fetches geocoding, corridor weather forecasts, routing polyline, active alerts, and hazards once in a single corridor pass. The 13 departure scenarios are then evaluated entirely in-memory against the resolved corridor timeline.

## Hazard vs. Exposure
Risk calculation explicitly separates:
- **Hazard Severity**: Environmental conditions (e.g., precipitation rate, poor visibility).
- **Route Exposure**: The intersection of the geographic route with known localized hazards using a lightweight spatial proximity check.
- **Temporal Exposure**: The duration spent in the hazard zone.
- **User Exposure (Mode)**: The degree to which the user's transport mode protects them. 

> [!NOTE]
> **Engineering Assumption:** Mode multipliers (Bike = 1.0, Car = 0.4, Metro = 0.15, Walk = 1.1) are MVP heuristics, not scientifically calibrated constants.

## Overall Risk Aggregation
The overall trip risk is an aggregation of two components:
1. **Bottleneck Risk**: The maximum risk score of any single segment.
2. **Exposure Risk**: The time-weighted average risk across all segments.

> [!NOTE]
> **Configurable Parameters:** 
> - `BOTTLENECK_WEIGHT` (Default: 0.6)
> - `EXPOSURE_WEIGHT` (Default: 0.4)
>
> **Engineering Assumption:** A severe short bottleneck shouldn't be averaged away. A hard guardrail ensures that if the bottleneck is "Severe" ($\ge 75$), the overall score remains "Severe" regardless of the exposure weight.

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

---

## 8. Route Alternative Evaluation & Deterministic Selection Policy

The Route Alternative Evaluation engine evaluates all alternatives returned by the routing provider using the same deterministic decision engine (`DecisionEngine.evaluate_route_core`), avoiding heuristic fragmentation or duplicated scoring models.

### Strict 6-Step Deterministic Selection Ordering

Route alternatives are filtered, compared, and selected through an unambiguous, non-overlapping 6-step policy:

1. **Arrival Deadline Filtering (Feasibility)**:
   - Evaluates whether `departure_time + traffic_aware_duration <= arrival_deadline`.
   - Routes violating `arrival_deadline` are marked `is_feasible = False` with an explicit `feasibility_reason`.
   - If at least one route is feasible, infeasible routes are excluded from the active candidate pool.
   - **All-Infeasible Fallback**: If *all* available routes violate the deadline, all routes are retained in the candidate pool with `is_feasible = False` rather than failing outright.

2. **Alert Policy Differentiation (Hard Avoidance vs. Advisory)**:
   - **Advisory / Warning Alerts**: General weather advisories and warnings inform raw risk scores and risk tiers without automatically disqualifying routes.
   - **Hard Avoidance / Closures**: Applies strictly when an authoritative alert meets emergency severity or explicitly mandates avoidance, evacuation, halt, or closure (`is_hard_alert_avoidance`).
   - If non-closure routes exist, routes covered by hard avoidance/closure orders are excluded from selection.
   - **Regional Emergency Fallback**: If *all* routes face active emergency closure/avoidance, all routes are retained and marked with regional emergency warnings.

3. **Risk Tier Comparison**:
   - Compares risk levels hierarchically: `Low (1) < Moderate (2) < High (3) < Severe (4)`.
   - If risk tiers differ, the route in the strictly lower risk tier is selected.

4. **Same Risk Tier — Large Score Difference ($\ge 15$ points)**:
   - If candidate routes occupy the same risk tier and $|\text{risk}_A - \text{risk}_B| \ge 15$, the route with the lower raw risk score is selected.

5. **Same Risk Tier — Small Score Difference ($< 15$ points)**:
   - If candidate routes occupy the same risk tier and $|\text{risk}_A - \text{risk}_B| < 15$, the system optimizes for traveler utility: the route with the shorter `traffic_aware_duration` (effective travel time) is selected.
   - *Example*: Route A (22m static + 12m traffic = 34m, risk 42) vs. Route B (27m static + 2m traffic = 29m, risk 45). Both are Moderate tier, $|\Delta\text{risk}| = 3 < 15$. Route B is selected because travel time is 5 minutes faster (29m vs 34m).

6. **Deterministic Tie-Breaking**:
   - a. Lower exposure score.
   - b. Shorter total distance (`distance_km`).
   - c. Lexicographical comparison of `route_id` for absolute reproducibility.

### Separation of Backend Recommendation and Frontend Inspection
- **Backend `selectedRouteId`**: The deterministic route recommendation computed via the 6-step policy (`is_selected = True`).
- **Frontend `activeRouteId`**: The route currently viewed/inspected by the user in Flutter. Tapping an alternative route updates `activeRouteId` for map/segment inspection but strictly never mutates `is_selected` or the backend recommendation.

