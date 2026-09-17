import 'package:flutter_test/flutter_test.dart';
import 'package:weather_gpt/models/models.dart';

void main() {
  group('Model Deserialization Tests', () {
    test('WeatherPoint handles precipitationMm to precipitation', () {
      final json = {
        'time': '2026-08-27T08:00:00Z',
        'temperature': 32.5,
        'precipitationMm': 12.0,
        'humidity': 80,
        'windSpeed': 15.0,
        'condition': 'Heavy Rain',
        'icon': '🌧️'
      };

      final point = WeatherPoint.fromJson(json);
      expect(point.precipitation, 12.0);
    });

    test('WeatherPoint handles optional windGusts and visibility', () {
      final json = {
        'time': '2026-08-27T08:00:00Z',
        'temperature': 32.5,
        'precipitationMm': 0.0,
        'humidity': 80,
        'windSpeed': 15.0,
        'windGusts': 20.0,
        'visibility': 5000.0,
        'condition': 'Cloudy',
        'icon': '☁️'
      };

      final point = WeatherPoint.fromJson(json);
      expect(point.windGusts, 20.0);
      expect(point.visibility, 5000.0);
    });

    test('Confidence qualitative parsing', () {
      final json = {
        'level': 'high',
        'explanation': 'Based on multiple sources'
      };

      final confidence = Confidence.fromJson(json);
      expect(confidence.level, ConfidenceLevel.high);
    });

    test('TripRequest serialization and deserialization', () {
      final original = TripRequest(
        origin: 'Noida',
        destination: 'Delhi',
        departureTime: DateTime.utc(2026, 8, 27, 8, 0),
        mode: TransportMode.car,
      );

      final json = original.toJson();
      expect(json['origin'], 'Noida');
      expect(json['mode'], 'car');

      final restored = TripRequest.fromJson(json);
      expect(restored.origin, original.origin);
      expect(restored.mode, original.mode);
      expect(restored.departureTime.toUtc(), original.departureTime.toUtc());
    });

    test('Hazard unwrapping from TripHazard', () {
      final json = {
        'hazard': {
          'id': 'h1',
          'type': 'waterlogging',
          'title': 'Flooded road',
          'description': 'Deep water',
          'lat': 28.5,
          'lng': 77.0,
          'severity': 'high',
          'sourceName': 'demo',
          'sourceClass': 'demo'
        },
        'distanceKm': 0.5,
        'riskContribution': 25
      };

      final hazard = Hazard.fromJson(json);
      expect(hazard.id, 'h1');
      expect(hazard.type, HazardType.waterlogging);
      expect(hazard.severity, RiskLevel.high);
      expect(hazard.source, 'demo');
    });

    test('Malformed JSON handling throws TypeError or format exception', () {
      final json = {
        'time': 'invalid-date',
        'temperature': 'not-a-number',
      };

      expect(() => WeatherPoint.fromJson(json), throwsException);
    });

    test('TripStatus.fromString parses snake_case and camelCase correctly', () {
      expect(TripStatus.fromString('routing_unavailable'), TripStatus.routingUnavailable);
      expect(TripStatus.fromString('routingUnavailable'), TripStatus.routingUnavailable);
      expect(TripStatus.fromString('weather_unavailable'), TripStatus.weatherUnavailable);
      expect(TripStatus.fromString('weatherUnavailable'), TripStatus.weatherUnavailable);
      expect(TripStatus.fromString('degraded'), TripStatus.degraded);
      expect(TripStatus.fromString('success'), TripStatus.success);
      expect(TripStatus.fromString(null), TripStatus.success);
    });

    test('TripResponse.fromJson parses degraded routing_unavailable response with null risk', () {
      final json = {
        'analysisId': 'test-analysis-123',
        'status': 'routing_unavailable',
        'request': {
          'origin': 'Noida',
          'destination': 'Gurgaon',
          'departureTime': '2026-08-27T08:00:00Z',
          'mode': 'bike'
        },
        'risk': null,
        'route': [],
        'recommendation': null,
        'modeOptions': [],
        'hazards': [],
        'sources': [
          {
            'name': 'Open-Meteo',
            'type': 'Weather',
            'lastUpdated': '2026-08-27T08:00:00Z'
          },
          {
            'name': 'GoogleRoutesProvider',
            'type': 'Routing [unavailable]',
            'lastUpdated': '2026-08-27T08:00:00Z'
          }
        ],
        'estimatedDuration': '0',
        'distanceKm': 0.0
      };

      final response = TripResponse.fromJson(json);
      expect(response.status, TripStatus.routingUnavailable);
      expect(response.risk, isNull);
      expect(response.recommendation, isNull);
      expect(response.route, isEmpty);
      expect(response.sources.length, 2);
      expect(response.sources[1].type, 'Routing [unavailable]');
      expect(response.sources[1].name, 'GoogleRoutesProvider');
    });

    test('TripResponse.fromJson parses weather_unavailable response with null risk', () {
      final json = {
        'analysisId': 'test-analysis-456',
        'status': 'weather_unavailable',
        'request': {
          'origin': 'Noida',
          'destination': 'Gurgaon',
          'departureTime': '2026-08-27T08:00:00Z',
          'mode': 'car'
        },
        'risk': null,
        'route': [],
        'recommendation': null,
        'modeOptions': [],
        'hazards': [],
        'sources': [],
        'estimatedDuration': '0',
        'distanceKm': 0.0
      };

      final response = TripResponse.fromJson(json);
      expect(response.status, TripStatus.weatherUnavailable);
      expect(response.risk, isNull);
      expect(response.recommendation, isNull);
      expect(response.route, isEmpty);
    });
  });
}
