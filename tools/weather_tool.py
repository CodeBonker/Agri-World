"""
tools/weather_tool.py
Weather tool wrapper for LLM tool-calling.
"""

import logging
from services.weather_service import weather_service

logger = logging.getLogger(__name__)

WEATHER_TOOL_SCHEMA = {
    "name": "get_weather",
    "description": "Fetch live weather data (temperature, humidity, rainfall) for a given city.",
    "parameters": {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "City name (e.g., Hyderabad, Mumbai)"},
        },
        "required": ["city"],
    },
}


def weather_tool(params: dict) -> dict:
    """Fetch weather for a city."""
    try:
        city = params.get("city", "").strip()
        if not city:
            return {"success": False, "error": "City name is required."}
        return weather_service.get_weather(city)
    except Exception as e:
        logger.exception("weather_tool error")
        return {"success": False, "error": str(e)}
