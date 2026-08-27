import '../models/models.dart';
import '../repositories/repositories.dart';

/// Mock implementation of TripRepository using realistic Delhi-NCR data
class MockTripRepository implements TripRepository {
  @override
  Future<TripResponse> analyzeTrip(TripRequest request) async {
    await Future.delayed(const Duration(milliseconds: 300));
    final riskScore = _riskForTime(request.departureTime, request.mode);
    return TripResponse(
      request: request,
      risk: _buildRisk(riskScore),
      route: _buildRoute(request.mode),
      recommendation: _buildRecommendation(riskScore, request.mode),
      modeOptions: await compareModes(
        request.origin,
        request.destination,
        request.departureTime,
      ),
      hazards: _buildHazards(),
      sources: _buildSources(),
      estimatedDuration: _etaForMode(request.mode),
      distanceKm: request.mode == TransportMode.metro ? 42.0 : 35.5,
    );
  }

  @override
  Future<List<ScenarioResult>> simulateScenarios(
    TripRequest request,
    List<DateTime> departureTimes,
  ) async {
    await Future.delayed(const Duration(milliseconds: 200));
    final mockResponse = await analyzeTrip(request);
    final times = departureTimes;
    return [
      ScenarioResult(
        scenarioId: 'sc_mock_1',
        departureTime: times[0],
        risk: mockResponse.risk,
        estimatedDuration: const Duration(hours: 1),
        recommendation: null,
        changedFactors: [],
      ),
      ScenarioResult(
        scenarioId: 'sc_mock_2',
        departureTime: times[1],
        risk: mockResponse.risk,
        estimatedDuration: const Duration(hours: 1),
        recommendation: null,
        changedFactors: [],
      ),
    ];
  }

  @override
  Future<List<ModeOption>> compareModes(
    String origin,
    String destination,
    DateTime departureTime,
  ) async {
    await Future.delayed(const Duration(milliseconds: 150));
    return [
      ModeOption(
        mode: TransportMode.bike,
        estimatedDuration: const Duration(minutes: 55),
        risk: _buildRisk(78),
        distanceKm: 35.5,
        recommendation: 'High risk due to waterlogging on key segments',
        highlights: [
          'Exposed to heavy rainfall 8:20–8:45 AM',
          'Waterlogging at Rajiv Chowk underpass',
          'Visibility drops below 200m in rain',
        ],
      ),
      ModeOption(
        mode: TransportMode.car,
        estimatedDuration: const Duration(minutes: 65),
        risk: _buildRisk(52),
        distanceKm: 35.5,
        recommendation: 'Moderate risk. Expect slowdowns near waterlogged areas',
        highlights: [
          'Protected from direct rain exposure',
          'Traffic congestion likely near Iffco Chowk',
          'Waterlogging may cause 15-min delay',
        ],
      ),
      ModeOption(
        mode: TransportMode.metro,
        estimatedDuration: const Duration(minutes: 75),
        risk: _buildRisk(12),
        distanceKm: 42.0,
        recommendation: 'Safest option. Weather-independent transit',
        highlights: [
          'No weather exposure during transit',
          'Aqua Line → Blue Line via Noida Sec 52',
          'Last-mile auto may face light rain',
        ],
      ),
    ];
  }

  // ── Helpers ──

  int _riskForTime(DateTime time, TransportMode mode) {
    final hour = time.hour;
    final modeMultiplier = switch (mode) {
      TransportMode.bike => 1.0,
      TransportMode.car => 0.67,
      TransportMode.metro => 0.15,
      TransportMode.walk => 1.1,
    };
    // Peak risk at 8AM, drops after 9:30AM
    final baseRisk = (hour >= 7 && hour <= 9) ? 78 : (hour <= 6 ? 25 : 35);
    return (baseRisk * modeMultiplier).round().clamp(0, 100);
  }

  RiskAssessment _buildRisk(int score) {
    return RiskAssessment(
      overallScore: score,
      level: _levelForScore(score),
      confidence: Confidence(
        level: ConfidenceLevel.high,
        explanation: 'Based on 3 weather models + real-time IMD radar',
      ),
      factors: [
        RiskFactor(
          name: 'Precipitation',
          description: 'Heavy rainfall 8:20–8:45 AM along NH-48',
          score: 82,
          level: RiskLevel.high,
          weight: 0.4,
        ),
        RiskFactor(
          name: 'Waterlogging',
          description: 'Known waterlogging at Rajiv Chowk underpass',
          score: 75,
          level: RiskLevel.high,
          weight: 0.25,
        ),
        RiskFactor(
          name: 'Visibility',
          description: 'Reduced to 200m during heavy rain',
          score: 60,
          level: RiskLevel.moderate,
          weight: 0.15,
        ),
        RiskFactor(
          name: 'Traffic',
          description: 'Congestion expected near Iffco Chowk',
          score: 55,
          level: RiskLevel.moderate,
          weight: 0.2,
        ),
      ],
      summary: 'High risk due to heavy rainfall and waterlogging on your route. '
          'Consider Metro or delay departure past 9:30 AM.',
    );
  }

  Recommendation _buildRecommendation(int riskScore, TransportMode mode) {
    if (riskScore >= 70) {
      return Recommendation(
        headline: 'Switch to Metro or delay to 9:30 AM',
        body: 'Heavy rainfall expected between 8:20–8:45 AM along your route. '
            'The Rajiv Chowk underpass has a known waterlogging history. '
            'Metro offers a weather-independent commute with comparable ETA.',
        alternativeAction: 'Take Aqua Line from Noida Sec 62 → Blue Line → Cyber Hub',
        suggestedMode: TransportMode.metro,
        suggestedDepartureTime: DateTime(2026, 8, 27, 9, 30),
      );
    }
    return Recommendation(
      headline: 'Proceed with caution',
      body: 'Conditions are manageable. Keep rain gear handy and monitor updates.',
    );
  }

  List<RouteSegment> _buildRoute(TransportMode mode) {
    // Noida Sec 62 → Gurgaon Cyber Hub route segments
    return [
      const RouteSegment(
        startLat: 28.6270, startLng: 77.3650, // Noida Sec 62
        endLat: 28.6150, endLng: 77.3400,
        riskLevel: RiskLevel.low,
        description: 'Noida Sec 62 to Noida Expressway',
      ),
      const RouteSegment(
        startLat: 28.6150, startLng: 77.3400,
        endLat: 28.5850, endLng: 77.2800,
        riskLevel: RiskLevel.moderate,
        description: 'Noida Expressway — light rain expected',
      ),
      RouteSegment(
        startLat: 28.5850, startLng: 77.2800,
        endLat: 28.5650, endLng: 77.2200,
        riskLevel: RiskLevel.high,
        description: 'DND Flyway to ITO — heavy rainfall zone',
        weather: WeatherPoint(
          time: DateTime(2026, 8, 27, 8, 20),
          temperature: 28,
          precipitation: 32,
          humidity: 92,
          windSpeed: 22,
          condition: 'Heavy Rain',
          icon: '🌧️',
        ),
      ),
      RouteSegment(
        startLat: 28.5650, startLng: 77.2200,
        endLat: 28.5400, endLng: 77.1700,
        riskLevel: RiskLevel.severe,
        description: 'Rajiv Chowk underpass — waterlogging risk',
        weather: WeatherPoint(
          time: DateTime(2026, 8, 27, 8, 35),
          temperature: 27,
          precipitation: 38,
          humidity: 95,
          windSpeed: 25,
          condition: 'Heavy Rain',
          icon: '⛈️',
        ),
      ),
      const RouteSegment(
        startLat: 28.5400, startLng: 77.1700,
        endLat: 28.4950, endLng: 77.0890,
        riskLevel: RiskLevel.moderate,
        description: 'NH-48 to Iffco Chowk — clearing rain',
      ),
      const RouteSegment(
        startLat: 28.4950, startLng: 77.0890,
        endLat: 28.4942, endLng: 77.0860, // Cyber Hub
        riskLevel: RiskLevel.low,
        description: 'Iffco Chowk to Cyber Hub',
      ),
    ];
  }

  List<Hazard> _buildHazards() {
    return [
      Hazard(
        id: 'h1',
        type: HazardType.waterlogging,
        title: 'Waterlogging — Rajiv Chowk Underpass',
        description: 'Chronic waterlogging point. Water level exceeds 1.5 ft '
            'during heavy rain. Two-wheelers should avoid.',
        lat: 28.5400,
        lng: 77.1700,
        severity: RiskLevel.severe,
        reportedAt: DateTime(2026, 8, 27, 7, 45),
        source: 'NDMA + Citizen Reports',
      ),
      Hazard(
        id: 'h2',
        type: HazardType.heavyRain,
        title: 'Heavy Rainfall — Central Delhi',
        description: 'IMD radar shows intense rain band moving NW. '
            'Expected to cross DND Flyway by 8:20 AM.',
        lat: 28.5650,
        lng: 77.2200,
        severity: RiskLevel.high,
        reportedAt: DateTime(2026, 8, 27, 7, 30),
        source: 'IMD Radar',
      ),
    ];
  }

  List<DataSource> _buildSources() {
    return [
      DataSource(
        name: 'India Meteorological Department',
        type: 'IMD',
        lastUpdated: DateTime(2026, 8, 27, 7, 30),
      ),
      DataSource(
        name: 'National Disaster Management Authority',
        type: 'NDMA',
        lastUpdated: DateTime(2026, 8, 27, 7, 0),
      ),
      DataSource(
        name: 'Google Maps Traffic',
        type: 'Traffic API',
        lastUpdated: DateTime(2026, 8, 27, 7, 55),
      ),
    ];
  }

  Duration _etaForMode(TransportMode mode) {
    return switch (mode) {
      TransportMode.bike => const Duration(minutes: 55),
      TransportMode.car => const Duration(minutes: 65),
      TransportMode.metro => const Duration(minutes: 75),
      TransportMode.walk => const Duration(minutes: 420),
    };
  }

  RiskLevel _levelForScore(int score) {
    if (score >= 75) return RiskLevel.severe;
    if (score >= 50) return RiskLevel.high;
    if (score >= 25) return RiskLevel.moderate;
    return RiskLevel.low;
  }
}

/// Mock implementation of WeatherRepository
class MockWeatherRepository implements WeatherRepository {
  @override
  Future<WeatherPoint> getCurrentWeather(String location) async {
    await Future.delayed(const Duration(milliseconds: 100));
    return WeatherPoint(
      time: DateTime.now(),
      temperature: 31,
      precipitation: 0,
      humidity: 78,
      windSpeed: 12,
      condition: 'Partly Cloudy',
      icon: '⛅',
    );
  }

  @override
  Future<List<WeatherPoint>> getForecast(String location, {int hours = 24}) async {
    await Future.delayed(const Duration(milliseconds: 200));
    final now = DateTime.now();
    return List.generate(hours, (i) {
      final time = now.add(Duration(hours: i));
      final isRainyWindow = time.hour >= 8 && time.hour <= 10;
      return WeatherPoint(
        time: time,
        temperature: isRainyWindow ? 27.0 : 31.0 + (i % 3),
        precipitation: isRainyWindow ? 28.0 + (i * 2) : 0,
        humidity: isRainyWindow ? 92 : 70,
        windSpeed: isRainyWindow ? 22 : 10,
        condition: isRainyWindow ? 'Heavy Rain' : 'Partly Cloudy',
        icon: isRainyWindow ? '🌧️' : '⛅',
      );
    });
  }
}

/// Mock implementation of RiskRepository
class MockRiskRepository implements RiskRepository {
  @override
  Future<RiskAssessment?> getRiskAssessment(TripRequest request) async {
    final tripRepo = MockTripRepository();
    final response = await tripRepo.analyzeTrip(request);
    return response.risk;
  }

  @override
  Future<List<Hazard>> getNearbyHazards(double lat, double lng,
      {double radiusKm = 10}) async {
    await Future.delayed(const Duration(milliseconds: 150));
    return [
      Hazard(
        id: 'h1',
        type: HazardType.waterlogging,
        title: 'Waterlogging — Rajiv Chowk Underpass',
        description: 'Chronic waterlogging point during monsoon.',
        lat: 28.5400,
        lng: 77.1700,
        severity: RiskLevel.severe,
        reportedAt: DateTime(2026, 8, 27, 7, 45),
        source: 'NDMA',
      ),
    ];
  }
}

/// Mock implementation of AlertRepository
class MockAlertRepository implements AlertRepository {
  @override
  Future<List<OfficialAlert>> getActiveAlerts({String? location}) async {
    await Future.delayed(const Duration(milliseconds: 200));
    return [
      OfficialAlert(
        id: 'a1',
        title: 'Orange Alert — Heavy Rainfall',
        description: 'IMD has issued an Orange Alert for Delhi-NCR. '
            'Heavy to very heavy rainfall expected in isolated areas. '
            'Avoid unnecessary travel, especially in low-lying areas.',
        severity: AlertSeverity.warning,
        issuedBy: 'India Meteorological Department',
        issuedAt: DateTime(2026, 8, 27, 6, 0),
        expiresAt: DateTime(2026, 8, 27, 18, 0),
        affectedAreas: ['Delhi', 'Noida', 'Gurgaon', 'Faridabad', 'Ghaziabad'],
        actionRequired: 'Avoid waterlogged roads. Do not cross flooded underpasses.',
        source: 'IMD',
      ),
      OfficialAlert(
        id: 'a2',
        title: 'Yellow Alert — Thunderstorm',
        description: 'Thunderstorm with lightning likely in parts of Haryana and '
            'Western UP during afternoon hours.',
        severity: AlertSeverity.watch,
        issuedBy: 'India Meteorological Department',
        issuedAt: DateTime(2026, 8, 27, 6, 0),
        expiresAt: DateTime(2026, 8, 27, 20, 0),
        affectedAreas: ['Gurgaon', 'Noida', 'Greater Noida'],
        actionRequired: 'Stay indoors during thunderstorm activity.',
        source: 'IMD',
      ),
      OfficialAlert(
        id: 'a3',
        title: 'Traffic Advisory — Waterlogging',
        description: 'Multiple underpasses in South Delhi reporting waterlogging. '
            'Traffic diversions in effect near Moolchand and Pragati Maidan.',
        severity: AlertSeverity.advisory,
        issuedBy: 'Delhi Traffic Police',
        issuedAt: DateTime(2026, 8, 27, 7, 30),
        affectedAreas: ['South Delhi', 'Central Delhi'],
        actionRequired: 'Use alternative routes. Check live traffic updates.',
        source: 'Delhi Traffic Police',
      ),
    ];
  }

  @override
  Future<OfficialAlert> getAlertDetail(String alertId) async {
    final alerts = await getActiveAlerts();
    return alerts.firstWhere((a) => a.id == alertId);
  }
}

/// Mock implementation of HistoryRepository
class MockHistoryRepository implements HistoryRepository {
  @override
  Future<List<HistoricalEvent>> getHistoricalEvents(
    String location, {
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    await Future.delayed(const Duration(milliseconds: 200));
    return [
      HistoricalEvent(
        date: DateTime(2026, 8, 15),
        title: 'Severe Waterlogging — Delhi-NCR',
        description: 'Record 120mm rainfall in 3 hours caused widespread '
            'waterlogging across Delhi-NCR. Major underpasses submerged.',
        severity: RiskLevel.severe,
        impacts: [
          '350+ vehicles stranded',
          'Metro services delayed 45 minutes',
          'NH-48 closed for 6 hours',
          '2 casualties reported',
        ],
        weatherTimeline: List.generate(12, (i) => WeatherPoint(
          time: DateTime(2026, 8, 15, 6 + i),
          temperature: 26.0 + (i % 3),
          precipitation: i >= 2 && i <= 5 ? 40.0 + (i * 8) : 5.0,
          humidity: i >= 2 && i <= 5 ? 96 : 75,
          windSpeed: i >= 2 && i <= 5 ? 35 : 10,
          condition: i >= 2 && i <= 5 ? 'Extreme Rain' : 'Cloudy',
          icon: i >= 2 && i <= 5 ? '⛈️' : '☁️',
        )),
      ),
      HistoricalEvent(
        date: DateTime(2026, 7, 28),
        title: 'Flash Floods — Gurgaon',
        description: 'Sudden downpour led to flash floods in Gurgaon. '
            'Golf Course Road and Sohna Road severely affected.',
        severity: RiskLevel.high,
        impacts: [
          'Golf Course Road submerged',
          'Power outages in 12 sectors',
          'Traffic gridlock for 4 hours',
        ],
        weatherTimeline: List.generate(8, (i) => WeatherPoint(
          time: DateTime(2026, 7, 28, 14 + i),
          temperature: 29.0,
          precipitation: i >= 1 && i <= 3 ? 55.0 : 8.0,
          humidity: 88,
          windSpeed: 18,
          condition: i >= 1 && i <= 3 ? 'Heavy Rain' : 'Overcast',
          icon: i >= 1 && i <= 3 ? '🌧️' : '☁️',
        )),
      ),
      HistoricalEvent(
        date: DateTime(2026, 7, 10),
        title: 'Heat Wave + Dust Storm',
        description: 'Temperatures exceeded 45°C followed by sudden dust storm '
            'with 70 km/h wind gusts.',
        severity: RiskLevel.high,
        impacts: [
          'Visibility dropped to 50m',
          'Trees uprooted on NH-48',
          '12 flights diverted from IGI',
        ],
        weatherTimeline: List.generate(8, (i) => WeatherPoint(
          time: DateTime(2026, 7, 10, 12 + i),
          temperature: 45.0 - (i * 2),
          precipitation: i >= 4 ? 5.0 : 0,
          humidity: i >= 4 ? 60 : 20,
          windSpeed: i >= 3 && i <= 5 ? 70 : 15,
          condition: i >= 3 && i <= 5 ? 'Dust Storm' : 'Extreme Heat',
          icon: i >= 3 && i <= 5 ? '🌪️' : '🔥',
        )),
      ),
    ];
  }
}
