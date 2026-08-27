/// WeatherGPT Domain Models
/// These represent the structured decision objects from the future backend.
/// Flutter consumes these — it does NOT compute risk or weather logic.

// ── Enums ──

enum TransportMode { bike, car, metro, walk }

enum RiskLevel { low, moderate, high, severe }

enum HazardType { waterlogging, fog, heavyRain, storm, heatwave, construction }

enum AlertSeverity { advisory, watch, warning, emergency }

enum ConfidenceLevel { low, medium, high, veryHigh }

// ── Core Models ──

class TripRequest {
  final String origin;
  final String destination;
  final DateTime departureTime;
  final TransportMode mode;

  const TripRequest({
    required this.origin,
    required this.destination,
    required this.departureTime,
    required this.mode,
  });

  TripRequest copyWith({
    String? origin,
    String? destination,
    DateTime? departureTime,
    TransportMode? mode,
  }) {
    return TripRequest(
      origin: origin ?? this.origin,
      destination: destination ?? this.destination,
      departureTime: departureTime ?? this.departureTime,
      mode: mode ?? this.mode,
    );
  }
}

class TripResponse {
  final TripRequest request;
  final RiskAssessment risk;
  final List<RouteSegment> route;
  final Recommendation recommendation;
  final List<ModeOption> modeOptions;
  final List<Hazard> hazards;
  final List<DataSource> sources;
  final Duration estimatedDuration;
  final double distanceKm;

  const TripResponse({
    required this.request,
    required this.risk,
    required this.route,
    required this.recommendation,
    required this.modeOptions,
    required this.hazards,
    required this.sources,
    required this.estimatedDuration,
    required this.distanceKm,
  });
}

class RiskAssessment {
  final int overallScore; // 0-100
  final RiskLevel level;
  final Confidence confidence;
  final List<RiskFactor> factors;
  final String summary;

  const RiskAssessment({
    required this.overallScore,
    required this.level,
    required this.confidence,
    required this.factors,
    required this.summary,
  });
}

class RiskFactor {
  final String name;
  final String description;
  final int score; // 0-100
  final RiskLevel level;
  final double weight;

  const RiskFactor({
    required this.name,
    required this.description,
    required this.score,
    required this.level,
    required this.weight,
  });
}

class RouteSegment {
  final double startLat;
  final double startLng;
  final double endLat;
  final double endLng;
  final RiskLevel riskLevel;
  final String? description;
  final WeatherPoint? weather;

  const RouteSegment({
    required this.startLat,
    required this.startLng,
    required this.endLat,
    required this.endLng,
    required this.riskLevel,
    this.description,
    this.weather,
  });
}

class WeatherPoint {
  final DateTime time;
  final double temperature; // Celsius
  final double precipitation; // mm/hr
  final int humidity; // percentage
  final double windSpeed; // km/h
  final String condition; // "Heavy Rain", "Cloudy", etc.
  final String icon;

  const WeatherPoint({
    required this.time,
    required this.temperature,
    required this.precipitation,
    required this.humidity,
    required this.windSpeed,
    required this.condition,
    required this.icon,
  });
}

class Hazard {
  final String id;
  final HazardType type;
  final String title;
  final String description;
  final double lat;
  final double lng;
  final RiskLevel severity;
  final DateTime? reportedAt;
  final String? source;

  const Hazard({
    required this.id,
    required this.type,
    required this.title,
    required this.description,
    required this.lat,
    required this.lng,
    required this.severity,
    this.reportedAt,
    this.source,
  });
}

class OfficialAlert {
  final String id;
  final String title;
  final String description;
  final AlertSeverity severity;
  final String issuedBy;
  final DateTime issuedAt;
  final DateTime? expiresAt;
  final List<String> affectedAreas;
  final String? actionRequired;
  final String? source;

  const OfficialAlert({
    required this.id,
    required this.title,
    required this.description,
    required this.severity,
    required this.issuedBy,
    required this.issuedAt,
    this.expiresAt,
    required this.affectedAreas,
    this.actionRequired,
    this.source,
  });
}

class ModeOption {
  final TransportMode mode;
  final Duration estimatedDuration;
  final RiskAssessment risk;
  final double distanceKm;
  final String? recommendation;
  final List<String> highlights;

  const ModeOption({
    required this.mode,
    required this.estimatedDuration,
    required this.risk,
    required this.distanceKm,
    this.recommendation,
    required this.highlights,
  });
}

class ScenarioResult {
  final DateTime departureTime;
  final RiskAssessment risk;
  final Duration estimatedDuration;
  final String recommendation;
  final List<RiskFactor> changedFactors;

  const ScenarioResult({
    required this.departureTime,
    required this.risk,
    required this.estimatedDuration,
    required this.recommendation,
    required this.changedFactors,
  });
}

class Confidence {
  final ConfidenceLevel level;
  final int percentage; // 0-100
  final String explanation;

  const Confidence({
    required this.level,
    required this.percentage,
    required this.explanation,
  });
}

class Recommendation {
  final String headline;
  final String body;
  final String? alternativeAction;
  final TransportMode? suggestedMode;
  final DateTime? suggestedDepartureTime;

  const Recommendation({
    required this.headline,
    required this.body,
    this.alternativeAction,
    this.suggestedMode,
    this.suggestedDepartureTime,
  });
}

class DataSource {
  final String name;
  final String type; // "IMD", "NDMA", "Traffic API", etc.
  final DateTime lastUpdated;

  const DataSource({
    required this.name,
    required this.type,
    required this.lastUpdated,
  });
}

class HistoricalEvent {
  final DateTime date;
  final String title;
  final String description;
  final RiskLevel severity;
  final List<String> impacts;
  final List<WeatherPoint> weatherTimeline;

  const HistoricalEvent({
    required this.date,
    required this.title,
    required this.description,
    required this.severity,
    required this.impacts,
    required this.weatherTimeline,
  });
}
