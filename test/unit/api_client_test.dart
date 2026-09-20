import 'package:flutter_test/flutter_test.dart';
import 'package:weather_gpt/core/api/api_exception.dart';

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

    test('ApiException toString formatting with retryAfter', () {
      final exception = ApiException(
        type: ApiErrorType.rateLimited,
        statusCode: 429,
        retryAfter: 30,
        message: 'Rate limit exceeded',
      );
      
      expect(
        exception.toString(),
        'ApiException(type: ApiErrorType.rateLimited, statusCode: 429, retryAfter: 30, message: Rate limit exceeded)',
      );
    });
  });
}
