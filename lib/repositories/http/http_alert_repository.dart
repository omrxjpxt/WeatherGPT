import '../../models/models.dart';
import '../repositories.dart';
import '../../core/api/api_client.dart';

class HttpAlertRepository implements AlertRepository {
  final ApiClient _apiClient;

  HttpAlertRepository(this._apiClient);

  @override
  Future<List<OfficialAlert>> getActiveAlerts({String? location}) async {
    // Backend takes lat/lng
    final response = await _apiClient.get(
      '/alerts/',
      queryParams: {'lat': '28.6270', 'lng': '77.3650'},
    );
    final List<dynamic> resultsJson = response;
    return resultsJson.map((json) => OfficialAlert.fromJson(json)).toList();
  }

  @override
  Future<OfficialAlert> getAlertDetail(String alertId) async {
    // There isn't a dedicated endpoint for single alert detail on backend right now.
    // We fetch all active alerts and filter.
    final alerts = await getActiveAlerts();
    return alerts.firstWhere(
      (a) => a.id == alertId,
      orElse: () => throw Exception('Alert not found'),
    );
  }
}
