"""
schemas/requests.py
Pydantic request models for all API endpoints
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class CropRequest(BaseModel):
    N: float = Field(..., ge=0, le=300, description="Nitrogen level (kg/ha)")
    P: float = Field(..., ge=0, le=300, description="Phosphorus level (kg/ha)")
    K: float = Field(..., ge=0, le=300, description="Potassium level (kg/ha)")
    temperature: Optional[float] = Field(None, ge=-10, le=60, description="Temperature in Celsius")
    humidity: Optional[float] = Field(None, ge=0, le=100, description="Humidity percentage")
    ph: float = Field(..., ge=0, le=14, description="Soil pH")
    rainfall: Optional[float] = Field(None, ge=0, description="Rainfall in mm")
    month: Optional[int] = Field(None, ge=1, le=12, description="Month (1-12)")
    top_n: int = Field(5, ge=1, le=10, description="Number of top recommendations")
    location: Optional[str] = Field(None, description="City name for live weather fetch")

    @field_validator("temperature", "humidity", "rainfall", mode="before")
    @classmethod
    def allow_none(cls, v):
        return v


class FertilizerRequest(BaseModel):
    temperature: float = Field(..., ge=-10, le=60, description="Temperature in Celsius")
    humidity: float = Field(..., ge=0, le=100, description="Humidity percentage")
    moisture: float = Field(..., ge=0, le=100, description="Soil moisture percentage")
    nitrogen: float = Field(..., ge=0, le=300, description="Nitrogen level")
    phosphorous: float = Field(..., ge=0, le=300, description="Phosphorus level")
    potassium: float = Field(..., ge=0, le=300, description="Potassium level")
    soil_type: str = Field(..., description="Soil type (Sandy, Loamy, Black, Red, Clayey)")
    crop_type: str = Field(..., description="Crop type (e.g., Wheat, Rice, Maize)")


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="Natural language query")
    session_id: Optional[str] = Field(None, description="Session ID for conversation memory")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Pre-parsed parameters")
