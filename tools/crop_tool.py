"""
tools/crop_tool.py
Thin wrapper around CropRecommender — loads model once, exposes tool function.
"""

import os
import logging
from core.crop_recommender import CropRecommender

logger = logging.getLogger(__name__)

_model: CropRecommender = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MODEL_PATH = os.path.join(BASE_DIR, "models", "crop_model.pkl")
DEFAULT_EXT_DATA = os.path.join(BASE_DIR, "data", "synthetic_102_crop_dataset.csv")


def _get_model() -> CropRecommender:
    global _model
    if _model is None:
        model_path = os.getenv("CROP_MODEL_PATH", DEFAULT_MODEL_PATH)
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Crop model not found at '{model_path}'. "
                "Run: python scripts/train_models.py"
            )
        rec = CropRecommender()
        rec.load(model_path)
        if os.path.exists(DEFAULT_EXT_DATA):
            rec.fit_extended(DEFAULT_EXT_DATA)
            logger.info(" Extended crop model loaded")
        _model = rec
        logger.info(f" Crop model loaded from {model_path}")
    return _model


# Tool schema (OpenAI / Gemini / Ollama function-calling compatible)

CROP_TOOL_SCHEMA = {
    "name": "recommend_crop",
    "description": (
        "Recommend the best crop based on soil nutrients (NPK), pH, "
        "temperature, humidity, rainfall, and month."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "N":           {"type": "number", "description": "Nitrogen level (0–300 kg/ha)"},
            "P":           {"type": "number", "description": "Phosphorus level (0–300 kg/ha)"},
            "K":           {"type": "number", "description": "Potassium level (0–300 kg/ha)"},
            "temperature": {"type": "number", "description": "Temperature in Celsius"},
            "humidity":    {"type": "number", "description": "Humidity percentage (0–100)"},
            "ph":          {"type": "number", "description": "Soil pH (0–14)"},
            "rainfall":    {"type": "number", "description": "Rainfall in mm"},
            "month":       {"type": "integer", "description": "Month (1–12)"},
            "top_n":       {"type": "integer", "description": "Number of top recommendations (1–10)"},
        },
        "required": ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"],
    },
}


def crop_tool(params: dict) -> dict:
    """Execute crop recommendation. Always returns structured output."""
    try:
        model = _get_model()

        N           = float(params["N"])
        P           = float(params["P"])
        K           = float(params["K"])
        temperature = float(params["temperature"])
        humidity    = float(params["humidity"])
        ph          = float(params["ph"])
        rainfall    = float(params["rainfall"])
        month       = params.get("month")
        top_n       = int(params.get("top_n", 5))

        if not (1 <= top_n <= 10):
            return {"type": "crop_recommendation", "success": False, "error": "top_n must be 1–10."}

        if month is not None:
            month = int(month)
            if not (1 <= month <= 12):
                return {"type": "crop_recommendation", "success": False, "error": "month must be 1–12."}

        return model.recommend(
            N=N, P=P, K=K,
            temperature=temperature, humidity=humidity,
            ph=ph, rainfall=rainfall,
            month=month, top_n=top_n,
        )

    except (KeyError, TypeError, ValueError) as e:
        logger.exception("crop_tool validation error")
        return {"type": "crop_recommendation", "success": False, "error": str(e)}
    except Exception as e:
        logger.exception("crop_tool execution error")
        return {"type": "crop_recommendation", "success": False, "error": str(e)}
