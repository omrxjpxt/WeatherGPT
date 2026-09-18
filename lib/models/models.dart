/// WeatherGPT Domain Models
/// These represent the structured decision objects from the future backend.
/// Flutter consumes these — it does NOT compute risk or weather logic.
library;

// ── Enums ──

enum TransportMode { bike, car, metro, walk }

enum RiskLevel {
  low,
  moderate,
  high,
  severe;

  static RiskLevel fromString(String? value) {
    if (value == null) return RiskLevel.low;
    switch (value.toLowerCase()) {
      case 'severe':
        return RiskLevel.severe;
      case 'high':
        return RiskLevel.high;
      case 'moderate':
        return RiskLevel.moderate;
      case 'low':
      default:
        return RiskLevel.low;
    }
  }
}

enum HazardType { waterlogging, fog, heavyRain, storm, heatwave, construction, wind, heat, visibility }

enum AlertSeverity { advisory, watch, warning, emergency }

enum ConfidenceLevel { low, medium, high, veryHigh }

enum TripStatus {
  success,
  routingUnavailable,
  weatherUnavailable,
  degraded;

  static TripStatus fromString(String? value) {
    switch (value) {
      case 'routing_unavailable':
      case 'routingUnavailable':
        return TripStatus.routingUnavailable;
      case 'weather_unavailable':
      case 'weatherUnavailable':
        return TripStatus.weatherUnavailable;
      case 'degraded':
        return TripStatus.degraded;
      case 'success':
      default:
        return TripStatus.success;
    }
  }
}

enum CongestionLevel {
  unknown,
  freeFlow,
  moderate,
  heavy,
  severe;

  static CongestionLevel fromString(String? value) {
    switch (value) {
      case 'free_flow':
      case 'freeFlow':
        return CongestionLevel.freeFlow;
      case 'moderate':
        return CongestionLevel.moderate;
      case 'heavy':
        return CongestionLevel.heavy;
      case 'severe':
        return CongestionLevel.severe;
      case 'unknown':
      default:
        return CongestionLevel.unknown;
    }
  }
}

enum TrafficStatus {
  live,
  cached,
  mock,
  unavailable;

  static TrafficStatus fromString(String? value) {
    switch (value) {
      case 'live':
        return TrafficStatus.live;
      case 'cached':
        return TrafficStatus.cached;
      case 'mock':
        return TrafficStatus.mock;
      case 'unavailable':
      default:
        return TrafficStatus.unavailable;
    }
  }
}

enum TrafficCondition {
  clear,
  congested,
  stopAndGo,
  gridlock,
  unknown;

  static TrafficCondition fromString(String? value) {
    switch (value) {
      case 'clear':
        return TrafficCondition.clear;
      case 'congested':
        return TrafficCondition.congested;
      case 'stop_and_go':
      case 'stopAndGo':
        return TrafficCondition.stopAndGo;
      case 'gridlock':
        return TrafficCondition.gridlock;
      case 'unknown':
      default:
        return TrafficCondition.unknown;
    }
  }
}

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

  Map<String, dynamic> toJson() => {
        'origin': origin,
        'destination': destination,
        'departureTime': departureTime.toUtc().toIso8601String(),
        'mode': mode.name,
      };

  factory TripRequest.fromJson(Map<String, dynamic> json) => TripRequest(
        origin: json['origin'] as String,
        destination: json['destination'] as String,
        departureTime: DateTime.parse(json['departureTime'] as String).toLocal(),
        mode: TransportMode.values.firstWhere((e) => e.name == json['mode']),
      );
}

class TrafficSegment {
  final double startLat;
  final double startLng;
  final double endLat;
  final double endLng;
  final CongestionLevel congestionLevel;
  final double delaySeconds;
  final double? currentSpeedKmh;
  final double? freeFlowSpeedKmh;

  const TrafficSegment({
    required this.startLat,
    required this.startLng,
    required this.endLat,
    required this.endLng,
    this.congestionLevel = CongestionLevel.unknown,
    this.delaySeconds = 0.0,
    this.currentSpeedKmh,
    this.freeFlowSpeedKmh,
  });

  factory TrafficSegment.fromJson(Map<String, dynamic> json) => TrafficSegment(
        startLat: (json['startLat'] as num).toDouble(),
        startLng: (json['startLng'] as num).toDouble(),
        endLat: (json['endLat'] as num).toDouble(),
        endLng: (json['endLng'] as num).toDouble(),
        congestionLevel: CongestionLevel.fromString(json['congestionLevel'] as String?),
        delaySeconds: (json['delaySeconds'] as num?)?.toDouble() ?? 0.0,
        currentSpeedKmh: (json['currentSpeedKmh'] as num?)?.toDouble(),
        freeFlowSpeedKmh: (json['freeFlowSpeedKmh'] as num?)?.toDouble(),
      );

  Map<String, dynamic> toJson() => {
        'startLat': startLat,
        'startLng': startLng,
        'endLat': endLat,
        'endLng': endLng,
        'congestionLevel': congestionLevel.name,
        'delaySeconds': delaySeconds,
        'currentSpeedKmh': currentSpeedKmh,
        'freeFlowSpeedKmh': freeFlowSpeedKmh,
      };
}

class TrafficSnapshot {
  final TrafficStatus status;
  final TrafficCondition condition;
  final CongestionLevel congestionLevel;
  final double delaySeconds;
  final Duration staticDuration;
  final Duration trafficAwareDuration;
  final double? currentSpeedKmh;
  final double? freeFlowSpeedKmh;
  final List<TrafficSegment> segments;
  final DateTime timestamp;
  final String sourceName;
  final String provenance;

  const TrafficSnapshot({
    required this.status,
    required this.condition,
    required this.congestionLevel,
    required this.delaySeconds,
    required this.staticDuration,
    required this.trafficAwareDuration,
    this.currentSpeedKmh,
    this.freeFlowSpeedKmh,
    this.segments = const [],
    required this.timestamp,
    required this.sourceName,
    required this.provenance,
  });

  Duration get trafficDelay => Duration(seconds: delaySeconds.round());

  factory TrafficSnapshot.fromJson(Map<String, dynamic> json) => TrafficSnapshot(
        status: TrafficStatus.fromString(json['status'] as String?),
        condition: TrafficCondition.fromString(json['condition'] as String?),
        congestionLevel: CongestionLevel.fromString(json['congestionLevel'] as String?),
        delaySeconds: (json['delaySeconds'] as num?)?.toDouble() ?? 0.0,
        staticDuration: _parseDuration(json['staticDuration']?.toString() ?? '0'),
        trafficAwareDuration: _parseDuration(json['trafficAwareDuration']?.toString() ?? '0'),
        currentSpeedKmh: (json['currentSpeedKmh'] as num?)?.toDouble(),
        freeFlowSpeedKmh: (json['freeFlowSpeedKmh'] as num?)?.toDouble(),
        segments: (json['segments'] as List?)
                ?.map((e) => TrafficSegment.fromJson(e as Map<String, dynamic>))
                .toList() ??
            const [],
        timestamp: json['timestamp'] != null
            ? DateTime.parse(json['timestamp'] as String).toLocal()
            : DateTime.now(),
        sourceName: json['sourceName'] as String? ?? 'Traffic Provider',
        provenance: json['provenance'] as String? ?? 'unknown',
      );

  Map<String, dynamic> toJson() => {
        'status': status.name,
        'condition': condition.name,
        'congestionLevel': congestionLevel.name,
        'delaySeconds': delaySeconds,
        'staticDuration': staticDuration.inSeconds.toString(),
        'trafficAwareDuration': trafficAwareDuration.inSeconds.toString(),
        'currentSpeedKmh': currentSpeedKmh,
        'freeFlowSpeedKmh': freeFlowSpeedKmh,
        'segments': segments.map((e) => e.toJson()).toList(),
        'timestamp': timestamp.toUtc().toIso8601String(),
        'sourceName': sourceName,
        'provenance': provenance,
      };
}

class RouteEvaluation {
  final String routeId;
  final int riskScore;
  final RiskLevel riskLevel;
  final Duration staticDuration;
  final Duration trafficAwareDuration;
  final double trafficDelaySeconds;
  final double exposureScore;
  final int bottleneckScore;
  final int hazardCount;
  final bool isFeasible;
  final String? feasibilityReason;
  final String recommendationHeadline;
  final String recommendationBody;
  final String? suggestedMode;
  final DateTime? suggestedDepartureTime;
  final bool isSelected;
  final String? selectionReason;
  final String provenance;

  const RouteEvaluation({
    required this.routeId,
    required this.riskScore,
    required this.riskLevel,
    required this.staticDuration,
    required this.trafficAwareDuration,
    required this.trafficDelaySeconds,
    required this.exposureScore,
    required this.bottleneckScore,
    required this.hazardCount,
    this.isFeasible = true,
    this.feasibilityReason,
    required this.recommendationHeadline,
    required this.recommendationBody,
    this.suggestedMode,
    this.suggestedDepartureTime,
    this.isSelected = false,
    this.selectionReason,
    this.provenance = 'unknown',
  });

  factory RouteEvaluation.fromJson(Map<String, dynamic> json) => RouteEvaluation(
        routeId: json['routeId'] as String? ?? '',
        riskScore: (json['riskScore'] as num?)?.toInt() ?? 0,
        riskLevel: RiskLevel.fromString(json['riskLevel'] as String?),
        staticDuration: _parseDuration(json['staticDuration']?.toString() ?? '0'),
        trafficAwareDuration: _parseDuration(json['trafficAwareDuration']?.toString() ?? '0'),
        trafficDelaySeconds: (json['trafficDelaySeconds'] as num?)?.toDouble() ?? 0.0,
        exposureScore: (json['exposureScore'] as num?)?.toDouble() ?? 0.0,
        bottleneckScore: (json['bottleneckScore'] as num?)?.toInt() ?? 0,
        hazardCount: (json['hazardCount'] as num?)?.toInt() ?? 0,
        isFeasible: json['isFeasible'] as bool? ?? true,
        feasibilityReason: json['feasibilityReason'] as String?,
        recommendationHeadline: json['recommendationHeadline'] as String? ?? '',
        recommendationBody: json['recommendationBody'] as String? ?? '',
        suggestedMode: json['suggestedMode'] as String?,
        suggestedDepartureTime: json['suggestedDepartureTime'] != null
            ? DateTime.parse(json['suggestedDepartureTime'] as String).toLocal()
            : null,
        isSelected: json['isSelected'] as bool? ?? false,
        selectionReason: json['selectionReason'] as String?,
        provenance: json['provenance'] as String? ?? 'unknown',
      );

  Map<String, dynamic> toJson() => {
        'routeId': routeId,
        'riskScore': riskScore,
        'riskLevel': riskLevel.name,
        'staticDuration': staticDuration.inSeconds.toString(),
        'trafficAwareDuration': trafficAwareDuration.inSeconds.toString(),
        'trafficDelaySeconds': trafficDelaySeconds,
        'exposureScore': exposureScore,
        'bottleneckScore': bottleneckScore,
        'hazardCount': hazardCount,
        'isFeasible': isFeasible,
        'feasibilityReason': feasibilityReason,
        'recommendationHeadline': recommendationHeadline,
        'recommendationBody': recommendationBody,
        'suggestedMode': suggestedMode,
        'suggestedDepartureTime': suggestedDepartureTime?.toUtc().toIso8601String(),
        'isSelected': isSelected,
        'selectionReason': selectionReason,
        'provenance': provenance,
      };
}

class EvaluatedRoute {
  final String routeId;
  final String summary;
  final double distanceKm;
  final Duration staticDuration;
  final String? polyline;
  final List<RouteSegment> segments;
  final TrafficSnapshot? traffic;
  final RouteEvaluation evaluation;
  final List<Hazard> hazards;
  final String sourceName;
  final String provenance;
  final RiskAssessment? risk;

  const EvaluatedRoute({
    required this.routeId,
    required this.summary,
    required this.distanceKm,
    required this.staticDuration,
    this.polyline,
    this.segments = const [],
    this.traffic,
    required this.evaluation,
    this.hazards = const [],
    this.sourceName = 'Routing Provider',
    this.provenance = 'unknown',
    this.risk,
  });

  factory EvaluatedRoute.fromJson(Map<String, dynamic> json) => EvaluatedRoute(
        routeId: json['routeId'] as String? ?? '',
        summary: json['summary'] as String? ?? '',
        distanceKm: (json['distanceKm'] as num?)?.toDouble() ?? 0.0,
        staticDuration: _parseDuration(json['staticDuration']?.toString() ?? '0'),
        polyline: json['polyline'] as String?,
        segments: (json['segments'] as List?)
                ?.map((e) => RouteSegment.fromJson(e as Map<String, dynamic>))
                .toList() ??
            const [],
        traffic: json['traffic'] != null
            ? TrafficSnapshot.fromJson(json['traffic'] as Map<String, dynamic>)
            : null,
        evaluation: RouteEvaluation.fromJson(json['evaluation'] as Map<String, dynamic>),
        hazards: (json['hazards'] as List?)
                ?.map((e) => Hazard.fromJson(e as Map<String, dynamic>))
                .toList() ??
            const [],
        sourceName: json['sourceName'] as String? ?? 'Routing Provider',
        provenance: json['provenance'] as String? ?? 'unknown',
        risk: json['risk'] != null
            ? RiskAssessment.fromJson(json['risk'] as Map<String, dynamic>)
            : null,
      );

  Map<String, dynamic> toJson() => {
        'routeId': routeId,
        'summary': summary,
        'distanceKm': distanceKm,
        'staticDuration': staticDuration.inSeconds.toString(),
        'polyline': polyline,
        'segments': segments.map((e) => e.toJson()).toList(),
        'traffic': traffic?.toJson(),
        'evaluation': evaluation.toJson(),
        'hazards': hazards.map((e) => e.toJson()).toList(),
        'sourceName': sourceName,
        'provenance': provenance,
        'risk': risk?.toJson(),
      };
}

class TripResponse {
  final String? analysisId;
  final TripStatus status;
  final TripRequest request;
  final RiskAssessment? risk;
  final List<RouteSegment> route;
  final Recommendation? recommendation;
  final List<ModeOption> modeOptions;
  final List<Hazard> hazards;
  final List<DataSource> sources;
  final Duration estimatedDuration;
  final double distanceKm;
  final TrafficSnapshot? traffic;
  final List<EvaluatedRoute> routes;

  TripResponse({
    this.analysisId,
    this.status = TripStatus.success,
    required this.request,
    this.risk,
    required this.route,
    this.recommendation,
    required this.modeOptions,
    required this.hazards,
    required this.sources,
    required this.estimatedDuration,
    required this.distanceKm,
    this.traffic,
    this.routes = const [],
  });

  factory TripResponse.fromJson(Map<String, dynamic> json) {
    return TripResponse(
      analysisId: json['analysisId'] as String?,
      status: TripStatus.fromString(json['status'] as String?),
      request: TripRequest.fromJson(json['request'] as Map<String, dynamic>),
      risk: json['risk'] != null ? RiskAssessment.fromJson(json['risk'] as Map<String, dynamic>) : null,
      route: (json['route'] as List).map((e) => RouteSegment.fromJson(e as Map<String, dynamic>)).toList(),
      recommendation: json['recommendation'] != null ? Recommendation.fromJson(json['recommendation'] as Map<String, dynamic>) : null,
      modeOptions: json['modeOptions'] == null ? [] : (json['modeOptions'] as List).map((e) => ModeOption.fromJson(e as Map<String, dynamic>)).toList(),
      hazards: (json['hazards'] as List).map((e) => Hazard.fromJson(e as Map<String, dynamic>)).toList(),
      sources: (json['sources'] as List).map((e) => DataSource.fromJson(e as Map<String, dynamic>)).toList(),
      estimatedDuration: _parseDuration(json['estimatedDuration'] as String),
      distanceKm: (json['distanceKm'] as num).toDouble(),
      traffic: json['traffic'] != null
          ? TrafficSnapshot.fromJson(json['traffic'] as Map<String, dynamic>)
          : null,
      routes: json['routes'] != null
          ? (json['routes'] as List).map((e) => EvaluatedRoute.fromJson(e as Map<String, dynamic>)).toList()
          : const [],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'analysisId': analysisId,
      'status': status.name,
      'request': request.toJson(),
      'risk': risk?.toJson(),
      'route': route.map((e) => e.toJson()).toList(),
      'recommendation': recommendation?.toJson(),
      'modeOptions': modeOptions.map((e) => e.toJson()).toList(),
      'hazards': hazards.map((e) => e.toJson()).toList(),
      'sources': sources.map((e) => e.toJson()).toList(),
      'estimatedDuration': estimatedDuration.inSeconds.toString(),
      'distanceKm': distanceKm,
      'traffic': traffic?.toJson(),
      'routes': routes.map((e) => e.toJson()).toList(),
    };
  }
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

  factory RiskAssessment.fromJson(Map<String, dynamic> json) => RiskAssessment(
        overallScore: json['overallScore'] as int,
        level: RiskLevel.values.firstWhere((e) => e.name == json['level']),
        confidence: Confidence.fromJson(json['confidence'] as Map<String, dynamic>),
        factors: (json['factors'] as List).map((e) => RiskFactor.fromJson(e as Map<String, dynamic>)).toList(),
        summary: json['summary'] as String,
      );
      
  Map<String, dynamic> toJson() => {
    'overallScore': overallScore,
    'level': level.name,
    'confidence': confidence.toJson(),
    'factors': factors.map((e) => e.toJson()).toList(),
    'summary': summary,
  };
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

  factory RiskFactor.fromJson(Map<String, dynamic> json) => RiskFactor(
        name: json['name'] as String,
        description: json['description'] as String,
        score: json['score'] as int,
        level: RiskLevel.values.firstWhere((e) => e.name == json['level']),
        weight: (json['weight'] as num).toDouble(),
      );

  Map<String, dynamic> toJson() => {
    'name': name,
    'description': description,
    'score': score,
    'level': level.name,
    'weight': weight,
  };
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

  factory RouteSegment.fromJson(Map<String, dynamic> json) => RouteSegment(
        startLat: (json['startLat'] as num).toDouble(),
        startLng: (json['startLng'] as num).toDouble(),
        endLat: (json['endLat'] as num).toDouble(),
        endLng: (json['endLng'] as num).toDouble(),
        riskLevel: RiskLevel.values.firstWhere((e) => e.name == json['riskLevel']),
        description: json['description'] as String?,
        weather: json['weather'] != null ? WeatherPoint.fromJson(json['weather'] as Map<String, dynamic>) : null,
      );

  Map<String, dynamic> toJson() => {
    'startLat': startLat,
    'startLng': startLng,
    'endLat': endLat,
    'endLng': endLng,
    'riskLevel': riskLevel.name,
    'description': description,
    'weather': weather?.toJson(),
  };
}

class WeatherPoint {
  final DateTime time;
  final double temperature; // Celsius
  final double precipitation; // mm/hr
  final int humidity; // percentage
  final double windSpeed; // km/h
  final double? windGusts;
  final double? visibility;
  final String condition; // "Heavy Rain", "Cloudy", etc.
  final String icon;

  const WeatherPoint({
    required this.time,
    required this.temperature,
    required this.precipitation,
    required this.humidity,
    required this.windSpeed,
    this.windGusts,
    this.visibility,
    required this.condition,
    required this.icon,
  });

  factory WeatherPoint.fromJson(Map<String, dynamic> json) => WeatherPoint(
        time: DateTime.parse(json['time'] as String).toLocal(),
        temperature: (json['temperature'] as num).toDouble(),
        // Handle camelCase precipitationMm to precipitation mapping
        precipitation: ((json['precipitationMm'] ?? json['precipitation'] ?? 0.0) as num).toDouble(),
        humidity: json['humidity'] as int,
        windSpeed: (json['windSpeed'] as num).toDouble(),
        windGusts: json['windGusts'] != null ? (json['windGusts'] as num).toDouble() : null,
        visibility: json['visibility'] != null ? (json['visibility'] as num).toDouble() : null,
        condition: json['condition'] as String,
        icon: json['icon'] as String,
      );

  Map<String, dynamic> toJson() => {
    'time': time.toIso8601String(),
    'temperature': temperature,
    'precipitation': precipitation,
    'humidity': humidity,
    'windSpeed': windSpeed,
    'windGusts': windGusts,
    'visibility': visibility,
    'condition': condition,
    'icon': icon,
  };
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

  factory Hazard.fromJson(Map<String, dynamic> json) {
    // If wrapped in TripHazard from engine, unwrap it
    final data = json.containsKey('hazard') ? json['hazard'] as Map<String, dynamic> : json;
    
    // Map backend type strings to HazardType enum, fallback to waterlogging if unknown
    HazardType parseType(String t) {
      try {
        return HazardType.values.firstWhere((e) => e.name == t);
      } catch (_) {
        return HazardType.waterlogging;
      }
    }

    return Hazard(
      id: data['id'] as String? ?? 'unknown',
      type: parseType(data['type'] as String? ?? 'waterlogging'),
      title: data['title'] as String? ?? 'Hazard',
      description: data['description'] as String? ?? '',
      lat: (data['lat'] as num? ?? 0).toDouble(),
      lng: (data['lng'] as num? ?? 0).toDouble(),
      severity: data['severity'] != null 
          ? RiskLevel.values.firstWhere((e) => e.name == data['severity'], orElse: () => RiskLevel.moderate) 
          : RiskLevel.moderate,
      reportedAt: data['reportedAt'] != null ? DateTime.parse(data['reportedAt'] as String).toLocal() : null,
      source: data['sourceClass'] != null ? '${data['sourceClass']}' : data['sourceName'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'type': type.name,
    'title': title,
    'description': description,
    'lat': lat,
    'lng': lng,
    'severity': severity.name,
    'reportedAt': reportedAt?.toIso8601String(),
    'sourceName': source,
  };
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

  factory OfficialAlert.fromJson(Map<String, dynamic> json) => OfficialAlert(
        id: json['id'] as String,
        title: json['title'] as String,
        description: json['description'] as String,
        severity: AlertSeverity.values.firstWhere((e) => e.name == json['severity']),
        issuedBy: json['issuedBy'] as String,
        issuedAt: DateTime.parse(json['issuedAt'] as String).toLocal(),
        expiresAt: json['expiresAt'] != null ? DateTime.parse(json['expiresAt'] as String).toLocal() : null,
        affectedAreas: (json['affectedAreas'] as List).map((e) => e.toString()).toList(),
        actionRequired: json['actionRequired'] as String?,
        source: json['source'] as String?,
      );
}

class ModeOption {
  final TransportMode mode;
  final Duration estimatedDuration;
  final RiskAssessment? risk;
  final double distanceKm;
  final String? recommendation;
  final List<String> highlights;

  ModeOption({
    required this.mode,
    required this.estimatedDuration,
    this.risk,
    required this.distanceKm,
    this.recommendation,
    required this.highlights,
  });

  factory ModeOption.fromJson(Map<String, dynamic> json) {
    return ModeOption(
      mode: TransportMode.values.firstWhere(
        (e) => e.name == json['mode'],
        orElse: () => TransportMode.car,
      ),
      estimatedDuration: _parseDuration(json['estimatedDuration'] as String),
      risk: json['risk'] != null ? RiskAssessment.fromJson(json['risk'] as Map<String, dynamic>) : null,
      distanceKm: (json['distanceKm'] as num).toDouble(),
      recommendation: json['recommendation'] as String?,
      highlights: (json['highlights'] as List).map((e) => e as String).toList(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'mode': mode.name,
      'estimatedDuration': estimatedDuration.inSeconds.toString(),
      'risk': risk?.toJson(),
      'distanceKm': distanceKm,
      'recommendation': recommendation,
      'highlights': highlights,
    };
  }
}

class ScenarioResult {
  final String? scenarioId;
  final TripStatus status;
  final DateTime departureTime;
  final RiskAssessment? risk;
  final Duration estimatedDuration;
  final String? recommendation;
  final List<RiskFactor> changedFactors;

  ScenarioResult({
    this.scenarioId,
    this.status = TripStatus.success,
    required this.departureTime,
    this.risk,
    required this.estimatedDuration,
    this.recommendation,
    required this.changedFactors,
  });

  factory ScenarioResult.fromJson(Map<String, dynamic> json) {
    return ScenarioResult(
      scenarioId: json['scenarioId'] as String?,
      status: TripStatus.fromString(json['status'] as String?),
      departureTime: DateTime.parse(json['departureTime'] as String).toLocal(),
      risk: json['risk'] != null ? RiskAssessment.fromJson(json['risk'] as Map<String, dynamic>) : null,
      estimatedDuration: _parseDuration(json['estimatedDuration'] as String),
      recommendation: json['recommendation'] as String?,
      changedFactors: (json['changedFactors'] as List).map((i) => RiskFactor.fromJson(i as Map<String, dynamic>)).toList(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'scenarioId': scenarioId,
      'status': status.name,
      'departureTime': departureTime.toIso8601String(),
      'risk': risk?.toJson(),
      'estimatedDuration': estimatedDuration.inSeconds.toString(),
      'recommendation': recommendation,
      'changedFactors': changedFactors.map((e) => e.toJson()).toList(),
    };
  }
}

class Confidence {
  final ConfidenceLevel level;
  final String explanation;

  const Confidence({
    required this.level,
    required this.explanation,
  });

  factory Confidence.fromJson(Map<String, dynamic> json) => Confidence(
        level: ConfidenceLevel.values.firstWhere((e) => e.name == json['level']),
        explanation: json['explanation'] as String,
      );
      
  Map<String, dynamic> toJson() => {
        'level': level.name,
        'explanation': explanation,
      };
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

  factory Recommendation.fromJson(Map<String, dynamic> json) => Recommendation(
        headline: json['headline'] as String,
        body: json['body'] as String,
        alternativeAction: json['alternativeAction'] as String?,
        suggestedMode: json['suggestedMode'] != null ? TransportMode.values.firstWhere((e) => e.name == json['suggestedMode']) : null,
        suggestedDepartureTime: json['suggestedDepartureTime'] != null ? DateTime.parse(json['suggestedDepartureTime'] as String).toLocal() : null,
      );

  Map<String, dynamic> toJson() => {
        'headline': headline,
        'body': body,
        'alternativeAction': alternativeAction,
        'suggestedMode': suggestedMode?.name,
        'suggestedDepartureTime': suggestedDepartureTime?.toUtc().toIso8601String(),
      };
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

  factory DataSource.fromJson(Map<String, dynamic> json) => DataSource(
        name: json['name'] as String,
        type: json['type'] as String,
        lastUpdated: DateTime.parse(json['lastUpdated'] as String).toLocal(),
      );

  Map<String, dynamic> toJson() => {
        'name': name,
        'type': type,
        'lastUpdated': lastUpdated.toUtc().toIso8601String(),
      };
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

  // Keep Mock behavior for now as this isn't strictly coming from backend MVP yet
}

/// Helper to parse ISO8601 duration (e.g. PT1H5M) or fallback to basic string
Duration _parseDuration(String durationString) {
  // Try to parse basic HH:MM:SS format if generated from timedelta directly
  try {
      if (durationString.startsWith('PT')) {
          // Simplistic ISO duration parser for PT#H#M#S
          int hours = 0;
          int minutes = 0;
          int seconds = 0;
          
          String s = durationString.substring(2);
          if (s.contains('H')) {
              var parts = s.split('H');
              hours = int.parse(parts[0]);
              s = parts.length > 1 ? parts[1] : '';
          }
          if (s.contains('M')) {
              var parts = s.split('M');
              minutes = int.parse(parts[0]);
              s = parts.length > 1 ? parts[1] : '';
          }
          if (s.contains('S')) {
              var parts = s.split('S');
              seconds = double.parse(parts[0]).round();
          }
          return Duration(hours: hours, minutes: minutes, seconds: seconds);
      }

      // Format like "0:55:00" from python timedelta
      List<String> parts = durationString.split(':');
      if (parts.length == 3) {
          int hours = int.parse(parts[0]);
          int minutes = int.parse(parts[1]);
          int seconds = double.parse(parts[2]).round();
          return Duration(hours: hours, minutes: minutes, seconds: seconds);
      }

      // Format like raw seconds "3300"
      final totalSeconds = int.tryParse(durationString);
      if (totalSeconds != null) {
        return Duration(seconds: totalSeconds);
      }
  } catch (e) {
      // Fallback
  }
  return const Duration(minutes: 0);
}
