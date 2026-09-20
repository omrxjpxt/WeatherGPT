import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:weather_gpt/core/theme/app_theme.dart';
import 'package:weather_gpt/core/providers.dart';
import 'package:weather_gpt/models/models.dart';
import 'package:weather_gpt/features/trip_analysis/trip_analysis_screen.dart';

Widget _buildTestApp({
  required TripResponse trip,
  Size size = const Size(393, 852),
}) {
  return ProviderScope(
    overrides: [
      tripResponseProvider.overrideWith((ref) => Future.value(trip)),
    ],
    child: MaterialApp(
      theme: AppTheme.light,
      home: MediaQuery(
        data: MediaQueryData(
          size: size,
          padding: const EdgeInsets.only(top: 50, bottom: 34),
        ),
        child: const TripAnalysisScreen(),
      ),
    ),
  );
}

TripResponse _createBaseTrip({
  AirQualitySnapshot? airQuality,
  TransportMode mode = TransportMode.car,
}) {
  return TripResponse(
    analysisId: 'aqi-test-1',
    status: TripStatus.success,
    request: TripRequest(
      origin: 'Connaught Place, Delhi',
      destination: 'Cyber Hub, Gurgaon',
      departureTime: DateTime(2026, 8, 27, 8, 0),
      mode: mode,
    ),
    risk: const RiskAssessment(
      overallScore: 25,
      level: RiskLevel.low,
      confidence: Confidence(level: ConfidenceLevel.high, explanation: 'High confidence based on verified models'),
      factors: [],
      summary: 'Low risk route',
    ),
    route: const [],
    recommendation: const Recommendation(
      headline: 'Proceed via NH 48',
      body: 'Clear conditions along the route.',
      alternativeAction: 'proceed',
    ),
    modeOptions: const [],
    hazards: const [],
    sources: [],
    estimatedDuration: const Duration(minutes: 45),
    distanceKm: 28.0,
    airQuality: airQuality,
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Air Quality Card Widget Tests', () {
    testWidgets('renders available AQI card with index, PM2.5, and category', (tester) async {
      final trip = _createBaseTrip(
        airQuality: const AirQualitySnapshot(
          aqi: 142,
          pm25: 55.4,
          pm10: 110.2,
          category: 'Moderate',
          sourceName: 'Open-Meteo CAMS',
          isAvailable: true,
          isStale: false,
          provenance: 'cams_reanalysis',
        ),
      );

      await tester.binding.setSurfaceSize(const Size(393, 852));
      await tester.pumpWidget(_buildTestApp(trip: trip));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('air_quality_card')), findsOneWidget);
      expect(find.text('AIR QUALITY INTELLIGENCE'), findsOneWidget);
      expect(find.text('AQI 142 • Moderate'), findsOneWidget);
      expect(find.text('55.4 µg/m³'), findsOneWidget);
      expect(find.text('110.2 µg/m³'), findsOneWidget);
      expect(find.text('Source: Open-Meteo CAMS • cams_reanalysis'), findsOneWidget);
    });

    testWidgets('renders unavailable state when airQuality is missing or unavailable', (tester) async {
      final trip = _createBaseTrip(
        airQuality: const AirQualitySnapshot(
          aqi: 0,
          pm25: 0.0,
          category: 'Unknown',
          sourceName: 'Unavailable',
          isAvailable: false,
          provenance: 'provider_failed',
        ),
      );

      await tester.binding.setSurfaceSize(const Size(393, 852));
      await tester.pumpWidget(_buildTestApp(trip: trip));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('air_quality_card_unavailable')), findsOneWidget);
      expect(find.text('Air Quality Unavailable'), findsOneWidget);
      expect(find.textContaining('Baseline environmental model applied'), findsOneWidget);
    });

    testWidgets('renders stale state indicator when airQuality isStale is true', (tester) async {
      final trip = _createBaseTrip(
        airQuality: const AirQualitySnapshot(
          aqi: 215,
          pm25: 145.0,
          category: 'Poor',
          sourceName: 'Open-Meteo CAMS',
          isAvailable: true,
          isStale: true,
          provenance: 'cached_cams',
        ),
      );

      await tester.binding.setSurfaceSize(const Size(393, 852));
      await tester.pumpWidget(_buildTestApp(trip: trip));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('air_quality_card')), findsOneWidget);
      expect(find.byKey(const Key('air_quality_stale_indicator')), findsOneWidget);
      expect(find.text('STALE DATA'), findsOneWidget);
      expect(find.text('AQI 215 • Poor'), findsOneWidget);
    });

    testWidgets('renders mode-specific guidance for car (cabin filtration)', (tester) async {
      final trip = _createBaseTrip(
        mode: TransportMode.car,
        airQuality: const AirQualitySnapshot(
          aqi: 260,
          pm25: 180.0,
          category: 'Severe',
          sourceName: 'Open-Meteo CAMS',
          isAvailable: true,
          isStale: false,
        ),
      );

      await tester.binding.setSurfaceSize(const Size(393, 852));
      await tester.pumpWidget(_buildTestApp(trip: trip));
      await tester.pumpAndSettle();

      expect(find.textContaining('Cabin air-filtration active'), findsOneWidget);
    });

    testWidgets('renders mode-specific guidance for bike with high AQI (mask recommended)', (tester) async {
      final trip = _createBaseTrip(
        mode: TransportMode.bike,
        airQuality: const AirQualitySnapshot(
          aqi: 260,
          pm25: 180.0,
          category: 'Severe',
          sourceName: 'Open-Meteo CAMS',
          isAvailable: true,
          isStale: false,
        ),
      );

      await tester.binding.setSurfaceSize(const Size(393, 852));
      await tester.pumpWidget(_buildTestApp(trip: trip));
      await tester.pumpAndSettle();

      expect(find.textContaining('N95 mask strongly recommended'), findsOneWidget);
    });
  });
}
