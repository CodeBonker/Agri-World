"""
schemas/responses.py
Pydantic response models
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class CropRecommendation(BaseModel):
    crop: str
    composite_score: float
    ml_probability: float
    seasonal_score: float
    weather_score: float


class CropResponse(BaseModel):
    success: bool
    tool: str
    explanation: str
    next_action: str
    primary_recommendation: Optional[str]
    season: Optional[str]
    confidence: Optional[str]
    top_recommendations: List[CropRecommendation]


class FertilizerRecommendation(BaseModel):
    fertilizer: str
    probability: float


class FertilizerResponse(BaseModel):
    success: bool
    tool: str
    explanation: str
    next_action: str
    primary_fertilizer: Optional[str]
    confidence: Optional[float]
    rule_applied: Optional[bool]
    top_recommendations: List[FertilizerRecommendation]


class DiseaseResponse(BaseModel):
    success: bool
    tool: str
    explanation: str
    next_action: str
    primary_disease: Optional[str]
    crop: Optional[str]
    confidence: Optional[float]
    is_healthy: Optional[bool]
    severity: Optional[str]


class ChatResponse(BaseModel):
    success: bool
    session_id: Optional[str]
    intent: str
    tool_used: str
    explanation: str
    next_action: str
    result: Optional[Dict[str, Any]]
    llm_mode: str
