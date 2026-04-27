"""
services/weather_service.py
Live weather integration via OpenWeatherMap API.
"""

import os
import logging
import requests
from typing import Dict

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


class WeatherService:

    def __init__(self):
        self.api_key: str = ""

    def _load_api_key(self):
        if not self.api_key:
            self.api_key = os.getenv("WEATHER_API_KEY", "")
            if not self.api_key:
                raise ValueError(
                    "WEATHER_API_KEY not set. Add it to your .env file. "
                    "Get a free key at https://openweathermap.org/api"
                )

    def get_weather(self, city: str) -> Dict:
        try:
            self._load_api_key()
            params = {"q": city, "appid": self.api_key, "units": "metric"}
            response = requests.get(BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            rainfall = data.get("rain", {}).get("1h", 0.0)
            result = {
                "city": city,
                "temperature": float(data["main"]["temp"]),
                "humidity": float(data["main"]["humidity"]),
                "rainfall": float(rainfall),
                "weather_condition": data["weather"][0]["description"],
            }
            logger.info(f"Weather fetched for {city}: {result}")
            return {"success": True, "data": result}
        except Exception as e:
            logger.exception(f"Weather fetch failed for {city}")
            return {"success": False, "error": str(e)}


weather_service = WeatherService()
