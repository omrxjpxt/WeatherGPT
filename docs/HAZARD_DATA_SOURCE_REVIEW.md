# Local Hazard Data Source Review (India)

This document evaluates the machine-readable data sources for localized weather-sensitive hazards (waterlogging, flood-prone locations, landslide zones) relevant to WeatherGPT in the context of a Smart India Hackathon (SIH) prototype.

## 1. Authoritative / Live Sources

### Google Flood Forecasting API (Flood Hub)
- **Source Authority**: High (Google Research in partnership with CWC).
- **Geographic Precision**: River basin and floodplain level.
- **Coordinates available?**: Yes.
- **Geometry**: Polygons (inundation maps) and Points (gauge stations).
- **Historical vs Live**: Live and predictive (up to 7 days).
- **Update Frequency**: Daily/Hourly depending on river stage.
- **Coverage**: Major Indian river basins; **lacks urban flash-flood / street-level waterlogging**.
- **API Availability**: Yes, restricted API access (often requires whitelisting).
- **Authentication**: API Key.
- **Licensing/Constraints**: Commercial/Restricted.
- **Suitability for SIH**: Low. It solves riverine flooding, not the urban routing/waterlogging problem critical to WeatherGPT's core use case.
- **Route Association**: Possible via polygon intersection, but too broad for street routing.
- **Honest Representation**: "Google Flood Hub".

### TomTom / Mapbox Incident APIs
- **Source Authority**: Secondary/Commercial Aggregator.
- **Geographic Precision**: Street-level.
- **Coordinates available?**: Yes.
- **Geometry**: Lines (route segments) and Points (incidents).
- **Historical vs Live**: Live.
- **Update Frequency**: Real-time.
- **Coverage**: Major Indian cities.
- **API Availability**: Yes (REST APIs).
- **Authentication**: API Key.
- **Licensing/Constraints**: Standard commercial free tiers.
- **Suitability for SIH**: Moderate. Provides real-time road closures, but does not always distinguish *why* a road is closed (accident vs waterlogging) reliably in India.
- **Route Association**: Excellent.
- **Honest Representation**: "TomTom Live Traffic/Incidents".

## 2. Government / Open-Data (Static/Historical)

### Bhuvan (ISRO) Flood Hazard Zonation
- **Source Authority**: Highest (ISRO/NDMA).
- **Geographic Precision**: State/District/Block level.
- **Coordinates available?**: Yes, via GIS formats.
- **Geometry**: Polygons.
- **Historical vs Live**: Historical susceptibility (static atlas).
- **Coverage**: Pan-India.
- **API Availability**: WMS/WFS (Web Map Services). Difficult to query purely via JSON REST for a specific route point.
- **Suitability for SIH**: Low for dynamic routing. WMS is meant for map rendering, not fast deterministic route-risk calculation.

### Municipal Data (data.gov.in / BMC / MCD CSVs)
- **Source Authority**: Official Municipal Corporations.
- **Geographic Precision**: Street/Landmark level (e.g., "Minto Bridge", "Hindmata").
- **Coordinates available?**: Often missing; requires manual geocoding from text addresses.
- **Geometry**: Points (once geocoded).
- **Historical vs Live**: Static historical lists of known waterlogging spots.
- **API Availability**: Mostly static CSV/PDF downloads. No live JSON API.
- **Suitability for SIH**: High, **if manually curated**. It represents ground truth for urban waterlogging hotspots.

## 3. Curated / Demo (SIH Prototype Standard)

### WeatherGPT Curated Hotspots Database (Firestore/Local JSON)
Because no unified, live, machine-readable API exists for exact street-level urban waterlogging in India, the most honest and technically sound approach for the SIH prototype is to curate a database of historically known hotspots derived from official municipal lists.

- **Source Authority**: Derived from official municipal vulnerability lists.
- **Geographic Precision**: Exact coordinates (Points) of underpasses and low-lying areas.
- **Coordinates available?**: Yes.
- **Geometry**: Point + Radius.
- **Historical vs Live**: Historical susceptibility, activated dynamically by live weather (e.g., if heavy rain is forecast over a known hotspot, it becomes an active hazard).
- **Suitability for SIH**: **Very High**. It allows deterministic testing, proves the geographic intersection logic, and solves the exact problem statements outlined in SIH without faking a live government feed.

---

## Recommendations & Integration Strategy

### 1. Primary Hazard Source
**Curated Historical Hotspots (Database)**
- We will maintain a geospatial database (JSON/Firestore) of known waterlogging and landslide hotspots (e.g., specific underpasses in Delhi/Mumbai).
- **Trigger Logic:** A hotspot is *dormant* by default. The Decision Engine activates the hazard ONLY IF the live weather provider (Open-Meteo) forecasts precipitation exceeding a certain threshold at that specific location.

### 2. Fallback
None required, as the curated dataset is highly available (bundled or Firestore).

### 3. MVP Geographic Scope
Delhi NCR and Mumbai (to demonstrate urban waterlogging).

### 4. Fields Required for `NormalizedHazard`
To accurately associate hazards with routes, the model requires:
- `id`: Unique identifier.
- `type`: `HazardType.waterlogging`, `landslide`, etc.
- `lat` / `lng`: Exact coordinates.
- `radius_meters`: The area of effect (e.g., 200m).
- `activation_threshold_mm`: The rainfall intensity required to trigger this hazard.
- `base_severity`: The danger level when triggered.
- `source`: E.g., "Delhi MCD Historical Data".

### 5. Honest Representation in UI/Provenance
- Do not claim this is a "Live Flood API".
- Represent it as: **"Historical Vulnerability triggered by Live Forecast"**.
- UI should show: "Known waterlogging hotspot ahead. High risk due to current heavy rainfall."

### 6. Limitations
This approach relies on static data for locations. It cannot predict temporary waterlogging caused by sudden drain blockages in normally safe areas. For a production system, this static database would be supplemented by crowdsourced reports or live traffic incident APIs.
