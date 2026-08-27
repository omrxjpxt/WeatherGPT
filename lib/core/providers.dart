import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/models.dart';
import '../repositories/repositories.dart';
import '../repositories/mock_repositories.dart';

// ── Repository Providers ──

final tripRepositoryProvider = Provider<TripRepository>((ref) {
  return MockTripRepository();
});

final weatherRepositoryProvider = Provider<WeatherRepository>((ref) {
  return MockWeatherRepository();
});

final riskRepositoryProvider = Provider<RiskRepository>((ref) {
  return MockRiskRepository();
});

final alertRepositoryProvider = Provider<AlertRepository>((ref) {
  return MockAlertRepository();
});

final historyRepositoryProvider = Provider<HistoryRepository>((ref) {
  return MockHistoryRepository();
});

// ── Trip State ──

class TripRequestNotifier extends Notifier<TripRequest> {
  @override
  TripRequest build() {
    return TripRequest(
      origin: 'Noida Sector 62',
      destination: 'Gurgaon Cyber Hub',
      departureTime: DateTime(2026, 8, 27, 8, 0),
      mode: TransportMode.bike,
    );
  }

  void update(TripRequest request) => state = request;
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
  DateTime build() => DateTime(2026, 8, 27, 8, 0);

  void update(DateTime time) => state = time;
}

final scenarioTimeProvider =
    NotifierProvider<ScenarioTimeNotifier, DateTime>(ScenarioTimeNotifier.new);

final scenarioResultsProvider = FutureProvider<List<ScenarioResult>>((ref) async {
  final request = ref.watch(activeTripRequestProvider);
  final repo = ref.read(tripRepositoryProvider);
  final baseTime = DateTime(2026, 8, 27, 6, 0);
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

  void simulateTranscript(String text) {
    state = state.copyWith(
      isListening: false,
      transcript: text,
      extractedTrip: TripRequest(
        origin: 'Noida Sector 62',
        destination: 'College (DTU)',
        departureTime: DateTime(2026, 8, 28, 8, 0),
        mode: TransportMode.bike,
      ),
    );
  }

  void reset() {
    state = const VoiceSessionState();
  }
}

final voiceSessionProvider =
    NotifierProvider<VoiceSessionNotifier, VoiceSessionState>(VoiceSessionNotifier.new);
