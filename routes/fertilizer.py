"""
routes/fertilizer.py
Fertilizer recommendation endpoint.
"""

import logging
from fastapi import APIRouter, HTTPException

from schemas.requests import FertilizerRequest
from tools.fertilizer_tool import fertilizer_tool
from llm.llm_engine import generate_explanation, suggest_next_action

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Fertilizer Recommendation"])


@router.post(
    "/fertilizer",
    summary="Recommend fertilizer based on soil nutrients and crop type",
    response_description="Primary fertilizer recommendation with top-K alternatives",
)
def recommend_fertilizer(req: FertilizerRequest):
    """
    Inputs: Temperature, humidity, moisture, N/P/K levels, soil type, crop type.

    Returns: Primary fertilizer + ranked alternatives with confidence scores.
    Rule-based override applied when NPK deficiency is critical.
    """
    params = req.model_dump()
    result = fertilizer_tool(params)

    if not result.get("success", True):
        raise HTTPException(status_code=422, detail=result.get("error", "Fertilizer tool failed"))

    explanation = generate_explanation("recommend_fertilizer", result)
    next_action = suggest_next_action("recommend_fertilizer", result)

    return {
        "success": True,
        "tool": "fertilizer_recommendation",
        "explanation": explanation,
        "next_action": next_action,
        "primary_fertilizer": result.get("primary_fertilizer"),
        "confidence": result.get("confidence"),
        "rule_applied": result.get("rule_applied"),
        "rule_reason": result.get("rule_reason"),
        "top_recommendations": result.get("top_recommendations", []),
        "input_summary": result.get("input_summary", {}),
        "raw": result,
    }
