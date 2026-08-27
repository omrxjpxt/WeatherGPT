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
  });
}
