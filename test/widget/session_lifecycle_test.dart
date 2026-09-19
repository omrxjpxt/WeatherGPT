import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:weather_gpt/core/auth/auth_service.dart';
import 'package:weather_gpt/core/auth/mock_auth_service.dart';
import 'package:weather_gpt/core/providers.dart';
import 'package:weather_gpt/core/theme/app_theme.dart';
import 'package:weather_gpt/features/assistant/assistant_screen.dart';
import 'package:weather_gpt/features/profile/profile_screen.dart';
import 'package:weather_gpt/models/models.dart';
import 'package:weather_gpt/repositories/repositories.dart';
import 'package:weather_gpt/repositories/mock_repositories.dart';

/// A test repository that isolates data by the currently authenticated user UID.
class AccountIsolationUserRepository implements UserRepository {
  final AuthService _auth;

  final Map<String, UserProfile> profiles = {
    'user-alice': UserProfile(
      uid: 'user-alice',
      email: 'alice@weathergpt.com',
      displayName: 'Alice Wonderland',
    ),
    'user-bob': UserProfile(
      uid: 'user-bob',
      email: 'bob@weathergpt.com',
      displayName: 'Bob Builder',
    ),
  };

  final Map<String, List<SavedRoute>> routesByUser = {
    'user-alice': [
      SavedRoute(
        id: 'alice-route-1',
        name: 'Alice Home → Tech Park',
        originId: 'Noida Sector 18',
        destinationId: 'Cyber City',
        createdAt: DateTime.utc(2026, 9, 1),
      ),
    ],
    'user-bob': [
      SavedRoute(
        id: 'bob-route-1',
        name: 'Bob DTU → Connaught Place',
        originId: 'Rohini',
        destinationId: 'CP Central',
        createdAt: DateTime.utc(2026, 9, 5),
      ),
    ],
  };

  final Map<String, List<TripHistorySummary>> historyByUser = {
    'user-alice': [
      TripHistorySummary(
        analysisId: 'alice-hist-1',
        status: 'success',
        origin: 'Noida Sector 18',
        destination: 'Cyber City',
        mode: 'car',
        riskLevel: 'low',
        recommendationHeadline: 'Clear corridor',
        createdAt: DateTime.utc(2026, 9, 10),
        isSnapshot: true,
      ),
    ],
    'user-bob': [
      TripHistorySummary(
        analysisId: 'bob-hist-1',
        status: 'success',
        origin: 'Rohini',
        destination: 'CP Central',
        mode: 'metro',
        riskLevel: 'moderate',
        recommendationHeadline: 'Moderate congestion',
        createdAt: DateTime.utc(2026, 9, 12),
        isSnapshot: true,
      ),
    ],
  };

  AccountIsolationUserRepository(this._auth);

  String get _currentUid => _auth.currentUser?.uid ?? 'guest';

  @override
  Future<UserProfile> getProfile() async {
    return profiles[_currentUid] ??
        UserProfile(uid: _currentUid, email: 'guest@example.com', displayName: 'Guest');
  }

  @override
  Future<UserProfile> updateProfile(UserProfile profile) async {
    profiles[_currentUid] = profile;
    return profile;
  }

  @override
  Future<List<SavedRoute>> getSavedRoutes() async {
    return List.unmodifiable(routesByUser[_currentUid] ?? []);
  }

  @override
  Future<SavedRoute> saveRoute(SavedRoute route) async {
    final list = routesByUser.putIfAbsent(_currentUid, () => []);
    list.removeWhere((r) => r.id == route.id);
    list.insert(0, route);
    return route;
  }

  @override
  Future<void> deleteSavedRoute(String savedRouteId) async {
    routesByUser[_currentUid]?.removeWhere((r) => r.id == savedRouteId);
  }

  @override
  Future<List<TripHistorySummary>> getTripHistory() async {
    return List.unmodifiable(historyByUser[_currentUid] ?? []);
  }

  @override
  Future<TripResponse> getTripDetail(String analysisId) async {
    final tripRepo = MockTripRepository();
    return tripRepo.analyzeTrip(TripRequest(
      origin: 'A',
      destination: 'B',
      departureTime: DateTime(2026, 9, 18, 9, 30),
      mode: TransportMode.car,
    ));
  }

  @override
  Future<List<ConversationSummary>> getConversations() async {
    return const [];
  }
}

class FakeAssistantRepository implements AssistantRepository {
  int requestCount = 0;
  String? lastConversationId;

  @override
  Future<AssistantChatResponse> chat(AssistantChatRequest request) async {
    requestCount++;
    lastConversationId = request.conversationId ?? 'conv-$requestCount';
    return AssistantChatResponse(
      message: 'Route from ${request.message} evaluated: low risk score 18/100.',
      intent: const ExtractedIntent(origin: 'Noida', destination: 'Gurgaon'),
      conversationId: lastConversationId,
      status: 'success',
      provenance: 'test/mock',
    );
  }

  @override
  Future<AssistantParseResponse> parseIntent(String query, {DateTime? referenceTime}) async {
    return const AssistantParseResponse(
      intent: ExtractedIntent(origin: 'Noida', destination: 'Gurgaon'),
      isComplete: true,
    );
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  Widget buildTestApp({
    Key? key,
    required Widget child,
    required AuthService authService,
    required UserRepository userRepository,
    AssistantRepository? assistantRepository,
    Size surfaceSize = const Size(393, 852),
    EdgeInsets padding = const EdgeInsets.only(top: 59, bottom: 34),
  }) {
    return ProviderScope(
      key: key,
      overrides: [
        authServiceProvider.overrideWithValue(authService),
        userRepositoryProvider.overrideWithValue(userRepository),
        if (assistantRepository != null)
          assistantRepositoryProvider.overrideWithValue(assistantRepository),
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

  group('Session Lifecycle & State Invalidation Tests', () {
    testWidgets('Sign-out invalidates user providers and transitions cleanly to Guest state', (tester) async {
      await tester.binding.setSurfaceSize(const Size(393, 852));

      final authService = MockAuthService(
        initialUser: const AppUser(
          uid: 'user-alice',
          email: 'alice@weathergpt.com',
          displayName: 'Alice Wonderland',
        ),
      );
      final userRepo = AccountIsolationUserRepository(authService);

      await tester.pumpWidget(buildTestApp(
        child: const ProfileScreen(),
        authService: authService,
        userRepository: userRepo,
      ));
      await tester.pumpAndSettle();

      // Verify authenticated view displays Alice's data
      expect(find.text('Alice Wonderland'), findsOneWidget);
      expect(find.text('Alice Home → Tech Park'), findsOneWidget);
      expect(find.text('Clear corridor'), findsOneWidget);

      // Scroll to sign out button
      await tester.drag(find.byType(SingleChildScrollView), const Offset(0, -900));
      await tester.pumpAndSettle();

      final signOutBtn = find.text('Sign Out');
      expect(signOutBtn, findsOneWidget);
      await tester.tap(signOutBtn);
      await tester.pumpAndSettle();

      // Verify guest state is rendered
      expect(find.text('Guest Traveler'), findsOneWidget);
      expect(find.text('Free trip analysis mode'), findsOneWidget);
      expect(find.text('Alice Wonderland'), findsNothing);
      expect(find.text('Alice Home → Tech Park'), findsNothing);
      expect(tester.takeException(), isNull);
    });

    testWidgets('Switching accounts isolates data without stale cache bleed', (tester) async {
      await tester.binding.setSurfaceSize(const Size(393, 852));

      final authService = MockAuthService();
      final userRepo = AccountIsolationUserRepository(authService);

      // 1. Initial Guest view
      await tester.pumpWidget(buildTestApp(
        child: const ProfileScreen(),
        authService: authService,
        userRepository: userRepo,
      ));
      await tester.pumpAndSettle();
      expect(find.text('Guest Traveler'), findsOneWidget);

      // 2. Sign in as Alice
      await authService.signInWithMockCredentials(
        uid: 'user-alice',
        email: 'alice@weathergpt.com',
        displayName: 'Alice Wonderland',
      );
      // Trigger ProviderContainer rebuild
      final element = tester.element(find.byType(ProfileScreen));
      final container = ProviderScope.containerOf(element);
      await container.read(authStateProvider.notifier).signInWithMockUser(
        uid: 'user-alice',
        email: 'alice@weathergpt.com',
        displayName: 'Alice Wonderland',
      );
      await tester.pumpAndSettle();

      // Alice's data visible
      expect(find.text('Alice Wonderland'), findsOneWidget);
      expect(find.text('Alice Home → Tech Park'), findsOneWidget);
      expect(find.text('Bob DTU → Connaught Place'), findsNothing);

      // 3. Sign out Alice
      await container.read(authStateProvider.notifier).signOut();
      await tester.pumpAndSettle();
      expect(find.text('Guest Traveler'), findsOneWidget);

      // 4. Sign in as Bob
      await container.read(authStateProvider.notifier).signInWithMockUser(
        uid: 'user-bob',
        email: 'bob@weathergpt.com',
        displayName: 'Bob Builder',
      );
      await tester.pumpAndSettle();

      // Bob's data visible, Alice's data strictly absent
      expect(find.text('Bob Builder'), findsOneWidget);
      expect(find.text('Bob DTU → Connaught Place'), findsOneWidget);
      expect(find.text('Alice Wonderland'), findsNothing);
      expect(find.text('Alice Home → Tech Park'), findsNothing);
      expect(tester.takeException(), isNull);
    });

    testWidgets('Assistant New Conversation option resets conversation and messages', (tester) async {
      await tester.binding.setSurfaceSize(const Size(393, 852));

      final authService = MockAuthService();
      final userRepo = AccountIsolationUserRepository(authService);
      final assistantRepo = FakeAssistantRepository();

      await tester.pumpWidget(buildTestApp(
        child: const AssistantScreen(),
        authService: authService,
        userRepository: userRepo,
        assistantRepository: assistantRepo,
      ));
      await tester.pumpAndSettle();

      // Initial welcome message
      expect(find.textContaining('Good morning!'), findsOneWidget);

      // Send first message
      await tester.enterText(find.byType(TextField), 'Trip to Gurgaon');
      await tester.testTextInput.receiveAction(TextInputAction.done);
      await tester.pumpAndSettle();

      expect(find.text('Trip to Gurgaon'), findsOneWidget);
      expect(find.textContaining('Route from Trip to Gurgaon evaluated'), findsOneWidget);

      // Tap conversation options popup menu
      final optionsBtn = find.byTooltip('Conversation Options');
      expect(optionsBtn, findsOneWidget);
      await tester.tap(optionsBtn);
      await tester.pumpAndSettle();

      // Tap 'New Conversation'
      final newConvItem = find.text('New Conversation');
      expect(newConvItem, findsOneWidget);
      await tester.tap(newConvItem);
      await tester.pumpAndSettle();

      // Previous user message should be cleared, welcome message remains
      expect(find.text('Trip to Gurgaon'), findsNothing);
      expect(find.textContaining('Route from Trip to Gurgaon evaluated'), findsNothing);
      expect(find.textContaining('Good morning!'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('Responsive verification on iPhone SE (375x667) without overflow', (tester) async {
      await tester.binding.setSurfaceSize(const Size(375, 667));

      final authService = MockAuthService(
        initialUser: const AppUser(
          uid: 'user-bob',
          email: 'bob@weathergpt.com',
          displayName: 'Bob Builder',
        ),
      );
      final userRepo = AccountIsolationUserRepository(authService);
      final assistantRepo = FakeAssistantRepository();

      // iPhone SE: Profile
      await tester.pumpWidget(buildTestApp(
        key: const ValueKey('profile-se'),
        child: const ProfileScreen(),
        authService: authService,
        userRepository: userRepo,
        surfaceSize: const Size(375, 667),
        padding: const EdgeInsets.only(top: 20, bottom: 0),
      ));
      await tester.pumpAndSettle();
      expect(find.text('Bob Builder'), findsOneWidget);
      expect(find.text('Bob DTU → Connaught Place'), findsOneWidget);
      expect(tester.takeException(), isNull);

      // iPhone SE: Assistant
      await tester.pumpWidget(buildTestApp(
        key: const ValueKey('assistant-se'),
        child: const AssistantScreen(),
        authService: authService,
        userRepository: userRepo,
        assistantRepository: assistantRepo,
        surfaceSize: const Size(375, 667),
        padding: const EdgeInsets.only(top: 20, bottom: 0),
      ));
      await tester.pumpAndSettle();
      expect(find.text('WeatherGPT'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('Responsive verification on iPhone 15 Pro (393x852) without overflow', (tester) async {
      await tester.binding.setSurfaceSize(const Size(393, 852));

      final authService = MockAuthService(
        initialUser: const AppUser(
          uid: 'user-bob',
          email: 'bob@weathergpt.com',
          displayName: 'Bob Builder',
        ),
      );
      final userRepo = AccountIsolationUserRepository(authService);
      final assistantRepo = FakeAssistantRepository();

      // iPhone 15 Pro: Profile
      await tester.pumpWidget(buildTestApp(
        key: const ValueKey('profile-pro'),
        child: const ProfileScreen(),
        authService: authService,
        userRepository: userRepo,
        surfaceSize: const Size(393, 852),
      ));
      await tester.pumpAndSettle();
      expect(find.text('Bob Builder'), findsOneWidget);
      expect(find.text('Bob DTU → Connaught Place'), findsOneWidget);
      expect(tester.takeException(), isNull);

      // iPhone 15 Pro: Assistant
      await tester.pumpWidget(buildTestApp(
        key: const ValueKey('assistant-pro'),
        child: const AssistantScreen(),
        authService: authService,
        userRepository: userRepo,
        assistantRepository: assistantRepo,
        surfaceSize: const Size(393, 852),
      ));
      await tester.pumpAndSettle();
      expect(find.text('WeatherGPT'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });
}
