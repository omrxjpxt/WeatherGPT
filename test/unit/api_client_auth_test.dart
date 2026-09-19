import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:weather_gpt/core/api/api_client.dart';
import 'package:weather_gpt/core/api/api_exception.dart';

void main() {
  group('ApiClient Auth and Method Tests', () {
    test('Authenticated request contains Authorization header', () async {
      http.Request? capturedRequest;

      final mockClient = MockClient((request) async {
        capturedRequest = request;
        return http.Response(jsonEncode({'status': 'ok'}), 200);
      });

      final apiClient = ApiClient(
        client: mockClient,
        tokenProvider: () async => 'mock-firebase-id-token-xyz',
      );

      final result = await apiClient.get('/test/endpoint');

      expect(result, {'status': 'ok'});
      expect(capturedRequest, isNotNull);
      expect(
        capturedRequest!.headers['Authorization'],
        'Bearer mock-firebase-id-token-xyz',
      );
      expect(capturedRequest!.headers['Content-Type'], 'application/json');
    });

    test('Guest request contains no Authorization header when token is null', () async {
      http.Request? capturedRequest;

      final mockClient = MockClient((request) async {
        capturedRequest = request;
        return http.Response(jsonEncode({'status': 'ok'}), 200);
      });

      final apiClient = ApiClient(
        client: mockClient,
        tokenProvider: () async => null,
      );

      final result = await apiClient.post('/trips/analyze', body: {'origin': 'A', 'destination': 'B'});

      expect(result, {'status': 'ok'});
      expect(capturedRequest, isNotNull);
      expect(capturedRequest!.headers.containsKey('Authorization'), isFalse);
    });

    test('Guest request contains no Authorization header when tokenProvider is omitted', () async {
      http.Request? capturedRequest;

      final mockClient = MockClient((request) async {
        capturedRequest = request;
        return http.Response(jsonEncode({'status': 'ok'}), 200);
      });

      final apiClient = ApiClient(client: mockClient);

      await apiClient.get('/trips/status');

      expect(capturedRequest, isNotNull);
      expect(capturedRequest!.headers.containsKey('Authorization'), isFalse);
    });

    test('HTTP 401 maps to ApiErrorType.unauthorized', () async {
      final mockClient = MockClient((request) async {
        return http.Response(jsonEncode({'detail': 'Token expired'}), 401);
      });

      final apiClient = ApiClient(client: mockClient);

      expect(
        () => apiClient.get('/users/me/profile'),
        throwsA(isA<ApiException>().having(
          (e) => e.type,
          'type',
          ApiErrorType.unauthorized,
        ).having(
          (e) => e.message,
          'message',
          'Token expired',
        )),
      );
    });

    test('HTTP 403 maps to ApiErrorType.forbidden', () async {
      final mockClient = MockClient((request) async {
        return http.Response(jsonEncode({'detail': 'Forbidden resource'}), 403);
      });

      final apiClient = ApiClient(client: mockClient);

      expect(
        () => apiClient.get('/users/me/admin'),
        throwsA(isA<ApiException>().having(
          (e) => e.type,
          'type',
          ApiErrorType.forbidden,
        ).having(
          (e) => e.message,
          'message',
          'Forbidden resource',
        )),
      );
    });

    test('PUT request sends body and parses JSON response', () async {
      http.Request? capturedRequest;

      final mockClient = MockClient((request) async {
        capturedRequest = request;
        return http.Response(jsonEncode({'updated': true}), 200);
      });

      final apiClient = ApiClient(client: mockClient);
      final response = await apiClient.put(
        '/users/me/profile',
        body: {'displayName': 'Om Gangwar'},
      );

      expect(response, {'updated': true});
      expect(capturedRequest, isNotNull);
      expect(capturedRequest!.method, 'PUT');
      expect(jsonDecode(capturedRequest!.body), {'displayName': 'Om Gangwar'});
    });

    test('DELETE request executes and parses response', () async {
      http.Request? capturedRequest;

      final mockClient = MockClient((request) async {
        capturedRequest = request;
        return http.Response(jsonEncode({'status': 'deleted'}), 200);
      });

      final apiClient = ApiClient(client: mockClient);
      final response = await apiClient.delete('/users/me/saved-routes/route-123');

      expect(response, {'status': 'deleted'});
      expect(capturedRequest, isNotNull);
      expect(capturedRequest!.method, 'DELETE');
    });
  });
}
