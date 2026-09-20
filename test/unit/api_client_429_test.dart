import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:weather_gpt/core/api/api_client.dart';
import 'package:weather_gpt/core/api/api_exception.dart';

void main() {
  group('ApiClient HTTP 429 Rate Limiting', () {
    test('parses HTTP 429 with retry-after header correctly', () async {
      final mockHttpClient = MockClient((request) async {
        return http.Response(
          jsonEncode({'detail': 'Rate limit exceeded.'}),
          429,
          headers: {'retry-after': '45', 'content-type': 'application/json'},
        );
      });

      final apiClient = ApiClient(client: mockHttpClient);

      expect(
        () async => await apiClient.get('/test-endpoint'),
        throwsA(
          isA<ApiException>()
              .having((e) => e.type, 'type', ApiErrorType.rateLimited)
              .having((e) => e.statusCode, 'statusCode', 429)
              .having((e) => e.retryAfter, 'retryAfter', 45)
              .having((e) => e.message, 'message', contains('45 seconds')),
        ),
      );
    });

    test('parses HTTP 429 without retry-after header gracefully', () async {
      final mockHttpClient = MockClient((request) async {
        return http.Response(
          jsonEncode({'detail': 'Too Many Requests'}),
          429,
          headers: {'content-type': 'application/json'},
        );
      });

      final apiClient = ApiClient(client: mockHttpClient);

      expect(
        () async => await apiClient.get('/test-endpoint'),
        throwsA(
          isA<ApiException>()
              .having((e) => e.type, 'type', ApiErrorType.rateLimited)
              .having((e) => e.statusCode, 'statusCode', 429)
              .having((e) => e.retryAfter, 'retryAfter', isNull),
        ),
      );
    });
  });
}
