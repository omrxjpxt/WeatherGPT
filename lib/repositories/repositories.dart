import '../models/models.dart';

/// Abstract repository interfaces for the WeatherGPT frontend.
/// The UI depends ONLY on these interfaces.
/// Mock implementations are provided for frontend development.
/// FastAPI-backed implementations will replace them later.

abstract class TripRepository {
  Future<TripResponse> analyzeTrip(TripRequest request);
  Future<List<ScenarioResult>> simulateScenarios(
    TripRequest request,
    List<DateTime> departureTimes,
  );
  Future<List<ModeOption>> compareModes(
    String origin,
    String destination,
    DateTime departureTime,
  );
}

abstract class WeatherRepository {
  Future<WeatherPoint> getCurrentWeather(String location);
  Future<List<WeatherPoint>> getForecast(String location, {int hours = 24});
}

abstract class RiskRepository {
  Future<RiskAssessment> getRiskAssessment(TripRequest request);
  Future<List<Hazard>> getNearbyHazards(double lat, double lng, {double radiusKm = 10});
}

abstract class AlertRepository {
  Future<List<OfficialAlert>> getActiveAlerts({String? location});
  Future<OfficialAlert> getAlertDetail(String alertId);
}

abstract class HistoryRepository {
  Future<List<HistoricalEvent>> getHistoricalEvents(
    String location, {
    DateTime? startDate,
    DateTime? endDate,
  });
}
