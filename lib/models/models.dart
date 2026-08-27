/// WeatherGPT Domain Models
/// These represent the structured decision objects from the future backend.
/// Flutter consumes these — it does NOT compute risk or weather logic.

// ── Enums ──

enum TransportMode { bike, car, metro, walk }

enum RiskLevel { low, moderate, high, severe }

enum HazardType { waterlogging, fog, heavyRain, storm, heatwave, construction, wind, heat, visibility }

enum AlertSeverity { advisory, watch, warning, emergency }

enum ConfidenceLevel { low, medium, high, veryHigh }

enum TripStatus {
  success,
  routingUnavailable,
  weatherUnavailable,
  degraded,
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
  });

  factory TripResponse.fromJson(Map<String, dynamic> json) {
    return TripResponse(
      analysisId: json['analysisId'] as String?,
      status: TripStatus.values.firstWhere(
        (e) => e.name == json['status'],
        orElse: () => TripStatus.success,
      ),
      request: TripRequest.fromJson(json['request'] as Map<String, dynamic>),
      risk: json['risk'] != null ? RiskAssessment.fromJson(json['risk'] as Map<String, dynamic>) : null,
      route: (json['route'] as List).map((e) => RouteSegment.fromJson(e as Map<String, dynamic>)).toList(),
      recommendation: json['recommendation'] != null ? Recommendation.fromJson(json['recommendation'] as Map<String, dynamic>) : null,
      modeOptions: json['modeOptions'] == null ? [] : (json['modeOptions'] as List).map((e) => ModeOption.fromJson(e as Map<String, dynamic>)).toList(),
      hazards: (json['hazards'] as List).map((e) => Hazard.fromJson(e as Map<String, dynamic>)).toList(),
      sources: (json['sources'] as List).map((e) => DataSource.fromJson(e as Map<String, dynamic>)).toList(),
      estimatedDuration: _parseDuration(json['estimatedDuration'] as String),
      distanceKm: (json['distanceKm'] as num).toDouble(),
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
      status: TripStatus.values.firstWhere(
        (e) => e.name == json['status'],
        orElse: () => TripStatus.success,
      ),
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
  } catch (e) {
      // Fallback
  }
  return const Duration(minutes: 0);
}
