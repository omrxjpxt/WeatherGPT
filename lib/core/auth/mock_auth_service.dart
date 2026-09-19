import 'dart:async';
import 'auth_service.dart';

class MockAuthService implements AuthService {
  AppUser? _currentUser;
  final StreamController<AppUser?> _controller = StreamController<AppUser?>.broadcast();
  final String mockToken;

  MockAuthService({
    AppUser? initialUser,
    this.mockToken = 'test-token',
  }) : _currentUser = initialUser;

  @override
  Stream<AppUser?> get authStateChanges => _controller.stream;

  @override
  AppUser? get currentUser => _currentUser;

  @override
  Future<String?> getIdToken({bool forceRefresh = false}) async {
    if (_currentUser == null) return null;
    return mockToken;
  }

  @override
  Future<AppUser> signInWithEmailAndPassword(String email, String password) async {
    final user = AppUser(
      uid: 'mock-uid-${email.split('@').first}',
      email: email,
      displayName: email.split('@').first,
    );
    _currentUser = user;
    _controller.add(_currentUser);
    return user;
  }

  @override
  Future<AppUser> createUserWithEmailAndPassword(String email, String password) async {
    return signInWithEmailAndPassword(email, password);
  }

  @override
  Future<AppUser> signInWithMockCredentials({
    String uid = 'test-user-id',
    String email = 'test@example.com',
    String displayName = 'Demo Traveler',
  }) async {
    final user = AppUser(
      uid: uid,
      email: email,
      displayName: displayName,
    );
    _currentUser = user;
    _controller.add(_currentUser);
    return user;
  }

  @override
  Future<void> signOut() async {
    _currentUser = null;
    _controller.add(null);
  }

  void dispose() {
    _controller.close();
  }
}
