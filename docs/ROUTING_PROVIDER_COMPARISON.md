# Routing Provider Comparison (2026)

This document evaluates the leading routing providers against the specific requirements of the WeatherGPT project for the Smart India Hackathon (SIH) 2026. The goal is to select a provider that seamlessly integrates with our deterministic Decision Engine, offering high-quality geographic polylines, reliable segment durations, and ease of implementation.

## Evaluated Providers
1. **Google Routes API**
2. **Mapbox Directions API**
3. **HERE Routing API**
4. **OSRM (Open Source Routing Machine) / OpenStreetMap**

---

## 1. India Coverage
- **Google Routes**: Exceptional. The undisputed market leader for Indian roads, small gullies, and highly accurate Point of Interest (POI) data.
- **Mapbox**: Good, but relies on OpenStreetMap (OSM) data augmented by telemetry. Can occasionally lack granularity in rural Indian regions or new urban developments compared to Google.
- **HERE**: Very Strong. HERE has a massive footprint in India, especially tuned for logistics, enterprise fleets, and two-wheeler specific navigation.
- **OSRM / OSM**: Good for major roads but highly dependent on the open-source community. Often lacks accurate data for unpaved roads, temporary closures, or local Indian nuances.

## 2. Route Polyline Quality
- **Google Routes**: Provides high-resolution, smooth encoded polylines ideal for Flutter Map rendering and accurate geographic hazard raycasting.
- **Mapbox**: Excellent. Mapbox specializes in high-fidelity mapping and provides extremely detailed GeoJSON or encoded polylines.
- **HERE**: High quality, offering flexible line geometries (Flexible Polyline format).
- **OSRM**: Provides standard encoded polylines. Resolution is generally good, but snapping to exact road curves can sometimes be less precise than commercial APIs.

## 3. Per-Step / Segment Duration
*(Crucial for WeatherGPT's spatial-temporal forecast alignment)*
- **Google Routes**: Provides granular `duration` and `distance` fields for every individual "leg" and "step" of the route.
- **Mapbox**: Provides detailed `duration` metrics per step in the `legs` array.
- **HERE**: Extremely detailed segment-level temporal data.
- **OSRM**: Provides step-by-step duration, but typically static (based on speed limits) unless custom live traffic data is injected.

## 4. Alternative Routes
- **Google Routes**: Natively supports requesting up to 3 alternative routes with distinct polylines and ETAs.
- **Mapbox**: Supports requesting alternatives via the `alternatives=true` flag.
- **HERE**: Supports requesting alternative routes with configurable constraints.
- **OSRM**: Supports alternatives, but the algorithmic variance is sometimes minimal (routes may look nearly identical).

## 5. Traffic-Aware ETA
- **Google Routes**: The gold standard. Real-time, highly accurate predictive traffic algorithms in India.
- **Mapbox**: Good traffic awareness in major Indian metros, but less comprehensive than Google in tier-2/3 cities.
- **HERE**: Enterprise-grade real-time traffic, heavily relied upon by logistics.
- **OSRM**: **None natively.** The public API is static. Implementing live traffic requires self-hosting and building complex custom data ingestion pipelines.

## 6. API Quotas / Free Tier
- **Google Routes**: $200 monthly credit system has been replaced with per-SKU caps. Compute Routes typically offers ~10,000 free requests per month, after which pay-as-you-go applies.
- **Mapbox**: Extremely generous. Up to 100,000 free Directions API requests per month.
- **HERE**: Excellent "Freemium" tier. Historically up to 250,000 free transactions/month, making it highly attractive for hackathons and startups.
- **OSRM**: The public demo API is free but strictly prohibits production/heavy usage (severe rate-limiting).

## 7. Pricing (Post-Free Tier)
- **Google Routes**: ~$5.00 per 1,000 requests (Compute Routes Essentials). Can get expensive quickly at scale.
- **Mapbox**: ~$2.00 per 1,000 requests. Very cost-effective.
- **HERE**: Pay-as-you-grow, generally scales cheaper than Google for high transaction volumes.
- **OSRM**: Free to use (software), but requires paying for AWS/GCP cloud infrastructure to self-host properly.

## 8. Licensing
- **Google Routes**: Proprietary. Strict Terms of Service (cannot be used to build a competing mapping platform; must generally be displayed on a Google Map).
- **Mapbox**: Proprietary API over open data.
- **HERE**: Proprietary.
- **OSRM**: Open Source (BSD-2-Clause). Maximum freedom.

## 9. Flutter Compatibility
- **Google Routes**: Excellent. Robust community plugins (`google_maps_flutter`, `flutter_polyline_points`).
- **Mapbox**: Excellent. Strong official and community plugins (`mapbox_gl`).
- **HERE**: Offers the HERE SDK for Flutter, highly optimized but slightly steeper learning curve.
- **OSRM**: Easy. REST API returns standard JSON; polylines can be decoded using standard Dart packages and rendered on `flutter_map` (which we are currently using).

## 10. FastAPI/Python Integration
- **Google Routes**: Trivial. Google provides official Python client libraries or standard HTTP `httpx` integration.
- **Mapbox**: Trivial. Simple REST API, easy to consume with `httpx`.
- **HERE**: Trivial. REST API based.
- **OSRM**: Trivial. REST API.

## 11. Reliability
- **Google Routes**: 99.9% enterprise SLA.
- **Mapbox**: Highly reliable cloud infrastructure.
- **HERE**: Enterprise-grade stability.
- **OSRM (Public Demo)**: **Low.** The public server is best-effort, can go down anytime, and will throttle hackathon bursts. Self-hosted OSRM is highly reliable but requires DevOps effort.

## 12. Ease of Implementation for SIH Timeline
- **Google Routes**: High. Documentation is ubiquitous, and Dart/Python packages are mature.
- **Mapbox**: High. Very developer-friendly documentation.
- **HERE**: Moderate to High.
- **OSRM (Public)**: High (just a simple HTTP GET), but risky due to throttling.
- **OSRM (Self-Hosted)**: **Low.** Setting up Docker, downloading OSM India maps (`.pbf`), extracting, and running the server will burn valuable hackathon hours.

---

## Recommendation

### **Primary Provider: Mapbox Directions API**
**Why:**
1. **Generous Free Tier:** 100,000 requests/month is more than enough for development, testing, and the SIH finale without risking unexpected credit card charges.
2. **Flutter Map Compatibility:** We are currently using `flutter_map` (an OSM-based map). Google Maps strictly forbids using their Routes API data on non-Google maps. Mapbox data perfectly aligns with our current frontend mapping stack.
3. **Data Quality:** Provides high-fidelity polylines and detailed per-step durations required for our spatial-temporal weather engine.
4. **Implementation Speed:** Simple REST API is trivial to implement in FastAPI within hours.

**Expected Limitations:**
- Traffic data in rural India might be slightly less accurate than Google's.
- Complex Indian addresses (landmarks vs. street numbers) might occasionally fail geocoding, though this is primarily a geocoding issue, not a routing issue.

**Required Credentials:**
- `MAPBOX_ACCESS_TOKEN` (Create a free account at Mapbox.com and generate a public token).

### **Fallback Provider: OSRM (Public API)**
**Why:**
1. Zero authentication required.
2. Identical underlying OSM road data, ensuring visual consistency if Mapbox fails.
3. It serves as a perfect backup for a live demo if API quotas are accidentally exhausted.

**Expected Limitations:**
- No live traffic awareness.
- Strict rate limits (can fail if queried too fast).

**Required Credentials:**
- None. (HTTP GET to `http://router.project-osrm.org/route/v1/...`)
