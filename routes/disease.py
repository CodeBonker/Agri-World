"""
routes/disease.py
Plant disease detection endpoint.
Accepts multipart image upload OR base64 JSON body.
"""

import os
import uuid
import logging
import aiofiles
from fastapi import APIRouter, UploadFile, File, HTTPException, Body

from tools.disease_tool import disease_tool
from llm.llm_engine import generate_explanation, suggest_next_action

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Disease Detection"])

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
MAX_FILE_SIZE_MB = 10
TEMP_DIR = "temp_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)


def _validate_extension(filename: str) -> str:
    ext = os.path.splitext(filename)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )
    return ext


def _clean_label(label: str) -> str:
    if not isinstance(label, str):
        return label
    return label.replace("___", " - ").replace("_", " ")


def _normalize_alternatives(raw: list) -> list:
    return [
        {
            "disease": _clean_label(alt.get("disease") or alt.get("class") or "unknown"),
            "confidence": alt.get("confidence", 0.0),
        }
        for alt in raw
    ]


@router.post(
    "/disease",
    summary="Detect plant disease from a leaf image (file upload)",
    response_description="Disease name, confidence, severity, and treatment recommendations",
)
async def detect_disease_upload(file: UploadFile = File(...)):
    """
    Input: Multipart image file (JPG/PNG/WEBP, max 10 MB)

    Returns: Disease classification, confidence, severity, and treatment plan.
    Supports 38 disease classes across Apple, Corn, Grape, Tomato, Potato, and more.
    """
    _validate_extension(file.filename)

    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f} MB). Max: {MAX_FILE_SIZE_MB} MB.",
        )

    ext = os.path.splitext(file.filename)[-1].lower()
    temp_path = f"{TEMP_DIR}/{uuid.uuid4().hex}{ext}"

    try:
        async with aiofiles.open(temp_path, "wb") as f:
            await f.write(contents)

        result = disease_tool({"image_path": temp_path})

        if not result.get("success", True):
            raise HTTPException(status_code=500, detail=result.get("error", "Disease detection failed"))

        explanation = generate_explanation("detect_disease", result)
        next_action = suggest_next_action("detect_disease", result)
        top_recs = _normalize_alternatives(result.get("top_3", result.get("top_recommendations", [])))

        return {
            "success": True,
            "tool": "disease_detection",
            "explanation": explanation,
            "next_action": next_action,
            "primary_disease": _clean_label(result.get("primary_disease")),
            "crop": result.get("crop"),
            "confidence": result.get("confidence"),
            "is_healthy": result.get("is_healthy"),
            "severity": result.get("severity"),
            "treatment_recommendations": result.get("treatment_recommendations", []),
            "top_3": top_recs,
            "raw": result,
        }

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.post(
    "/disease/base64",
    summary="Detect plant disease from a base64-encoded image",
)
def detect_disease_base64(payload: dict = Body(...)):
    """
    Input: JSON body with `image_base64` field (base64-encoded image string).
    Useful for mobile apps and web clients.
    """
    image_base64 = payload.get("image_base64")
    if not image_base64:
        raise HTTPException(status_code=422, detail="Field 'image_base64' is required.")

    result = disease_tool({"image_base64": image_base64})

    if not result.get("success", True):
        raise HTTPException(status_code=500, detail=result.get("error", "Disease detection failed"))

    explanation = generate_explanation("detect_disease", result)
    next_action = suggest_next_action("detect_disease", result)
    top_recs = _normalize_alternatives(result.get("top_3", result.get("top_recommendations", [])))

    return {
        "success": True,
        "tool": "disease_detection",
        "explanation": explanation,
        "next_action": next_action,
        "primary_disease": _clean_label(result.get("primary_disease")),
        "crop": result.get("crop"),
        "confidence": result.get("confidence"),
        "is_healthy": result.get("is_healthy"),
        "severity": result.get("severity"),
        "treatment_recommendations": result.get("treatment_recommendations", []),
        "top_3": top_recs,
        "raw": result,
    }
