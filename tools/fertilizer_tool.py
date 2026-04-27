"""
tools/fertilizer_tool.py
Thin wrapper around FertilizerRecommender.
"""

import os
import logging
from core.fertilizer_rec import FertilizerRecommender

logger = logging.getLogger(__name__)

_model: FertilizerRecommender = None


def _get_model() -> FertilizerRecommender:
    global _model
    if _model is None:
        rec = FertilizerRecommender()
        rec.load()
        _model = rec
        logger.info("Fertilizer model loaded")
    return _model


# Tool schema 
FERTILIZER_TOOL_SCHEMA = {
    "name": "recommend_fertilizer",
    "description": (
        "Recommend the best fertilizer based on soil type, crop type, "
        "NPK levels, temperature, humidity, and moisture."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "temperature":  {"type": "number", "description": "Temperature in Celsius"},
            "humidity":     {"type": "number", "description": "Humidity percentage"},
            "moisture":     {"type": "number", "description": "Soil moisture percentage"},
            "nitrogen":     {"type": "number", "description": "Nitrogen level"},
            "phosphorous":  {"type": "number", "description": "Phosphorus level"},
            "potassium":    {"type": "number", "description": "Potassium level"},
            "soil_type":    {"type": "string", "description": "Soil type (Sandy, Loamy, Black, Red, Clayey)"},
            "crop_type":    {"type": "string", "description": "Crop type (e.g., Wheat, Rice, Maize)"},
        },
        "required": ["temperature", "humidity", "moisture", "nitrogen", "phosphorous", "potassium", "soil_type", "crop_type"],
    },
}


def fertilizer_tool(params: dict) -> dict:
    """Execute fertilizer recommendation."""
    try:
        model = _get_model()
        return model.recommend(
            temperature=float(params["temperature"]),
            humidity=float(params["humidity"]),
            moisture=float(params["moisture"]),
            nitrogen=float(params["nitrogen"]),
            phosphorous=float(params["phosphorous"]),
            potassium=float(params["potassium"]),
            soil_type=str(params["soil_type"]),
            crop_type=str(params["crop_type"]),
        )
    except (KeyError, TypeError, ValueError) as e:
        logger.exception("fertilizer_tool validation error")
        return {"type": "fertilizer_recommendation", "success": False, "error": str(e)}
    except Exception as e:
        logger.exception("fertilizer_tool execution error")
        return {"type": "fertilizer_recommendation", "success": False, "error": str(e)}
