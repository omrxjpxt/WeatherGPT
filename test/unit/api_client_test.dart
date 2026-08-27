import 'package:flutter_test/flutter_test.dart';
import 'package:weather_gpt/core/api/api_exception.dart';
import 'package:weather_gpt/core/api/api_client.dart';

void main() {
  group('ApiException Tests', () {
    test('ApiException toString formatting', () {
      final exception = ApiException(
        type: ApiErrorType.networkError,
        message: 'No connection',
      );
      
      expect(
        exception.toString(),
        'ApiException(type: ApiErrorType.networkError, statusCode: null, message: No connection)',
      );
    });
  });
}
