// ignore_for_file: avoid_print
import 'package:weather_gpt/models/models.dart';
import 'package:weather_gpt/core/api/api_client.dart';
import 'package:weather_gpt/repositories/http/http_trip_repository.dart';

void main() async {
  final client = ApiClient();
  final repo = HttpTripRepository(client);

  final req = TripRequest(
    origin: 'Noida Sector 62',
    destination: 'Gurgaon Cyber Hub',
    departureTime: DateTime.now().add(const Duration(hours: 1)),
    mode: TransportMode.bike,
  );

  try {
    print('Sending request...');
    final response = await repo.analyzeTrip(req);
    print('Success!');
    print('Distance: ${response.distanceKm} km');
    print('Risk Score: ${response.risk?.overallScore}');
    print('Risk Confidence: ${response.risk?.confidence.level}');
  } catch (e) {
    print('Failed: $e');
  }
}
