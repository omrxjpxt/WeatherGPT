import 'package:flutter/foundation.dart';
import '../../models/models.dart';
import '../repositories.dart';
import '../../core/api/api_client.dart';

class HttpTripRepository implements TripRepository {
  final ApiClient _apiClient;

  HttpTripRepository(this._apiClient);

  @override
  Future<TripResponse> analyzeTrip(TripRequest request) async {
    final response = await _apiClient.post('/trips/analyze', body: request.toJson());
    return TripResponse.fromJson(response);
  }

  @override
  Future<List<ScenarioResult>> simulateScenarios(
    TripRequest request,
    List<DateTime> departureTimes,
  ) async {
    final body = {
      'request': request.toJson(),
      'departureTimes': departureTimes.map((t) => t.toUtc().toIso8601String()).toList(),
    };
    final response = await _apiClient.post('/scenarios/evaluate', body: body);
    
    final List<dynamic> resultsJson = response;
    return resultsJson.map((json) => ScenarioResult.fromJson(json)).toList();
  }

  @override
  Future<List<ModeOption>> compareModes(
    String origin,
    String destination,
    DateTime departureTime,
  ) async {
    try {
      final request = TripRequest(
        origin: origin,
        destination: destination,
        departureTime: departureTime,
        mode: TransportMode.car,
      );
      final tripResponse = await analyzeTrip(request);
      if (tripResponse.modeOptions.isNotEmpty) {
        return tripResponse.modeOptions;
      }
    } catch (e) {
      debugPrint('Single-pass mode comparison failed: $e');
    }
    return [];
  }
}
