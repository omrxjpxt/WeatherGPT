import 'package:flutter_test/flutter_test.dart';
import 'package:weather_gpt/core/api/api_config.dart';

void main() {
  group('ApiConfig tests', () {
    test('ApiConfig defaults to live mode and 15s timeout', () {
      expect(ApiConfig.mode, equals(AppMode.live));
      expect(ApiConfig.timeout, equals(const Duration(seconds: 15)));
    });

    test('ApiConfig baseUrl produces valid HTTP/HTTPS endpoint ending with /api/v1', () {
      final url = ApiConfig.baseUrl;
      expect(url, isNotEmpty);
      expect(url.endsWith('/api/v1'), isTrue);
      expect(url.startsWith('http://') || url.startsWith('https://'), isTrue);
    });
  });
}
