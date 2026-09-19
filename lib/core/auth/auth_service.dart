import 'dart:async';

class AppUser {
  final String uid;
  final String? email;
  final String? displayName;
  final bool isAnonymous;

  const AppUser({
    required this.uid,
    this.email,
    this.displayName,
    this.isAnonymous = false,
  });

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is AppUser &&
          runtimeType == other.runtimeType &&
          uid == other.uid &&
          email == other.email;

  @override
  int get hashCode => uid.hashCode ^ email.hashCode;
}

class AuthState {
  final AppUser? user;
  final bool isLoading;
  final String? error;

  const AuthState({
    this.user,
    this.isLoading = false,
    this.error,
  });

  bool get isAuthenticated => user != null;
  bool get isGuest => user == null;

  AuthState copyWith({
    AppUser? user,
    bool? isLoading,
    String? error,
    bool clearUser = false,
  }) {
    return AuthState(
      user: clearUser ? null : (user ?? this.user),
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

abstract class AuthService {
  Stream<AppUser?> get authStateChanges;
  AppUser? get currentUser;
  Future<String?> getIdToken({bool forceRefresh = false});
  Future<AppUser> signInWithEmailAndPassword(String email, String password);
  Future<AppUser> createUserWithEmailAndPassword(String email, String password);
  Future<AppUser> signInWithMockCredentials({
    String uid = 'test-user-id',
    String email = 'test@example.com',
    String displayName = 'Demo Traveler',
  });
  Future<void> signOut();
}
