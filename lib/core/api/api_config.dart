import 'dart:io' show Platform;
import 'package:flutter/foundation.dart';

enum AppMode { mock, live }

class ApiConfig {
  // Switch to live mode to test integration
  static AppMode mode = AppMode.live;
  
  static const Duration timeout = Duration(seconds: 15);

  /// Get the base URL based on platform/environment.
  static String get baseUrl {
    // In production/release, you would use a real domain.
    if (kReleaseMode) {
      return 'https://api.weathergpt.com/api/v1'; 
    }

    // For local development
    if (kIsWeb) {
      return 'http://localhost:8000/api/v1';
    }
    
    // Android emulator requires 10.0.2.2 to reach host localhost
    if (Platform.isAndroid) {
      return 'http://10.0.2.2:8000/api/v1';
    }
    
    // iOS simulator / physical device 
    // To run on a physical iOS device, you must set the environment variable
    // or change this to your Mac's LAN IP when compiling.
    // Defaulting to localhost for iOS Simulator.
    const String envApiHost = String.fromEnvironment('API_HOST', defaultValue: '127.0.0.1');
    return 'http://$envApiHost:8000/api/v1';
  }
}
