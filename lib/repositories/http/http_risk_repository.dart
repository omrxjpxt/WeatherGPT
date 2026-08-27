import '../../models/models.dart';
import '../repositories.dart';
import '../../core/api/api_client.dart';

class HttpRiskRepository implements RiskRepository {
  final ApiClient _apiClient;
  final TripRepository _tripRepository;

  HttpRiskRepository(this._apiClient, this._tripRepository);

  @override
  Future<RiskAssessment?> getRiskAssessment(TripRequest request) async {
    // Risk assessment is inherently tied to a trip in the backend architecture.
    // We delegate to the TripRepository.
    final tripResponse = await _tripRepository.analyzeTrip(request);
    return tripResponse.risk;
  }

  @override
  Future<List<Hazard>> getNearbyHazards(double lat, double lng, {double radiusKm = 10}) async {
    // The hazard endpoint takes bounds, we construct a rough bounding box
    final offset = radiusKm / 111.0; // rough degree equivalent
    final response = await _apiClient.get(
      '/hazards/',
      queryParams: {
        'min_lat': (lat - offset).toString(),
        'max_lat': (lat + offset).toString(),
        'min_lng': (lng - offset).toString(),
        'max_lng': (lng + offset).toString(),
      },
    );
    
    final List<dynamic> resultsJson = response;
    return resultsJson.map((json) => Hazard.fromJson(json)).toList();
  }
}
