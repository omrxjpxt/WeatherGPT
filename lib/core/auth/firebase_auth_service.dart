import 'dart:async';
import 'package:firebase_auth/firebase_auth.dart' as fb;
import 'auth_service.dart';

class FirebaseAuthService implements AuthService {
  final fb.FirebaseAuth _firebaseAuth;

  FirebaseAuthService({fb.FirebaseAuth? firebaseAuth})
      : _firebaseAuth = firebaseAuth ?? fb.FirebaseAuth.instance;

  @override
  Stream<AppUser?> get authStateChanges =>
      _firebaseAuth.authStateChanges().map(_mapFirebaseUser);

  @override
  AppUser? get currentUser => _mapFirebaseUser(_firebaseAuth.currentUser);

  @override
  Future<String?> getIdToken({bool forceRefresh = false}) async {
    final user = _firebaseAuth.currentUser;
    if (user == null) return null;
    return user.getIdToken(forceRefresh);
  }

  @override
  Future<AppUser> signInWithEmailAndPassword(String email, String password) async {
    final credential = await _firebaseAuth.signInWithEmailAndPassword(
      email: email,
      password: password,
    );
    final user = _mapFirebaseUser(credential.user);
    if (user == null) {
      throw Exception('Failed to sign in: user is null.');
    }
    return user;
  }

  @override
  Future<AppUser> createUserWithEmailAndPassword(String email, String password) async {
    final credential = await _firebaseAuth.createUserWithEmailAndPassword(
      email: email,
      password: password,
    );
    final user = _mapFirebaseUser(credential.user);
    if (user == null) {
      throw Exception('Failed to create account: user is null.');
    }
    return user;
  }

  @override
  Future<AppUser> signInWithMockCredentials({
    String uid = 'test-user-id',
    String email = 'test@example.com',
    String displayName = 'Demo Traveler',
  }) async {
    try {
      final credential = await _firebaseAuth.signInAnonymously();
      return _mapFirebaseUser(credential.user) ??
          AppUser(uid: uid, email: email, displayName: displayName);
    } catch (_) {
      return AppUser(uid: uid, email: email, displayName: displayName);
    }
  }

  @override
  Future<void> signOut() async {
    await _firebaseAuth.signOut();
  }

  AppUser? _mapFirebaseUser(fb.User? user) {
    if (user == null) return null;
    return AppUser(
      uid: user.uid,
      email: user.email,
      displayName: user.displayName,
      isAnonymous: user.isAnonymous,
    );
  }
}
