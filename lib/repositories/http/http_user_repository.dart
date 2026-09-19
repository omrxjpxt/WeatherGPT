import '../../models/models.dart';
import '../repositories.dart';
import '../../core/api/api_client.dart';

class HttpUserRepository implements UserRepository {
  final ApiClient _apiClient;

  HttpUserRepository(this._apiClient);

  @override
  Future<UserProfile> getProfile() async {
    final response = await _apiClient.get('/users/me/profile');
    return UserProfile.fromJson(response as Map<String, dynamic>);
  }

  @override
  Future<UserProfile> updateProfile(UserProfile profile) async {
    final response = await _apiClient.put('/users/me/profile', body: profile.toJson());
    return UserProfile.fromJson(response as Map<String, dynamic>);
  }

  @override
  Future<List<SavedRoute>> getSavedRoutes() async {
    final response = await _apiClient.get('/users/me/saved-routes');
    final List<dynamic> list = response as List<dynamic>;
    return list.map((e) => SavedRoute.fromJson(e as Map<String, dynamic>)).toList();
  }

  @override
  Future<SavedRoute> saveRoute(SavedRoute route) async {
    final response = await _apiClient.post('/users/me/saved-routes', body: route.toJson());
    return SavedRoute.fromJson(response as Map<String, dynamic>);
  }

  @override
  Future<void> deleteSavedRoute(String savedRouteId) async {
    await _apiClient.delete('/users/me/saved-routes/$savedRouteId');
  }

  @override
  Future<List<TripHistorySummary>> getTripHistory() async {
    final response = await _apiClient.get('/users/me/trips');
    final List<dynamic> list = response as List<dynamic>;
    return list.map((e) => TripHistorySummary.fromJson(e as Map<String, dynamic>)).toList();
  }

  @override
  Future<TripResponse> getTripDetail(String analysisId) async {
    final response = await _apiClient.get('/users/me/trips/$analysisId');
    return TripResponse.fromJson(response as Map<String, dynamic>);
  }

  @override
  Future<List<ConversationSummary>> getConversations() async {
    final response = await _apiClient.get('/users/me/conversations');
    final List<dynamic> list = response as List<dynamic>;
    return list.map((e) => ConversationSummary.fromJson(e as Map<String, dynamic>)).toList();
  }
}
