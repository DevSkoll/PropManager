import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

OPENWEATHERMAP_BASE_URL = "https://api.openweathermap.org/data/2.5"


class WeatherService:
    def __init__(self):
        self.api_key = settings.OPENWEATHERMAP_API_KEY

    def get_current_weather(self, lat, lon):
        if not self.api_key:
            logger.warning("OpenWeatherMap API key not configured")
            return None
        try:
            response = requests.get(
                f"{OPENWEATHERMAP_BASE_URL}/weather",
                params={
                    "lat": lat,
                    "lon": lon,
                    "appid": self.api_key,
                    "units": "imperial",
                },
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            logger.exception(f"Failed to fetch weather for ({lat}, {lon})")
            return None


weather_service = WeatherService()
