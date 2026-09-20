import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/models.dart';
import '../repositories/repositories.dart';
import '../repositories/mock_repositories.dart';
import '../repositories/http/http_trip_repository.dart';
import '../repositories/http/http_weather_repository.dart';
import '../repositories/http/http_risk_repository.dart';
import '../repositories/http/http_alert_repository.dart';
import '../repositories/http/http_assistant_repository.dart';
import '../repositories/http/http_user_repository.dart';
import 'auth/auth_service.dart';
import 'auth/firebase_auth_service.dart';
import 'auth/mock_auth_service.dart';
import 'auth/firebase_init.dart';
import 'api/api_config.dart';
import 'api/api_client.dart';

// ── Auth Service & State ──

final authServiceProvider = Provider<AuthService>((ref) {
  if (ApiConfig.mode == AppMode.live && FirebaseInit.isInitialized) {
    return FirebaseAuthService();
  }
  return MockAuthService();
});

class AuthNotifier extends Notifier<AuthState> {
  @override
  AuthState build() {
    final authService = ref.watch(authServiceProvider);
    final subscription = authService.authStateChanges.listen((user) {
      state = state.copyWith(user: user, clearUser: user == null, isLoading: false, error: null);
    });
    ref.onDispose(subscription.cancel);

    return AuthState(user: authService.currentUser);
  }

  Future<void> signInWithEmail(String email, String password) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final user = await ref.read(authServiceProvider).signInWithEmailAndPassword(email, password);
      state = state.copyWith(user: user, isLoading: false);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
      rethrow;
    }
  }

  Future<void> createUserWithEmail(String email, String password) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final user = await ref.read(authServiceProvider).createUserWithEmailAndPassword(email, password);
      state = state.copyWith(user: user, isLoading: false);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
      rethrow;
    }
  }

  Future<void> signInWithMockUser({
    String uid = 'test-user-id',
    String email = 'test@example.com',
    String displayName = 'Demo Traveler',
  }) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final user = await ref.read(authServiceProvider).signInWithMockCredentials(
        uid: uid,
        email: email,
        displayName: displayName,
      );
      state = state.copyWith(user: user, isLoading: false);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
      rethrow;
    }
  }

  Future<void> signOut() async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      await ref.read(authServiceProvider).signOut();
      state = const AuthState(user: null, isLoading: false);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
      rethrow;
    }
  }
}

final authStateProvider = NotifierProvider<AuthNotifier, AuthState>(AuthNotifier.new);

// ── API Client Provider ──
final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient(
    tokenProvider: () async {
      final auth = ref.read(authServiceProvider);
      return auth.getIdToken();
    },
  );
});

// ── Repository Providers ──

final tripRepositoryProvider = Provider<TripRepository>((ref) {
  if (ApiConfig.mode == AppMode.live) {
    return HttpTripRepository(ref.read(apiClientProvider));
  }
  return MockTripRepository();
});

final weatherRepositoryProvider = Provider<WeatherRepository>((ref) {
  if (ApiConfig.mode == AppMode.live) {
    return HttpWeatherRepository(ref.read(apiClientProvider));
  }
  return MockWeatherRepository();
});

final riskRepositoryProvider = Provider<RiskRepository>((ref) {
  if (ApiConfig.mode == AppMode.live) {
    return HttpRiskRepository(ref.read(apiClientProvider), ref.read(tripRepositoryProvider));
  }
  return MockRiskRepository();
});

final alertRepositoryProvider = Provider<AlertRepository>((ref) {
  if (ApiConfig.mode == AppMode.live) {
    return HttpAlertRepository(ref.read(apiClientProvider));
  }
  return MockAlertRepository();
});

final historyRepositoryProvider = Provider<HistoryRepository>((ref) {
  // History is always mock for now since there's no backend for it in this MVP
  return MockHistoryRepository();
});

final assistantRepositoryProvider = Provider<AssistantRepository>((ref) {
  if (ApiConfig.mode == AppMode.live) {
    return HttpAssistantRepository(ref.read(apiClientProvider));
  }
  return MockAssistantRepository();
});

final userRepositoryProvider = Provider<UserRepository>((ref) {
  if (ApiConfig.mode == AppMode.live) {
    return HttpUserRepository(ref.read(apiClientProvider));
  }
  return MockUserRepository();
});

// ── User Persistence Providers ──

final userProfileProvider = FutureProvider<UserProfile?>((ref) async {
  final authState = ref.watch(authStateProvider);
  if (!authState.isAuthenticated) return null;
  final repo = ref.read(userRepositoryProvider);
  return repo.getProfile();
});

class SavedRoutesNotifier extends AsyncNotifier<List<SavedRoute>> {
  @override
  Future<List<SavedRoute>> build() async {
    final authState = ref.watch(authStateProvider);
    if (!authState.isAuthenticated) return const [];
    final repo = ref.read(userRepositoryProvider);
    return repo.getSavedRoutes();
  }

  Future<void> saveRoute(SavedRoute route) async {
    final repo = ref.read(userRepositoryProvider);
    await repo.saveRoute(route);
    state = await AsyncValue.guard(() => repo.getSavedRoutes());
  }

  Future<void> deleteRoute(String savedRouteId) async {
    final repo = ref.read(userRepositoryProvider);
    await repo.deleteSavedRoute(savedRouteId);
    state = await AsyncValue.guard(() => repo.getSavedRoutes());
  }
}

final userSavedRoutesProvider =
    AsyncNotifierProvider<SavedRoutesNotifier, List<SavedRoute>>(SavedRoutesNotifier.new);

final userTripHistoryProvider = FutureProvider<List<TripHistorySummary>>((ref) async {
  final authState = ref.watch(authStateProvider);
  if (!authState.isAuthenticated) return const [];
  final repo = ref.read(userRepositoryProvider);
  return repo.getTripHistory();
});

final userConversationsProvider = FutureProvider<List<ConversationSummary>>((ref) async {
  final authState = ref.watch(authStateProvider);
  if (!authState.isAuthenticated) return const [];
  final repo = ref.read(userRepositoryProvider);
  return repo.getConversations();
});


// ── Trip State ──

class TripRequestNotifier extends Notifier<TripRequest> {
  @override
  TripRequest build() {
    return TripRequest(
      origin: 'Noida Sector 62',
      destination: 'Gurgaon Cyber Hub',
      departureTime: DateTime.now().add(const Duration(minutes: 15)),
      mode: TransportMode.bike,
    );
  }

  void update(TripRequest request) => state = request;

  void adjustDeparture(Duration offset) {
    state = TripRequest(
      origin: state.origin,
      destination: state.destination,
      departureTime: state.departureTime.add(offset),
      mode: state.mode,
    );
  }

  void setDepartureFromNow(Duration offset) {
    state = TripRequest(
      origin: state.origin,
      destination: state.destination,
      departureTime: DateTime.now().add(offset),
      mode: state.mode,
    );
  }
}

final activeTripRequestProvider =
    NotifierProvider<TripRequestNotifier, TripRequest>(TripRequestNotifier.new);

final tripResponseProvider = FutureProvider<TripResponse>((ref) async {
  final request = ref.watch(activeTripRequestProvider);
  final repo = ref.read(tripRepositoryProvider);
  return repo.analyzeTrip(request);
});

// ── Scenario / What-If State ──

class ScenarioTimeNotifier extends Notifier<DateTime> {
  @override
  DateTime build() => DateTime.now().add(const Duration(minutes: 15));

  void update(DateTime time) => state = time;
}

final scenarioTimeProvider =
    NotifierProvider<ScenarioTimeNotifier, DateTime>(ScenarioTimeNotifier.new);

final scenarioResultsProvider = FutureProvider<List<ScenarioResult>>((ref) async {
  final request = ref.watch(activeTripRequestProvider);
  final repo = ref.read(tripRepositoryProvider);
  final baseTime = DateTime.now().add(const Duration(minutes: 15)); // starting point
  final times = List.generate(13, (i) => baseTime.add(Duration(minutes: i * 30)));
  return repo.simulateScenarios(request, times);
});

// ── Mode Comparison State ──

class SelectedModeNotifier extends Notifier<TransportMode> {
  @override
  TransportMode build() => TransportMode.bike;

  void update(TransportMode mode) => state = mode;
}

final selectedModeProvider =
    NotifierProvider<SelectedModeNotifier, TransportMode>(SelectedModeNotifier.new);

final modeComparisonProvider = FutureProvider<List<ModeOption>>((ref) async {
  final request = ref.watch(activeTripRequestProvider);
  final repo = ref.read(tripRepositoryProvider);
  return repo.compareModes(
    request.origin,
    request.destination,
    request.departureTime,
  );
});

// ── Weather State ──

final currentWeatherProvider = FutureProvider<WeatherPoint>((ref) async {
  final repo = ref.read(weatherRepositoryProvider);
  return repo.getCurrentWeather('Noida Sector 62');
});

final forecastProvider = FutureProvider<List<WeatherPoint>>((ref) async {
  final repo = ref.read(weatherRepositoryProvider);
  return repo.getForecast('Noida Sector 62');
});

// ── Alerts State ──

final activeAlertsProvider = FutureProvider<List<OfficialAlert>>((ref) async {
  final repo = ref.read(alertRepositoryProvider);
  return repo.getActiveAlerts();
});

// ── Historical State ──

final historicalEventsProvider = FutureProvider<List<HistoricalEvent>>((ref) async {
  final repo = ref.read(historyRepositoryProvider);
  return repo.getHistoricalEvents('Delhi-NCR');
});

// ── Voice Session State ──

class VoiceSessionState {
  final bool isListening;
  final String transcript;
  final TripRequest? extractedTrip;

  const VoiceSessionState({
    this.isListening = false,
    this.transcript = '',
    this.extractedTrip,
  });

  VoiceSessionState copyWith({
    bool? isListening,
    String? transcript,
    TripRequest? extractedTrip,
  }) {
    return VoiceSessionState(
      isListening: isListening ?? this.isListening,
      transcript: transcript ?? this.transcript,
      extractedTrip: extractedTrip ?? this.extractedTrip,
    );
  }
}

class VoiceSessionNotifier extends Notifier<VoiceSessionState> {
  @override
  VoiceSessionState build() => const VoiceSessionState();

  void startListening() {
    state = state.copyWith(isListening: true, transcript: '');
  }

  void stopListening() {
    state = state.copyWith(isListening: false);
  }

  Future<void> simulateTranscript(String text) async {
    state = state.copyWith(isListening: false, transcript: text);
    try {
      final repo = ref.read(assistantRepositoryProvider);
      final res = await repo.parseIntent(text);
      if (res.isComplete && res.intent.origin != null && res.intent.destination != null) {
        final req = TripRequest(
          origin: res.intent.origin!,
          destination: res.intent.destination!,
          departureTime: res.intent.departureTime ?? DateTime.now().add(const Duration(minutes: 15)),
          mode: res.intent.mode ?? TransportMode.bike,
        );
        state = state.copyWith(extractedTrip: req);
        ref.read(activeTripRequestProvider.notifier).update(req);
        return;
      }
    } catch (_) {
      // Fallback
    }

    final fallbackReq = TripRequest(
      origin: 'Noida Sector 62',
      destination: 'College (DTU)',
      departureTime: DateTime.now().add(const Duration(minutes: 15)),
      mode: TransportMode.bike,
    );
    state = state.copyWith(extractedTrip: fallbackReq);
    ref.read(activeTripRequestProvider.notifier).update(fallbackReq);
  }

  void reset() {
    state = const VoiceSessionState();
  }
}

final voiceSessionProvider =
    NotifierProvider<VoiceSessionNotifier, VoiceSessionState>(VoiceSessionNotifier.new);
