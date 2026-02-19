import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

OPENWEATHERMAP_BASE_URL = "https://api.openweathermap.org/data/2.5"
OPENWEATHERMAP_GEO_URL = "https://api.openweathermap.org/geo/1.0"


class WeatherService:
    def __init__(self):
        self.api_key = settings.OPENWEATHERMAP_API_KEY

    def geocode_zip(self, zip_code, country_code="US"):
        """Convert a ZIP code to latitude/longitude.

        Tries OpenWeatherMap geocoding first (if API key is configured),
        then falls back to the free zippopotam.us service.

        Returns a dict with 'lat' and 'lon' keys, or None on failure.
        """
        if self.api_key:
            result = self._geocode_zip_owm(zip_code, country_code)
            if result:
                return result

        return self._geocode_zip_fallback(zip_code, country_code)

    def _geocode_zip_owm(self, zip_code, country_code):
        """Geocode via OpenWeatherMap."""
        try:
            response = requests.get(
                f"{OPENWEATHERMAP_GEO_URL}/zip",
                params={
                    "zip": f"{zip_code},{country_code}",
                    "appid": self.api_key,
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            return {"lat": data["lat"], "lon": data["lon"]}
        except requests.RequestException:
            logger.exception("OWM geocoding failed for ZIP %s", zip_code)
            return None
        except (KeyError, ValueError):
            logger.warning("Unexpected OWM geocoding response for ZIP %s", zip_code)
            return None

    def _geocode_zip_fallback(self, zip_code, country_code):
        """Geocode via zippopotam.us (free, no API key required)."""
        try:
            response = requests.get(
                f"https://api.zippopotam.us/{country_code.lower()}/{zip_code}",
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            place = data["places"][0]
            return {
                "lat": float(place["latitude"]),
                "lon": float(place["longitude"]),
            }
        except requests.RequestException:
            logger.exception("Fallback geocoding failed for ZIP %s", zip_code)
            return None
        except (KeyError, IndexError, ValueError):
            logger.warning("Unexpected fallback geocoding response for ZIP %s", zip_code)
            return None

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
