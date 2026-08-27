from app.providers.weather.mock import MockWeatherProvider
from app.providers.weather.open_meteo import OpenMeteoWeatherProvider
from app.providers.weather.fallback import FallbackWeatherProvider
from app.providers.routing.mock import MockRoutingProvider
from app.providers.traffic.mock import MockTrafficProvider
from app.providers.alerts.mock import MockAlertProvider
from app.providers.llm.mock import MockLLMProvider

from app.services.trip_service import TripService
from app.services.scenario_service import ScenarioService
from app.services.assistant_service import AssistantService
from app.core.config import settings

# Dependency Injection setup
_mock_weather = MockWeatherProvider()
if settings.weather_provider == "open-meteo":
    _open_meteo = OpenMeteoWeatherProvider()
    weather_provider = FallbackWeatherProvider(primary=_open_meteo, secondary=_mock_weather)
else:
    weather_provider = _mock_weather

routing_provider = MockRoutingProvider()
traffic_provider = MockTrafficProvider()
alert_provider = MockAlertProvider()
llm_provider = MockLLMProvider()

trip_service = TripService(weather_provider, routing_provider, alert_provider)
scenario_service = ScenarioService(trip_service)
assistant_service = AssistantService(llm_provider)

def get_trip_service() -> TripService:
    return trip_service

def get_scenario_service() -> ScenarioService:
    return scenario_service

def get_assistant_service() -> AssistantService:
    return assistant_service
