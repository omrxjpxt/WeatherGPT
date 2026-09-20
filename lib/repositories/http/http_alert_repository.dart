import '../../models/models.dart';
import '../repositories.dart';
import '../../core/api/api_client.dart';

class HttpAlertRepository implements AlertRepository {
  final ApiClient _apiClient;

  HttpAlertRepository(this._apiClient);

  @override
  Future<List<OfficialAlert>> getActiveAlerts({String? location}) async {
    final Map<String, String> queryParams = {};
    if (location != null && location.trim().isNotEmpty) {
      queryParams['location'] = location.trim();
    }
    final response = await _apiClient.get(
      '/alerts/',
      queryParams: queryParams.isNotEmpty ? queryParams : null,
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
