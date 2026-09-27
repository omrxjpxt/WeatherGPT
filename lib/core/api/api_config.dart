import 'dart:io' show Platform;
import 'package:flutter/foundation.dart';

enum AppMode { mock, live }

class ApiConfig {
  // Switch to live mode to test integration
  static AppMode mode = AppMode.live;
  
  static const Duration timeout = Duration(seconds: 15);

  /// Get the base URL based on platform/environment.
  ///
  /// Can be overridden at build or runtime via:
  /// `--dart-define=API_BASE_URL=https://your-backend-service/api/v1`
  static String get baseUrl {
    // 1. Check explicit build-time or runtime environment override
    const String definedBaseUrl = String.fromEnvironment('API_BASE_URL');
    if (definedBaseUrl.isNotEmpty) {
      final trimmed = definedBaseUrl.endsWith('/')
          ? definedBaseUrl.substring(0, definedBaseUrl.length - 1)
          : definedBaseUrl;
      return trimmed.endsWith('/api/v1') ? trimmed : '$trimmed/api/v1';
    }

    // 2. Local development on web
    if (kIsWeb) {
      return 'http://localhost:8000/api/v1';
    }
    
    // 3. Android emulator requires 10.0.2.2 to reach host localhost
    if (Platform.isAndroid) {
      return 'http://10.0.2.2:8000/api/v1';
    }
    
    // 4. iOS simulator / physical device / macOS desktop
    // Defaulting to 127.0.0.1 (or API_HOST override if provided).
    const String envApiHost = String.fromEnvironment('API_HOST', defaultValue: '127.0.0.1');
    return 'http://$envApiHost:8000/api/v1';
  }
}
