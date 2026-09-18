import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:weather_gpt/features/assistant/assistant_screen.dart';
import 'package:weather_gpt/models/models.dart';
import 'package:weather_gpt/repositories/repositories.dart';
import 'package:weather_gpt/core/theme/app_theme.dart';
import 'package:weather_gpt/core/providers.dart';

class FakeAssistantRepository implements AssistantRepository {
  final AssistantChatResponse Function(AssistantChatRequest request)? onChat;

  FakeAssistantRepository({this.onChat});

  @override
  Future<AssistantChatResponse> chat(AssistantChatRequest request) async {
    if (onChat != null) {
      return onChat!(request);
    }
    return AssistantChatResponse(
      message: 'Taking bike via Noida-Greater Noida Expy has a low risk score of 22/100.',
      intent: const ExtractedIntent(
        origin: 'Noida Sector 62',
        destination: 'Gurgaon Cyber Hub',
        mode: TransportMode.bike,
      ),
      tripRequest: TripRequest(
        origin: 'Noida Sector 62',
        destination: 'Gurgaon Cyber Hub',
        departureTime: DateTime.utc(2026, 9, 19, 8, 0),
        mode: TransportMode.bike,
      ),
      tripResponse: TripResponse(
        request: TripRequest(
          origin: 'Noida Sector 62',
          destination: 'Gurgaon Cyber Hub',
          departureTime: DateTime.utc(2026, 9, 19, 8, 0),
          mode: TransportMode.bike,
        ),
        route: const [],
        modeOptions: const [],
        hazards: const [],
        sources: const [],
        estimatedDuration: const Duration(minutes: 35),
        distanceKm: 34.0,
        status: TripStatus.success,
      ),
      status: 'success',
      provenance: 'demo/mock',
    );
  }

  @override
  Future<AssistantParseResponse> parseIntent(String query, {DateTime? referenceTime}) async {
    return const AssistantParseResponse(
      intent: ExtractedIntent(
        origin: 'Noida Sector 62',
        destination: 'Gurgaon Cyber Hub',
        mode: TransportMode.bike,
      ),
      isComplete: true,
    );
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  Widget buildTestableWidget({
    required Widget child,
    required AssistantRepository assistantRepo,
    Size surfaceSize = const Size(393, 852), // iPhone 15 Pro
    EdgeInsets padding = const EdgeInsets.only(top: 59, bottom: 34),
  }) {
    return ProviderScope(
      overrides: [
        assistantRepositoryProvider.overrideWithValue(assistantRepo),
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

  group('Assistant Screen Chat Tests', () {
    testWidgets('Renders initial welcome message and input bar without overflow on iPhone SE', (tester) async {
      await tester.binding.setSurfaceSize(const Size(375, 667));

      final repo = FakeAssistantRepository();
      await tester.pumpWidget(buildTestableWidget(
        child: const AssistantScreen(),
        assistantRepo: repo,
        surfaceSize: const Size(375, 667),
        padding: const EdgeInsets.only(top: 20, bottom: 0),
      ));
      await tester.pumpAndSettle();

      expect(find.text('WeatherGPT'), findsOneWidget);
      expect(find.textContaining('Good morning!'), findsOneWidget);
      expect(find.byType(TextField), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('Sends user message, displays explanation and action button on iPhone 15 Pro', (tester) async {
      await tester.binding.setSurfaceSize(const Size(393, 852));

      final repo = FakeAssistantRepository();
      await tester.pumpWidget(buildTestableWidget(
        child: const AssistantScreen(),
        assistantRepo: repo,
        surfaceSize: const Size(393, 852),
      ));
      await tester.pumpAndSettle();

      // Enter query
      await tester.enterText(find.byType(TextField), 'Noida to Gurgaon by bike');
      await tester.testTextInput.receiveAction(TextInputAction.done);
      await tester.pump();

      // Verify user message appeared
      expect(find.text('Noida to Gurgaon by bike'), findsOneWidget);

      await tester.pumpAndSettle();

      // Verify assistant explanation appeared
      expect(find.textContaining('Taking bike via Noida-Greater Noida Expy'), findsOneWidget);
      // Verify View Trip Analysis action chip
      expect(find.text('View Trip Analysis'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('Renders degraded explanation when routing is unavailable', (tester) async {
      await tester.binding.setSurfaceSize(const Size(393, 852));

      final repo = FakeAssistantRepository(
        onChat: (req) => const AssistantChatResponse(
          message: 'Routing data is currently unavailable between Noida and Gurgaon.',
          intent: ExtractedIntent(origin: 'Noida', destination: 'Gurgaon'),
          tripRequest: null,
          tripResponse: null,
          status: 'degraded',
          provenance: 'demo/mock',
        ),
      );

      await tester.pumpWidget(buildTestableWidget(
        child: const AssistantScreen(),
        assistantRepo: repo,
      ));
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextField), 'Noida to Gurgaon');
      await tester.testTextInput.receiveAction(TextInputAction.done);
      await tester.pumpAndSettle();

      expect(find.textContaining('Routing data is currently unavailable'), findsOneWidget);
      // No Trip Analysis button because tripResponse is null
      expect(find.text('View Trip Analysis'), findsNothing);
      expect(tester.takeException(), isNull);
    });
  });
}
