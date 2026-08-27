# Official Alert Provider Comparison (2026)

This document evaluates the authoritative Indian weather-alert data sources suitable for WeatherGPT, specifically in the context of a Smart India Hackathon (SIH) prototype.

## 1. Authoritative Official Source: IMD API / NDMA SACHET (CAP 1.2) [UNAVAILABLE]

The India Meteorological Department (IMD) and the National Disaster Management Authority (NDMA) SACHET portal provide the official Common Alerting Protocol (CAP) 1.2 alerts for India. 
We do not make unsupported claims about direct IMD access. Direct IMD API access is currently unavailable for our backend due to IP whitelisting constraints.

1. **Availability of machine-readable data**: Yes, standard CAP 1.2 XML and JSON.
2. **API/feed format**: REST API (IMD) and RSS feeds linking to XML (SACHET).
3. **Authentication requirements**: IMD official API requires formal registration, approval from a Nodal Officer, and strict IP whitelisting. SACHET RSS is public.
4. **Geographic representation**: Primarily administrative regions (District/Taluka/State blocks). Specific hazards like cyclones may include polygons.
5. **Alert severity levels**: Standard CAP parameters (Extreme, Severe, Moderate, Minor) mapped to color codes (Red, Orange, Yellow).
6. **Issue time**: Explicitly defined (`onset`).
7. **Start/end validity**: Explicitly defined (`effective` and `expires`).
8. **Alert source/provenance**: Fully traceable to specific agencies (IMD, CWC, INCOIS, SDMAs).
9. **Update frequency**: Near real-time.
10. **India coverage**: 100% comprehensive, national standard.
11. **Reliability**: Highest (authoritative government source).
12. **Licensing/usage constraints**: Free for public good, but API access is administratively gated.
13. **Feasibility for a student SIH prototype**: **Low.** The IP whitelisting requirement blocks dynamic cloud deployments (like Vercel/Render) without static IPs, and the approval process is too slow for a hackathon timeline. SACHET RSS scraping is possible but prone to breaking and lacks a direct spatial-query API.
14. **Whether route-level spatial matching is possible**: Difficult. Requires maintaining a complex offline database mapping Indian district names/geofences to coordinate bounding boxes.
15. **Whether the source can support our existing alert override model**: Yes, standard CAP severity fields perfectly map to deterministic overrides.

## 2. Secondary Source: Commercial Aggregator (e.g., WeatherAPI / OpenWeather) [PLANNED]

Commercial APIs aggregate official warnings from national agencies (including IMD) and expose them through unified developer-friendly JSON APIs.

1. **Availability of machine-readable data**: Yes.
2. **API/feed format**: JSON REST API.
3. **Authentication requirements**: Standard API Key (Free tiers available).
4. **Geographic representation**: Point-based spatial querying (you query a Lat/Lng, and it returns alerts intersecting that point).
5. **Alert severity levels**: Mapped to standard scales, though sometimes reliant on free-form text depending on the upstream source.
6. **Issue time**: Yes.
7. **Start/end validity**: Yes.
8. **Alert source/provenance**: Preserved (identifies IMD as the original issuer).
9. **Update frequency**: High (pulled from upstream).
10. **India coverage**: Good, relies on IMD upstream ingestion.
11. **Reliability**: High, though slight latency compared to direct IMD feeds.
12. **Licensing/usage constraints**: Free tier quota limits apply.
13. **Feasibility for a student SIH prototype**: **Very High.** Instant API key provisioning, standard JSON, no IP whitelisting.
14. **Whether route-level spatial matching is possible**: Yes. We can query the API using the Lat/Lng of our route segments to see if that segment intersects an active warning zone.
15. **Whether the source can support our existing alert override model**: Yes, severity and urgency can be mapped to our internal override schema.

## 3. Fallback/Demo Source: MockAlertProvider [DEMO]

Our existing internal mock provider for development.

1. **Feasibility**: 100% feasible for offline demos and testing the Decision Engine.
2. **Spatial matching**: Hardcoded bounding boxes.
3. **Usage**: Essential for the final SIH presentation if live APIs fail or there is no severe weather on demo day.

---

## Recommendations

### Primary Alert Source (For SIH Prototype)
**WeatherAPI (Alerts Endpoint) / Secondary Aggregator**
*Why?* While IMD is the true authoritative source, their strict IP whitelisting and bureaucratic access model make a direct API integration unfeasible for a rapid student hackathon prototype. A commercial aggregator like WeatherAPI effectively proxies IMD alerts while providing a point-based spatial query JSON API that works instantly out of the box. We will clearly document in the SIH presentation that the *production* architecture would use the official IMD CAP feed, while the *prototype* uses a commercial proxy for demonstration.

### Fallback Alert Source
**MockAlertProvider**
Must remain available to force severe weather alerts during the SIH judge evaluation, as live weather cannot be guaranteed to be severe during the presentation.

### Exact Fields We Need to Normalize
When mapping the provider response to our `NormalizedAlert` contract, we must extract:
1. `id`: Unique identifier for deduplication.
2. `source`: Provenance (e.g., "IMD via WeatherAPI").
3. `event`: The hazard type (e.g., "Heavy Rain", "Cyclone").
4. `severity`: Normalized to `extreme`, `severe`, `moderate`, or `minor`.
5. `description`: Actionable advice.
6. `effective_time` / `expires_time`: For temporal alignment with the trip duration.
7. `polygon` / `bounding_box`: If provided (otherwise assumed to intersect the queried point).

### Important Limitations
- The secondary aggregator may have up to a 1-hour propagation delay from the official IMD issuance.
- Point-based API querying means we have to make multiple API calls (one per major route waypoint) to check an entire 200km route, which eats into rate limits.

### Required Credentials/Configuration
- `WEATHER_API_KEY`: A standard API key for the chosen secondary aggregator.
- `ALERT_PROVIDER`: Config toggle (`weatherapi`, `mock`).
