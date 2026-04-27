"""
routes/crop.py
Crop recommendation endpoint with optional live weather integration.
"""

import logging
import asyncio
from fastapi import APIRouter, HTTPException

from schemas.requests import CropRequest
from tools.crop_tool import crop_tool
from llm.llm_engine import generate_explanation, suggest_next_action, _build_seasonal_reason
from services.weather_service import weather_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Crop Recommendation"])


@router.post(
    "/crop",
    summary="Recommend crops based on soil and weather conditions",
    response_description="Ranked crop recommendations with seasonal intelligence",
)
async def recommend_crop(req: CropRequest):
    """
    Inputs: Soil NPK, pH, temperature, humidity, rainfall, month, optional location.

    Returns: Ranked crop recommendations with seasonal and weather scoring.
    """
    try:
        params = req.model_dump()

        # Auto-fetch weather if location provided
        if req.location:
            weather = weather_service.get_weather(req.location)
            if weather.get("success"):
                wd = weather["data"]
                params["temperature"] = wd["temperature"]
                params["humidity"] = wd["humidity"]
                if not params.get("rainfall"):
                    params["rainfall"] = wd["rainfall"]
                logger.info(f"Live weather for {req.location}: {wd}")
            else:
                logger.warning(f"Weather API failed for {req.location}: {weather.get('error')}")

        # Validate required fields after potential weather fill
        missing = [f for f in ["temperature", "humidity", "rainfall"] if params.get(f) is None]
        if missing:
            raise HTTPException(
                status_code=422,
                detail=f"Missing required fields: {missing}. Provide them directly or use 'location' for auto-fetch.",
            )

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, crop_tool, params)

        if not result.get("success", True):
            raise HTTPException(status_code=422, detail=result.get("error", "Crop tool failed"))

        explanation = generate_explanation("recommend_crop", result)
        next_action = suggest_next_action("recommend_crop", result)

        primary_crop = result.get("primary_crop") or result.get("primary_recommendation")
        rankings = result.get("top_recommendations", [])
        top_data = rankings[0] if rankings else {}
        season = result.get("season", "unknown")
        seasonal_score = top_data.get("seasonal_score", 0.0)
        weather_score = top_data.get("weather_score", 0.0)
        why_now = _build_seasonal_reason(primary_crop or "", season, seasonal_score, weather_score)

        return {
            "success": True,
            "tool": "crop_recommendation",
            "explanation": explanation,
            "next_action": next_action,
            "primary_recommendation": primary_crop,
            "primary_crop": primary_crop,
            "season": season,
            "seasonal_score": seasonal_score,
            "weather_score": weather_score,
            "why_this_crop_now": why_now,
            "confidence": result.get("confidence"),
            "uncertainty_score": result.get("uncertainty_score"),
            "top_recommendations": rankings,
            "raw": result,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("recommend_crop failed")
        raise HTTPException(status_code=500, detail=str(e))
