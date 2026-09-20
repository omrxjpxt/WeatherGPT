import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:weather_gpt/core/theme/app_theme.dart';
import 'package:weather_gpt/core/api/api_config.dart';
import 'package:weather_gpt/core/providers.dart';
import 'package:weather_gpt/models/models.dart';
import 'package:weather_gpt/features/home/home_screen.dart';
import 'package:weather_gpt/features/trip_analysis/trip_analysis_screen.dart';
import 'package:weather_gpt/features/what_if/what_if_screen.dart';
import 'package:weather_gpt/features/mode_comparison/mode_comparison_screen.dart';
import 'package:weather_gpt/features/risk_confidence/risk_confidence_screen.dart';
import 'package:weather_gpt/features/official_alert/official_alert_screen.dart';
import 'package:weather_gpt/features/local_hazard/local_hazard_screen.dart';
import 'package:weather_gpt/features/alerts/alerts_feed_screen.dart';
import 'package:weather_gpt/features/historical_replay/historical_replay_screen.dart';
import 'package:weather_gpt/features/assistant/assistant_screen.dart';
import 'package:weather_gpt/features/voice/voice_input_screen.dart';
import 'package:weather_gpt/features/profile/profile_screen.dart';
import 'package:weather_gpt/core/auth/auth_service.dart';
import 'package:weather_gpt/core/auth/mock_auth_service.dart';

Widget _buildTestApp({
  required Widget screen,
  Size size = const Size(393, 852), // iPhone 15 Pro standard
  EdgeInsets padding = const EdgeInsets.only(top: 59, bottom: 34), // Dynamic Island + Home bar
  List overrides = const [],
}) {
  return ProviderScope(
    overrides: overrides.cast(),
    child: MaterialApp(
      theme: AppTheme.light,
      home: MediaQuery(
        data: MediaQueryData(
          size: size,
          padding: padding,
          viewInsets: EdgeInsets.zero,
        ),
        child: screen,
      ),
    ),
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Screen Layout & iPhone Visual QA Tests', () {
    setUp(() {
      ApiConfig.mode = AppMode.mock;
    });
    testWidgets('Home Screen renders without overflow on iPhone standard and small screens', (tester) async {
      // iPhone standard
      await tester.binding.setSurfaceSize(const Size(393, 852));
      await tester.pumpWidget(_buildTestApp(screen: const HomeScreen()));
      await tester.pumpAndSettle();

      expect(find.text('Good Morning'), findsOneWidget);
      expect(find.text('Noida, Sector 62'), findsOneWidget);
      expect(find.text('AI Insight'), findsOneWidget);
      expect(tester.takeException(), isNull);

      // iPhone SE (375 x 667)
      await tester.binding.setSurfaceSize(const Size(375, 667));
      await tester.pumpWidget(_buildTestApp(
        screen: const HomeScreen(),
        size: const Size(375, 667),
        padding: const EdgeInsets.only(top: 20, bottom: 0),
      ));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    });

    testWidgets('Trip Analysis renders properly and handles degraded routing_unavailable state', (tester) async {
      final degradedTrip = TripResponse(
        analysisId: 'degraded-1',
        status: TripStatus.routingUnavailable,
        request: TripRequest(
          origin: 'Noida Sector 62',
          destination: 'Gurgaon Cyber Hub',
          departureTime: DateTime(2026, 8, 27, 8, 0),
          mode: TransportMode.bike,
        ),
        risk: null,
        route: [],
        recommendation: null,
        modeOptions: [],
        hazards: [],
        sources: [
          DataSource(
            name: 'Open-Meteo',
            type: 'Weather',
            lastUpdated: DateTime(2026, 8, 27, 8, 0),
          ),
          DataSource(
            name: 'GoogleRoutesProvider',
            type: 'Routing [unavailable]',
            lastUpdated: DateTime(2026, 8, 27, 8, 0),
          ),
        ],
        estimatedDuration: Duration.zero,
        distanceKm: 0.0,
      );

      FlutterErrorDetails? caughtDetails;
      final originalOnError = FlutterError.onError;
      FlutterError.onError = (details) {
        caughtDetails = details;
      };

      await tester.binding.setSurfaceSize(const Size(393, 852));
      await tester.pumpWidget(_buildTestApp(
        screen: const TripAnalysisScreen(),
        overrides: [
          tripResponseProvider.overrideWith((ref) => Future.value(degradedTrip)),
        ],
      ));
      await tester.pumpAndSettle();

      FlutterError.onError = originalOnError;
      if (caughtDetails != null) {
        // ignore: avoid_print
        print('FULL ERROR DETAILS:\n${caughtDetails!.toString()}');
      }
      expect(find.text('Routing is currently unavailable.'), findsWidgets);
      expect(caughtDetails, isNull);
    });

    testWidgets('Trip Analysis renders Traffic Intelligence card with delays and metrics on iPhone 15 Pro and SE', (tester) async {
      final tripWithTraffic = TripResponse(
        analysisId: 'traffic-test-1',
        status: TripStatus.success,
        request: TripRequest(
          origin: 'Noida Sector 62',
          destination: 'Gurgaon Cyber Hub',
          departureTime: DateTime(2026, 8, 27, 8, 0),
          mode: TransportMode.car,
        ),
        risk: const RiskAssessment(
          overallScore: 42,
          level: RiskLevel.moderate,
          confidence: Confidence(level: ConfidenceLevel.high, explanation: 'Deterministic models'),
          factors: [
            RiskFactor(
              name: 'Traffic Congestion',
              description: 'Moderate rush hour delay',
              score: 15,
              level: RiskLevel.moderate,
              weight: 0.15,
            )
          ],
          summary: 'Moderate rush hour delay with clear skies.',
        ),
        route: const [
          RouteSegment(
            startLat: 28.5355,
            startLng: 77.3910,
            endLat: 28.4595,
            endLng: 77.0266,
            riskLevel: RiskLevel.moderate,
            description: 'Take Noida-Greater Noida Expy',
          ),
        ],
        recommendation: const Recommendation(
          headline: 'Depart on schedule',
          body: 'Congestion adds 12 min to your trip. No severe weather on route.',
        ),
        modeOptions: const [],
        hazards: const [],
        sources: [
          DataSource(
            name: 'Open-Meteo',
            type: 'Weather',
            lastUpdated: DateTime(2026, 8, 27, 8, 0),
          ),
          DataSource(
            name: 'Mock Traffic Provider (Demo)',
            type: 'Traffic [mock]',
            lastUpdated: DateTime(2026, 8, 27, 8, 0),
          ),
        ],
        estimatedDuration: const Duration(minutes: 50),
        distanceKm: 38.0,
        traffic: TrafficSnapshot(
          status: TrafficStatus.mock,
          condition: TrafficCondition.congested,
          congestionLevel: CongestionLevel.moderate,
          delaySeconds: 720.0,
          staticDuration: const Duration(minutes: 50),
          trafficAwareDuration: const Duration(minutes: 62),
          currentSpeedKmh: 35.0,
          freeFlowSpeedKmh: 45.0,
          segments: const [],
          timestamp: DateTime(2026, 8, 27, 8, 0),
          sourceName: 'Mock Traffic Provider (Demo)',
          provenance: 'demo/mock',
        ),
      );

      // iPhone 15 Pro
      await tester.binding.setSurfaceSize(const Size(393, 852));
      await tester.pumpWidget(_buildTestApp(
        screen: const TripAnalysisScreen(),
        overrides: [
          tripResponseProvider.overrideWith((ref) => Future.value(tripWithTraffic)),
        ],
      ));
      await tester.pumpAndSettle();

      await tester.drag(find.byType(CustomScrollView), const Offset(0, -300));
      await tester.pumpAndSettle();

      expect(find.text('TRAFFIC CONDITIONS'), findsOneWidget);
      expect(find.text('CURRENT TIME'), findsOneWidget);
      expect(find.text('FREE-FLOW'), findsOneWidget);
      expect(find.text('EST. DELAY'), findsOneWidget);
      expect(find.text('+12 min'), findsWidgets);
      expect(find.text('Moderate Traffic'), findsOneWidget);
      expect(tester.takeException(), isNull);

      // iPhone SE
      await tester.binding.setSurfaceSize(const Size(375, 667));
      await tester.pumpWidget(_buildTestApp(
        screen: const TripAnalysisScreen(),
        size: const Size(375, 667),
        padding: const EdgeInsets.only(top: 20, bottom: 0),
        overrides: [
          tripResponseProvider.overrideWith((ref) => Future.value(tripWithTraffic)),
        ],
      ));
      await tester.pumpAndSettle();

      await tester.drag(find.byType(CustomScrollView), const Offset(0, -300));
      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull);
    });

    testWidgets('Trip Analysis renders degraded traffic banner when traffic is unavailable', (tester) async {
      final tripWithUnavailableTraffic = TripResponse(
        analysisId: 'traffic-unavail-1',
        status: TripStatus.success,
        request: TripRequest(
          origin: 'Noida Sector 62',
          destination: 'Gurgaon Cyber Hub',
          departureTime: DateTime(2026, 8, 27, 8, 0),
          mode: TransportMode.car,
        ),
        risk: const RiskAssessment(
          overallScore: 20,
          level: RiskLevel.low,
          confidence: Confidence(level: ConfidenceLevel.high, explanation: 'Clear skies'),
          factors: [],
          summary: 'Low risk trip.',
        ),
        route: const [
          RouteSegment(
            startLat: 28.5355,
            startLng: 77.3910,
            endLat: 28.4595,
            endLng: 77.0266,
            riskLevel: RiskLevel.low,
            description: 'Take Noida-Greater Noida Expy',
          ),
        ],
        recommendation: const Recommendation(
          headline: 'Good to go',
          body: 'Weather conditions are optimal.',
        ),
        modeOptions: const [],
        hazards: const [],
        sources: [
          DataSource(
            name: 'Unavailable Traffic Provider',
            type: 'Traffic [unavailable]',
            lastUpdated: DateTime(2026, 8, 27, 8, 0),
          ),
        ],
        estimatedDuration: const Duration(minutes: 50),
        distanceKm: 38.0,
        traffic: TrafficSnapshot(
          status: TrafficStatus.unavailable,
          condition: TrafficCondition.unknown,
          congestionLevel: CongestionLevel.unknown,
          delaySeconds: 0.0,
          staticDuration: const Duration(minutes: 50),
          trafficAwareDuration: const Duration(minutes: 50),
          segments: const [],
          timestamp: DateTime(2026, 8, 27, 8, 0),
          sourceName: 'Unavailable Traffic Provider',
          provenance: 'unavailable',
        ),
      );

      await tester.binding.setSurfaceSize(const Size(393, 852));
      await tester.pumpWidget(_buildTestApp(
        screen: const TripAnalysisScreen(),
        overrides: [
          tripResponseProvider.overrideWith((ref) => Future.value(tripWithUnavailableTraffic)),
        ],
      ));
      await tester.pumpAndSettle();

      await tester.drag(find.byType(CustomScrollView), const Offset(0, -300));
      await tester.pumpAndSettle();

      expect(find.text('Traffic Data Unavailable'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('Trip Analysis renders Route Alternatives and manages activeRouteId vs backend recommendation', (tester) async {
      final static1 = const Duration(minutes: 65);
      final delay1 = const Duration(minutes: 12);
      final traffic1 = TrafficSnapshot(
        status: TrafficStatus.mock,
        condition: TrafficCondition.congested,
        congestionLevel: CongestionLevel.moderate,
        delaySeconds: delay1.inSeconds.toDouble(),
        staticDuration: static1,
        trafficAwareDuration: static1 + delay1,
        currentSpeedKmh: 35.0,
        freeFlowSpeedKmh: 45.0,
        timestamp: DateTime(2026, 8, 27, 8, 0),
        sourceName: 'Mock Traffic Provider (Demo)',
        provenance: 'demo/mock',
      );

      final static2 = const Duration(minutes: 56);
      final delay2 = const Duration(minutes: 24);
      final traffic2 = TrafficSnapshot(
        status: TrafficStatus.mock,
        condition: TrafficCondition.congested,
        congestionLevel: CongestionLevel.heavy,
        delaySeconds: delay2.inSeconds.toDouble(),
        staticDuration: static2,
        trafficAwareDuration: static2 + delay2,
        currentSpeedKmh: 28.5,
        freeFlowSpeedKmh: 45.0,
        timestamp: DateTime(2026, 8, 27, 8, 0),
        sourceName: 'Mock Traffic Provider (Demo)',
        provenance: 'demo/mock',
      );

      final route1 = EvaluatedRoute(
        routeId: 'route_1',
        summary: 'Via Expressway',
        distanceKm: 35.5,
        staticDuration: static1,
        traffic: traffic1,
        sourceName: 'Mock Routing (Demo)',
        provenance: 'demo/mock',
        risk: const RiskAssessment(
          overallScore: 42,
          level: RiskLevel.moderate,
          confidence: Confidence(level: ConfidenceLevel.high, explanation: 'High confidence'),
          factors: [],
          summary: 'Expressway corridor conditions',
        ),
        evaluation: RouteEvaluation(
          routeId: 'route_1',
          riskScore: 42,
          riskLevel: RiskLevel.moderate,
          staticDuration: static1,
          trafficAwareDuration: static1 + delay1,
          trafficDelaySeconds: delay1.inSeconds.toDouble(),
          exposureScore: 16.8,
          bottleneckScore: 40,
          hazardCount: 1,
          isFeasible: true,
          recommendationHeadline: 'Expressway Route',
          recommendationBody: 'Recommended deterministic path.',
          isSelected: true,
          selectionReason: 'Recommended: Moderate risk (42/100) with 77 min travel time (+12m traffic).',
          provenance: 'demo/mock',
        ),
      );

      final route2 = EvaluatedRoute(
        routeId: 'route_2',
        summary: 'Via DND Flyway',
        distanceKm: 38.0,
        staticDuration: static2,
        traffic: traffic2,
        sourceName: 'Mock Routing (Demo)',
        provenance: 'demo/mock',
        risk: const RiskAssessment(
          overallScore: 48,
          level: RiskLevel.moderate,
          confidence: Confidence(level: ConfidenceLevel.high, explanation: 'High confidence'),
          factors: [],
          summary: 'Flyway corridor conditions',
        ),
        evaluation: RouteEvaluation(
          routeId: 'route_2',
          riskScore: 48,
          riskLevel: RiskLevel.moderate,
          staticDuration: static2,
          trafficAwareDuration: static2 + delay2,
          trafficDelaySeconds: delay2.inSeconds.toDouble(),
          exposureScore: 21.6,
          bottleneckScore: 65,
          hazardCount: 2,
          isFeasible: true,
          recommendationHeadline: 'Flyway Route',
          recommendationBody: 'Alternative path.',
          isSelected: false,
          selectionReason: '+6 higher risk score and 3 min slower effective travel time.',
          provenance: 'demo/mock',
        ),
      );

      final tripWithAlternatives = TripResponse(
        analysisId: 'alternatives-test-1',
        status: TripStatus.success,
        request: TripRequest(
          origin: 'Noida Sector 62',
          destination: 'Gurgaon Cyber Hub',
          departureTime: DateTime(2026, 8, 27, 8, 0),
          mode: TransportMode.car,
        ),
        risk: route1.risk,
        route: const [
          RouteSegment(
            startLat: 28.5355,
            startLng: 77.3910,
            endLat: 28.4595,
            endLng: 77.0266,
            riskLevel: RiskLevel.moderate,
            description: 'Take Noida-Greater Noida Expy',
          ),
        ],
        recommendation: const Recommendation(
          headline: 'Via Expressway Recommended',
          body: 'Optimal balance of safety and travel duration.',
          alternativeAction: 'proceed',
        ),
        modeOptions: const [],
        hazards: const [],
        sources: [
          DataSource(
            name: 'Open-Meteo',
            type: 'Weather',
            lastUpdated: DateTime(2026, 8, 27, 8, 0),
          ),
        ],
        estimatedDuration: static1,
        distanceKm: 35.5,
        traffic: traffic1,
        routes: [route1, route2],
      );

      // Verify on iPhone SE screen (375x667)
      await tester.binding.setSurfaceSize(const Size(375, 667));
      await tester.pumpWidget(_buildTestApp(
        screen: const TripAnalysisScreen(),
        size: const Size(375, 667),
        padding: const EdgeInsets.only(top: 20, bottom: 0),
        overrides: [
          tripResponseProvider.overrideWith((ref) => Future.value(tripWithAlternatives)),
        ],
      ));
      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull);

      // Scroll down to view Route Alternatives
      await tester.scrollUntilVisible(find.text('ROUTE ALTERNATIVES'), 100);
      await tester.pumpAndSettle();

      expect(find.text('ROUTE ALTERNATIVES'), findsOneWidget);
      expect(find.text('Via Expressway'), findsOneWidget);
      expect(find.text('Via DND Flyway'), findsOneWidget);

      // Initially route_1 is both RECOMMENDED and VIEWING
      expect(find.text('RECOMMENDED'), findsOneWidget);
      expect(find.text('VIEWING'), findsOneWidget);

      // Tap on route_2 card to inspect it
      final route2Finder = find.byKey(const Key('route_card_route_2'));
      expect(route2Finder, findsOneWidget);
      await tester.scrollUntilVisible(route2Finder, 100);
      await tester.pumpAndSettle();
      await tester.tap(route2Finder);
      await tester.pumpAndSettle();

      // After tap:
      // 1. RECOMMENDED remains exactly 1, still on route_1
      expect(find.text('RECOMMENDED'), findsOneWidget);
      // 2. VIEWING is still present, now for route_2 (activeRouteId updated)
      expect(find.text('VIEWING'), findsOneWidget);
      // 3. Backend recommendation is untouched
      expect(tripWithAlternatives.routes[0].evaluation.isSelected, isTrue);
      expect(tripWithAlternatives.routes[1].evaluation.isSelected, isFalse);

      // Verify no overflow error occurred
      expect(tester.takeException(), isNull);
    });

    testWidgets('What-If Screen renders correctly without overflow on iPhone SE', (tester) async {
      await tester.binding.setSurfaceSize(const Size(375, 667));
      await tester.pumpWidget(_buildTestApp(
        screen: const WhatIfScreen(),
        size: const Size(375, 667),
        padding: const EdgeInsets.only(top: 20, bottom: 0),
      ));
      await tester.pumpAndSettle();

      expect(find.text('What-If Simulator'), findsOneWidget);
      expect(find.text('DEPARTURE TIME'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('Mode Comparison Screen renders correctly and allows switching modes', (tester) async {
      FlutterErrorDetails? caughtDetails;
      final originalOnError = FlutterError.onError;
      FlutterError.onError = (details) {
        caughtDetails = details;
      };

      await tester.binding.setSurfaceSize(const Size(393, 852));
      await tester.pumpWidget(_buildTestApp(screen: const ModeComparisonScreen()));
      await tester.pumpAndSettle();

      FlutterError.onError = originalOnError;
      if (caughtDetails != null) {
        // ignore: avoid_print
        print('MODE COMPARISON OVERFLOW:\n${caughtDetails!.toString()}');
      }

      expect(find.text('Compare Modes'), findsOneWidget);
      expect(caughtDetails, isNull);
    });

    testWidgets('Risk & Confidence Screen renders breakdown and data sources', (tester) async {
      await tester.binding.setSurfaceSize(const Size(393, 852));
      await tester.pumpWidget(_buildTestApp(screen: const RiskConfidenceScreen()));
      await tester.pumpAndSettle();

      expect(find.text('Risk & Confidence'), findsOneWidget);
      expect(find.text('DATA SOURCES'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('Official Alert Screen renders details with provenance', (tester) async {
      await tester.binding.setSurfaceSize(const Size(393, 852));
      await tester.pumpWidget(_buildTestApp(screen: const OfficialAlertScreen()));
      await tester.pumpAndSettle();

      expect(find.text('Alert Details'), findsOneWidget);
      expect(find.text('Issued By'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('Local Hazard Screen renders hazard details and map', (tester) async {
      await tester.binding.setSurfaceSize(const Size(393, 852));
      await tester.pumpWidget(_buildTestApp(screen: const LocalHazardScreen()));
      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull);
    });

    testWidgets('Alerts Feed Screen renders list and handles empty state', (tester) async {
      await tester.binding.setSurfaceSize(const Size(393, 852));
      await tester.pumpWidget(_buildTestApp(screen: const AlertsFeedScreen()));
      await tester.pumpAndSettle();

      expect(find.text('Alerts'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('Historical Replay Screen renders event timeline', (tester) async {
      await tester.binding.setSurfaceSize(const Size(393, 852));
      await tester.pumpWidget(_buildTestApp(screen: const HistoricalReplayScreen()));
      await tester.pumpAndSettle();

      expect(find.text('Historical Replay'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('Voice Input Screen renders on iPhone SE without overflow', (tester) async {
      await tester.binding.setSurfaceSize(const Size(375, 667));
      await tester.pumpWidget(_buildTestApp(
        screen: const VoiceInputScreen(),
        size: const Size(375, 667),
        padding: const EdgeInsets.only(top: 20, bottom: 0),
      ));
      await tester.pump(const Duration(milliseconds: 300));

      expect(find.text('Voice Input'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('Assistant Screen renders chat interface and input bar', (tester) async {
      await tester.binding.setSurfaceSize(const Size(393, 852));
      await tester.pumpWidget(_buildTestApp(screen: const AssistantScreen()));
      await tester.pumpAndSettle();

      expect(find.text('WeatherGPT'), findsOneWidget);
      expect(find.byType(TextField), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('Profile Screen renders user settings and preferences', (tester) async {
      await tester.binding.setSurfaceSize(const Size(393, 852));
      final authService = MockAuthService(
        initialUser: const AppUser(
          uid: 'user-om',
          email: 'om@weathergpt.com',
          displayName: 'Om Gangwar',
        ),
      );
      await tester.pumpWidget(_buildTestApp(
        screen: const ProfileScreen(),
        overrides: [
          authServiceProvider.overrideWithValue(authService),
        ],
      ));
      await tester.pumpAndSettle();

      expect(find.text('Profile'), findsOneWidget);
      expect(find.text('Om Gangwar'), findsOneWidget);
      expect(find.text('SAVED ROUTES'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });
}
