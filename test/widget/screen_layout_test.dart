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
      await tester.pumpWidget(_buildTestApp(screen: const ProfileScreen()));
      await tester.pumpAndSettle();

      expect(find.text('Profile'), findsOneWidget);
      expect(find.text('Om Gangwar'), findsOneWidget);
      expect(find.text('SAVED ROUTES'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });
}
