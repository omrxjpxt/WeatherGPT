import 'package:flutter_test/flutter_test.dart';
import 'package:weather_gpt/core/auth/auth_service.dart';
import 'package:weather_gpt/core/auth/mock_auth_service.dart';

void main() {
  group('MockAuthService Tests', () {
    late MockAuthService authService;

    setUp(() {
      authService = MockAuthService();
    });

    tearDown(() {
      authService.dispose();
    });

    test('Initial state is unauthenticated / guest', () async {
      expect(authService.currentUser, isNull);
      final token = await authService.getIdToken();
      expect(token, isNull);
    });

    test('signInWithMockCredentials signs in user and emits to authStateChanges', () async {
      final emittedUsers = <AppUser?>[];
      final subscription = authService.authStateChanges.listen(emittedUsers.add);

      final user = await authService.signInWithMockCredentials(
        uid: 'user-om-123',
        email: 'om@weathergpt.com',
        displayName: 'Om Gangwar',
      );

      expect(user.uid, 'user-om-123');
      expect(user.email, 'om@weathergpt.com');
      expect(user.displayName, 'Om Gangwar');
      expect(authService.currentUser, user);

      final token = await authService.getIdToken();
      expect(token, 'test-token');

      // Allow microtask to process stream
      await Future<void>.delayed(Duration.zero);
      expect(emittedUsers.length, 1);
      expect(emittedUsers.first?.uid, 'user-om-123');

      await subscription.cancel();
    });

    test('signInWithEmailAndPassword updates currentUser and emits to stream', () async {
      final user = await authService.signInWithEmailAndPassword('traveler@test.com', 'secret');
      expect(user.email, 'traveler@test.com');
      expect(authService.currentUser?.email, 'traveler@test.com');

      final token = await authService.getIdToken();
      expect(token, 'test-token');
    });

    test('signOut clears user and emits null', () async {
      await authService.signInWithMockCredentials(uid: 'user-temp');
      expect(authService.currentUser, isNotNull);

      final emittedUsers = <AppUser?>[];
      final subscription = authService.authStateChanges.listen(emittedUsers.add);

      await authService.signOut();

      expect(authService.currentUser, isNull);
      final token = await authService.getIdToken();
      expect(token, isNull);

      await Future<void>.delayed(Duration.zero);
      expect(emittedUsers.length, 1);
      expect(emittedUsers.first, isNull);

      await subscription.cancel();
    });
  });
}
