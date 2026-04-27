"""
tools/disease_tool.py
Thin wrapper around DiseaseDetector.
"""

import logging
from core.disease_detector import DiseaseDetector

logger = logging.getLogger(__name__)

_detector: DiseaseDetector = None


def _get_detector() -> DiseaseDetector:
    global _detector
    if _detector is None:
        det = DiseaseDetector()
        det.load()
        _detector = det
        logger.info(" Disease detector loaded")
    return _detector


# Tool schema 
DISEASE_TOOL_SCHEMA = {
    "name": "detect_disease",
    "description": (
        "Detect plant disease from a leaf image. "
        "Provide either image_path (file path) or image_base64 (base64 string)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "image_path":   {"type": "string", "description": "Path to the image file"},
            "image_base64": {"type": "string", "description": "Base64-encoded image string"},
        },
    },
}


def disease_tool(params: dict) -> dict:
    """Execute disease detection."""
    try:
        detector = _get_detector()
        return detector.predict(
            image_path=params.get("image_path"),
            image_base64=params.get("image_base64"),
        )
    except Exception as e:
        logger.exception("disease_tool execution error")
        return {"type": "disease_detection", "success": False, "error": str(e)}
