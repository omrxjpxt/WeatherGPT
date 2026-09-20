import '../../models/models.dart';
import '../repositories.dart';
import '../../core/api/api_client.dart';

class HttpWeatherRepository implements WeatherRepository {
  final ApiClient _apiClient;

  HttpWeatherRepository(this._apiClient);

  @override
  Future<WeatherPoint> getCurrentWeather(String location) async {
    final response = await _apiClient.get(
      '/weather/current',
      queryParams: {'location': location},
    );
    return WeatherPoint.fromJson(response);
  }

  @override
  Future<List<WeatherPoint>> getForecast(String location, {int hours = 24}) async {
    final response = await _apiClient.get(
      '/weather/forecast',
      queryParams: {
        'location': location,
        'hours': hours.toString(),
      },
    );
    final List<dynamic> resultsJson = response;
    return resultsJson.map((json) => WeatherPoint.fromJson(json)).toList();
  }
}
