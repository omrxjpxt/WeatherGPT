import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:weather_gpt/features/profile/profile_screen.dart';
import 'package:weather_gpt/features/profile/auth_dialog.dart';
import 'package:weather_gpt/core/auth/auth_service.dart';
import 'package:weather_gpt/core/auth/mock_auth_service.dart';
import 'package:weather_gpt/repositories/repositories.dart';
import 'package:weather_gpt/repositories/mock_repositories.dart';
import 'package:weather_gpt/core/theme/app_theme.dart';
import 'package:weather_gpt/core/providers.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  Widget buildTestableWidget({
    required Widget child,
    required AuthService authService,
    required UserRepository userRepository,
    Size surfaceSize = const Size(393, 852),
    EdgeInsets padding = const EdgeInsets.only(top: 59, bottom: 34),
  }) {
    return ProviderScope(
      overrides: [
        authServiceProvider.overrideWithValue(authService),
        userRepositoryProvider.overrideWithValue(userRepository),
      ],
      child: MaterialApp(
        theme: AppTheme.light,
        home: MediaQuery(
          data: MediaQueryData(
            size: surfaceSize,
            padding: padding,
            viewInsets: EdgeInsets.zero,
          ),
          child: child,
        ),
      ),
    );
  }

  group('Profile Screen Auth & Persistence Flow Tests', () {
    testWidgets('Guest traveler renders on iPhone SE without overflow', (tester) async {
      await tester.binding.setSurfaceSize(const Size(375, 667));

      final authService = MockAuthService();
      final userRepo = MockUserRepository();

      await tester.pumpWidget(buildTestableWidget(
        child: const ProfileScreen(),
        authService: authService,
        userRepository: userRepo,
        surfaceSize: const Size(375, 667),
        padding: const EdgeInsets.only(top: 20, bottom: 0),
      ));
      await tester.pumpAndSettle();

      expect(find.text('Profile'), findsOneWidget);
      expect(find.text('Guest Traveler'), findsOneWidget);
      expect(find.text('Free trip analysis mode'), findsOneWidget);
      expect(find.text('Sign In / Create Account'), findsOneWidget);
      expect(find.text('Sign in to access and manage your saved commutes across devices.'), findsOneWidget);
      expect(find.text('Sign in to view your past trip analyses and historical snapshots.'), findsOneWidget);

      expect(tester.takeException(), isNull);
    });

    testWidgets('Guest can open AuthDialog and perform Quick Demo Sign-In', (tester) async {
      await tester.binding.setSurfaceSize(const Size(393, 852));

      final authService = MockAuthService();
      final userRepo = MockUserRepository();

      await tester.pumpWidget(buildTestableWidget(
        child: const ProfileScreen(),
        authService: authService,
        userRepository: userRepo,
      ));
      await tester.pumpAndSettle();

      // Tap Sign In / Create Account button on guest card
      final ctaBtn = find.text('Sign In / Create Account');
      expect(ctaBtn, findsOneWidget);
      await tester.tap(ctaBtn);
      await tester.pumpAndSettle();

      // AuthDialog should be visible
      expect(find.byType(AuthDialog), findsOneWidget);
      expect(find.text('Quick Demo Sign-In'), findsOneWidget);

      // Tap Quick Demo Sign-In
      await tester.tap(find.text('Quick Demo Sign-In'));
      await tester.pumpAndSettle();

      // Auth dialog should dismiss and user should now be signed in
      expect(find.byType(AuthDialog), findsNothing);
      expect(authService.currentUser, isNotNull);
      expect(find.text('Sign Out'), findsOneWidget);
    });

    testWidgets('Authenticated traveler renders saved routes and trip history on iPhone 15 Pro', (tester) async {
      await tester.binding.setSurfaceSize(const Size(393, 852));

      final authService = MockAuthService(
        initialUser: const AppUser(
          uid: 'user-om-123456789',
          email: 'om@weathergpt.com',
          displayName: 'Om Gangwar',
        ),
      );
      final userRepo = MockUserRepository();

      await tester.pumpWidget(buildTestableWidget(
        child: const ProfileScreen(),
        authService: authService,
        userRepository: userRepo,
      ));
      await tester.pumpAndSettle();

      // Verify authenticated identity card
      expect(find.text('Om Gangwar'), findsOneWidget);
      expect(find.text('om@weathergpt.com'), findsOneWidget);
      expect(find.textContaining('UID: user-om-123'), findsOneWidget);

      // Verify Saved Routes
      expect(find.text('Home → Office'), findsOneWidget);
      expect(find.text('Noida Sector 62 → Gurgaon Cyber Hub'), findsWidgets);
      expect(find.text('Home → DTU'), findsOneWidget);

      // Verify Trip History
      expect(find.text('Historical Snapshot (Audit)'), findsWidgets);
      expect(find.text('Clear route via Noida-Greater Noida Expy'), findsOneWidget);

      // Scroll down to Sign Out
      await tester.drag(find.byType(SingleChildScrollView), const Offset(0, -500));
      await tester.pumpAndSettle();

      // Verify Sign Out button
      expect(find.text('Sign Out'), findsOneWidget);

      expect(tester.takeException(), isNull);
    });

    testWidgets('Authenticated traveler renders on iPhone SE (375x667) without overflow', (tester) async {
      await tester.binding.setSurfaceSize(const Size(375, 667));

      final authService = MockAuthService(
        initialUser: const AppUser(
          uid: 'user-om-se',
          email: 'om@weathergpt.com',
          displayName: 'Om Gangwar',
        ),
      );
      final userRepo = MockUserRepository();

      await tester.pumpWidget(buildTestableWidget(
        child: const ProfileScreen(),
        authService: authService,
        userRepository: userRepo,
        surfaceSize: const Size(375, 667),
        padding: const EdgeInsets.only(top: 20, bottom: 0),
      ));
      await tester.pumpAndSettle();

      expect(find.text('Om Gangwar'), findsOneWidget);
      expect(find.text('Home → Office'), findsOneWidget);
      expect(find.text('Historical Snapshot (Audit)'), findsWidgets);

      expect(tester.takeException(), isNull);
    });

    testWidgets('Authenticated user can delete a saved route and sign out', (tester) async {
      await tester.binding.setSurfaceSize(const Size(393, 852));

      final authService = MockAuthService(
        initialUser: const AppUser(
          uid: 'user-om-123456789',
          email: 'om@weathergpt.com',
          displayName: 'Om Gangwar',
        ),
      );
      final userRepo = MockUserRepository();

      await tester.pumpWidget(buildTestableWidget(
        child: const ProfileScreen(),
        authService: authService,
        userRepository: userRepo,
      ));
      await tester.pumpAndSettle();

      // Find trash button for saved routes
      final trashIcons = find.byTooltip('Delete saved route');
      expect(trashIcons, findsWidgets);

      // Delete the first saved route
      await tester.tap(trashIcons.first);
      await tester.pumpAndSettle();

      // Verify it was removed from UI
      expect(find.text('Home → Office'), findsNothing);

      // Verify it was removed from repository using runAsync to avoid FakeAsync stall
      final routesAfterDelete = await tester.runAsync(() => userRepo.getSavedRoutes());
      expect(routesAfterDelete!.any((r) => r.id == 'mock-route-1'), isFalse);

      // Now scroll down and tap Sign Out
      await tester.drag(find.byType(SingleChildScrollView), const Offset(0, -900));
      await tester.pumpAndSettle();

      expect(find.text('Sign Out'), findsOneWidget);
      await tester.tap(find.text('Sign Out'));
      await tester.pumpAndSettle();

      // Should return to guest state
      expect(find.text('Guest Traveler'), findsOneWidget);
      expect(find.text('Sign Out'), findsNothing);
      expect(authService.currentUser, isNull);
    });
  });
}
