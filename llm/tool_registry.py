"""
llm/tool_registry.py
Central registry mapping tool names to callable functions.
"""

from tools.crop_tool import crop_tool
from tools.fertilizer_tool import fertilizer_tool
from tools.disease_tool import disease_tool
from tools.weather_tool import weather_tool

TOOL_REGISTRY = {
    "recommend_crop":       crop_tool,
    "recommend_fertilizer": fertilizer_tool,
    "detect_disease":       disease_tool,
    "get_weather":          weather_tool,
}
