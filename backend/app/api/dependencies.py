from app.providers.weather.mock import MockWeatherProvider
from app.providers.weather.open_meteo import OpenMeteoWeatherProvider
from app.providers.weather.fallback import FallbackWeatherProvider
from app.providers.routing.mock import MockRoutingProvider
from app.providers.routing.google_routes import GoogleRoutesProvider
from app.providers.routing.fallback import FallbackRoutingProvider
from app.providers.traffic.mock import MockTrafficProvider
from app.providers.alerts.mock import MockAlertProvider
from app.providers.llm.mock import MockLLMProvider

from app.providers.weather.base import WeatherProvider
from app.providers.alerts.base import AlertProvider
from app.providers.traffic.base import TrafficProvider
from app.services.trip_service import TripService
from app.services.scenario_service import ScenarioService
from app.services.assistant_service import AssistantService
from app.core.config import settings
import os

# Dependency Injection setup
_mock_weather = MockWeatherProvider()
if settings.weather_provider == "open-meteo":
    _open_meteo = OpenMeteoWeatherProvider()
    # In production, NEVER silently substitute mock weather
    _secondary = None if settings.is_production else (_mock_weather if settings.demo_mode else None)
    weather_provider = FallbackWeatherProvider(primary=_open_meteo, secondary=_secondary)
else:
    weather_provider = _mock_weather

_mock_routing = MockRoutingProvider()
if settings.routing_provider == "google":
    _google_routing = GoogleRoutesProvider()
    routing_provider = FallbackRoutingProvider(primary=_google_routing)
else:
    routing_provider = _mock_routing

traffic_provider = MockTrafficProvider()
alert_provider = MockAlertProvider()

if settings.llm_api_key or os.environ.get("GEMINI_API_KEY"):
    from app.providers.llm.gemini import GeminiLLMProvider
    llm_provider = GeminiLLMProvider()
else:
    llm_provider = MockLLMProvider()

from app.repositories.mock_hazard_repository import MockHazardRepository
from app.repositories.firestore.client import get_firestore_client
from app.repositories.firestore.trip_repository import FirestoreTripRepository
from app.repositories.firestore.user_repository import FirestoreUserRepository
from app.repositories.firestore.conversation_repository import FirestoreConversationRepository

firestore_client = get_firestore_client()
trip_repository = FirestoreTripRepository(firestore_client)
user_repository = FirestoreUserRepository(firestore_client)
conversation_repository = FirestoreConversationRepository(firestore_client)

# Repositories
hazard_repository = MockHazardRepository()

trip_service = TripService(
    weather_provider=weather_provider, 
    routing_provider=routing_provider, 
    alert_provider=alert_provider,
    traffic_provider=traffic_provider,
    hazard_repository=hazard_repository,
    trip_repository=trip_repository
)
scenario_service = ScenarioService(trip_service)
assistant_service = AssistantService(
    llm_provider, 
    trip_service=trip_service,
    conversation_repository=conversation_repository
)

def get_trip_service() -> TripService:
    return trip_service

def get_scenario_service() -> ScenarioService:
    return scenario_service

def get_assistant_service() -> AssistantService:
    return assistant_service

def get_weather_provider() -> WeatherProvider:
    return weather_provider

def get_alert_provider() -> AlertProvider:
    return alert_provider

def get_traffic_provider() -> TrafficProvider:
    return traffic_provider

def get_trip_repository() -> FirestoreTripRepository:
    return trip_repository

def get_user_repository() -> FirestoreUserRepository:
    return user_repository

def get_conversation_repository() -> FirestoreConversationRepository:
    return conversation_repository

def get_hazard_repository() -> MockHazardRepository:
    return hazard_repository
