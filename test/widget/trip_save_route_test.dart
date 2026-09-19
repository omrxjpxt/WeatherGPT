import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:weather_gpt/features/trip_analysis/trip_analysis_screen.dart';
import 'package:weather_gpt/models/models.dart';
import 'package:weather_gpt/repositories/repositories.dart';
import 'package:weather_gpt/core/auth/auth_service.dart';
import 'package:weather_gpt/core/auth/mock_auth_service.dart';
import 'package:weather_gpt/repositories/mock_repositories.dart';
import 'package:weather_gpt/core/theme/app_theme.dart';
import 'package:weather_gpt/core/providers.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  final testTripResponse = TripResponse(
    request: TripRequest(
      origin: 'Noida Sector 62',
      destination: 'Gurgaon Cyber Hub',
      departureTime: DateTime.utc(2026, 9, 19, 8, 0),
      mode: TransportMode.bike,
    ),
    route: [
      RouteSegment(
        startLat: 28.62,
        startLng: 77.36,
        endLat: 28.49,
        endLng: 77.08,
        riskLevel: RiskLevel.low,
        description: 'Via Noida-Greater Noida Expy',
      ),
    ],
    modeOptions: const [],
    hazards: const [],
    sources: const [],
    estimatedDuration: const Duration(minutes: 42),
    distanceKm: 34.0,
    status: TripStatus.success,
    risk: const RiskAssessment(
      overallScore: 20,
      level: RiskLevel.low,
      confidence: Confidence(level: ConfidenceLevel.high, explanation: 'High data quality'),
      summary: 'Safe travel conditions with light traffic.',
      factors: [],
    ),
  );

  Widget buildTestableWidget({
    required Widget child,
    required AuthService authService,
    required UserRepository userRepository,
    Size surfaceSize = const Size(393, 852),
  }) {
    return ProviderScope(
      overrides: [
        authServiceProvider.overrideWithValue(authService),
        userRepositoryProvider.overrideWithValue(userRepository),
        tripResponseProvider.overrideWith((ref) async => testTripResponse),
      ],
      child: MaterialApp(
        theme: AppTheme.light,
        home: MediaQuery(
          data: MediaQueryData(
            size: surfaceSize,
            padding: const EdgeInsets.only(top: 59, bottom: 34),
            viewInsets: EdgeInsets.zero,
          ),
          child: child,
        ),
      ),
    );
  }

  group('TripAnalysisScreen Save Route Tests', () {
    testWidgets('Guest sees authentication prompt modal when tapping Save Route', (tester) async {
      await tester.binding.setSurfaceSize(const Size(393, 852));

      final authService = MockAuthService(); // unauthenticated by default
      final userRepo = MockUserRepository();

      await tester.pumpWidget(buildTestableWidget(
        child: const TripAnalysisScreen(),
        authService: authService,
        userRepository: userRepo,
      ));
      await tester.pumpAndSettle();

      // Scroll down to action buttons
      await tester.scrollUntilVisible(
        find.text('Save Route'),
        200,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.pumpAndSettle();

      final saveBtn = find.text('Save Route');
      expect(saveBtn, findsOneWidget);

      await tester.tap(saveBtn);
      await tester.pumpAndSettle();

      // Verify authentication requirement prompt is presented
      expect(find.text('Sign in to save this route to your profile and sync across devices.'), findsOneWidget);
      expect(find.text('Continue as Guest'), findsOneWidget);
      expect(find.text('Sign In / Create Account'), findsOneWidget);

      // Dismiss dialog
      await tester.tap(find.text('Continue as Guest'));
      await tester.pumpAndSettle();

      expect(find.text('Sign in to save this route to your profile and sync across devices.'), findsNothing);
    });

    testWidgets('Authenticated user saves route and sees success feedback', (tester) async {
      await tester.binding.setSurfaceSize(const Size(393, 852));

      final authService = MockAuthService(
        initialUser: const AppUser(uid: 'auth-user-om', email: 'om@weathergpt.com'),
      );
      final userRepo = MockUserRepository();

      await tester.pumpWidget(buildTestableWidget(
        child: const TripAnalysisScreen(),
        authService: authService,
        userRepository: userRepo,
      ));
      await tester.pumpAndSettle();

      // Scroll down to action buttons
      await tester.scrollUntilVisible(
        find.text('Save Route'),
        200,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.pumpAndSettle();

      final saveBtn = find.text('Save Route');
      expect(saveBtn, findsOneWidget);

      await tester.tap(saveBtn);
      await tester.pumpAndSettle();

      // Verify SnackBar feedback
      expect(find.text('Route saved to your profile'), findsOneWidget);

      // Verify saved routes in repository contains the newly saved route
      final savedRoutes = await tester.runAsync(() => userRepo.getSavedRoutes());
      expect(savedRoutes!.any((r) => r.originId == 'Noida Sector 62' && r.destinationId == 'Gurgaon Cyber Hub'), isTrue);
    });
  });
}
