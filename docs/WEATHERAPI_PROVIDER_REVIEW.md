# WeatherAPI Provider Review (2026)

## 1. Provider Classification
**Classification: SECONDARY**

WeatherAPI aggregates weather data and alerts from various global sources, including national agencies. However, it is a commercial aggregator, not an official government entity. Because it lacks a strict, structured guarantee of origin for every alert (e.g., an explicit `issuing_agency_type` boolean), it must be strictly classified as a `SECONDARY` alert provider according to WeatherGPT's policy. It cannot be legally or technically presented to users as direct, unmediated communication from the India Meteorological Department (IMD) unless the alert's unstructured metadata explicitly specifies IMD.

## 2. API Capabilities

### Current Weather & Forecast API
WeatherAPI provides robust current weather and forecast APIs (up to 14 days). The endpoint `/v1/forecast.json` can return both hourly weather and alerts in a single HTTP request by appending the `alerts=yes` parameter, making it highly efficient.

### Weather Alerts API
Alerts are returned inside an `alerts` object in the standard JSON response.

**Key Fields Present:**
- **Severity**: Yes (`severity` field - e.g., "Moderate", "Severe").
- **Alert Times**: Yes (`effective` and `expires` fields in ISO 8601 format).
- **Event**: Yes (`event` field - e.g., "Flood Warning").
- **Description & Instructions**: Yes (`desc` and `instruction` fields).

**Key Fields Missing or Unstructured:**
- **Source/Authority Metadata**: The API does not provide a dedicated `source_agency` field. The issuing authority is often appended to the end of the `headline` string (e.g., `"... by NWS"` or `"... by IMD"`).
- **Machine-Readable Geometry**: The API **does not** return alert polygons or bounding boxes. It returns a comma/semicolon-separated string of administrative `areas`.
- **Geographic Representation**: You query a specific point (latitude/longitude), and the API returns alerts for the administrative region encompassing that point. This means we cannot determine the exact spatial boundaries of the alert.

## 3. Operations & Constraints

- **API Authentication**: Simple API key passed as a query parameter (`?key=YOUR_API_KEY`).
- **Free-Plan Limits**: WeatherAPI offers a generous free tier (typically 1 million calls per month).
- **Rate Limits**: Sufficient for a hackathon prototype, but point-based spatial querying means a 500km route might require multiple API calls to check for alerts along the polyline.
- **Licensing/Usage**: Standard commercial terms. Attribution to WeatherAPI is required on the free tier.

## 4. IMD Provenance
**Can alert data legitimately be described as originating from IMD?**
Only conditionally. We cannot blanket-label all WeatherAPI alerts as "IMD Alerts". The system must parse the `headline` or `desc` string to check for "IMD" or "India Meteorological Department". If found, we can display "IMD via WeatherAPI". If not found, it must simply be attributed to "WeatherAPI".

## 5. Integration Summary

### Exact Capabilities
- Single API call for hourly forecast and active alerts.
- Standardized severity and timing fields.

### Required Fields for Normalization
To map to our `NormalizedAlert`:
- `id`: Must be generated (e.g., hash of headline + effective time) as WeatherAPI does not provide a unique alert ID.
- `sourceName`: Parsed from `headline`, defaulting to `"WeatherAPI"`.
- `sourceClass`: Strictly `AlertSourceClass.secondary`.
- `severity`: Map WeatherAPI's severity to our `AlertSeverity` enum.
- `affectedAreasPolygon`: Must remain empty/null (regional match only).
- `issuedAt`: Mapped from `effective`.
- `expiresAt`: Mapped from `expires`.
- `action`: Mapped from `instruction`.

### API Credentials Required
- `WEATHERAPI_KEY`: standard string.

### Suitable for SIH Prototype?
**Yes.** It provides realistic, real-time alert structures without the IP-whitelisting bottlenecks of the official IMD API. It serves perfectly to demonstrate the WeatherGPT alert override pipeline.

### Recommended Integration Scope
We should implement `WeatherApiAlertProvider` extending the `AlertProvider` interface. It will execute point queries. Because it lacks geometry, any alert it returns will trigger a "regional match" in our Decision Engine. By design, our policy evaluator will strip these secondary alerts of their override eligibility unless we specifically write a parser that promotes them to `authoritative` if "IMD" is explicitly found in the headline text (this promotion logic should be carefully scoped).

### Reasons NOT to integrate
The primary drawback is the lack of explicit geometry (polygons). Without polygons, we cannot demonstrate the precise geographic intersection logic (e.g., "The route grazes the edge of the alert polygon"). However, given the lack of alternatives for an SIH timeline, it remains the best option.
