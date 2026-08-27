from app.providers.weather.base import WeatherProvider

class WeatherService:
    def __init__(self, weather_provider: WeatherProvider):
        self.provider = weather_provider
