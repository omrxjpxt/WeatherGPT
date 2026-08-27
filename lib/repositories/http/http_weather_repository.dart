import '../../models/models.dart';
import '../repositories.dart';
import '../../core/api/api_client.dart';

class HttpWeatherRepository implements WeatherRepository {
  final ApiClient _apiClient;

  HttpWeatherRepository(this._apiClient);

  @override
  Future<WeatherPoint> getCurrentWeather(String location) async {
    // Geocoding should theoretically happen in backend, but weather endpoint takes lat/lng.
    // For MVP, we will pass fixed lat/lng for Noida or rely on backend to accept 'location' eventually.
    // The current backend route takes `lat` and `lng`.
    // We'll hardcode Noida coordinates here for the MVP if we don't have geocoding yet in flutter.
    final response = await _apiClient.get(
      '/weather/current',
      queryParams: {'lat': '28.6270', 'lng': '77.3650'},
    );
    return WeatherPoint.fromJson(response);
  }

  @override
  Future<List<WeatherPoint>> getForecast(String location, {int hours = 24}) async {
    final response = await _apiClient.get(
      '/weather/forecast',
      queryParams: {'lat': '28.6270', 'lng': '77.3650'},
    );
    final List<dynamic> resultsJson = response;
    return resultsJson.map((json) => WeatherPoint.fromJson(json)).toList();
  }
}
