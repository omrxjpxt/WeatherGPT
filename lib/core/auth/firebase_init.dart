import 'package:flutter/foundation.dart';
import 'package:firebase_core/firebase_core.dart';

class FirebaseInit {
  static bool isInitialized = false;

  static Future<void> initialize() async {
    try {
      await Firebase.initializeApp();
      isInitialized = true;
      debugPrint('Firebase initialized successfully.');
    } catch (e) {
      isInitialized = false;
      debugPrint('Firebase initialization skipped or unavailable: $e. Operating in mock/offline auth mode.');
    }
  }
}
