"""
main.py
CropSeek LLM — FastAPI application entry point.

Features:
  - Crop recommendation (ML + seasonal intelligence)
  - Fertilizer recommendation (ML + rule-based overrides)
  - Plant disease detection (PyTorch CNN)
  - LLM-powered chat (Ollama / OpenAI / Gemini mock fallback)
  - Live weather integration (OpenWeatherMap)
  - Multilingual support (EN, HI, TE, TA, KN)
  - Rate limiting, CORS, GZip, request logging
"""

import os
import sys
import logging
import datetime
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("agri_api")

from config import get_settings
settings = get_settings()

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("  CropSeek LLM — Starting up")
    logger.info("=" * 60)

    # Load crop model
    try:
        from tools.crop_tool import _get_model as load_crop
        load_crop()
        logger.info("  Crop model loaded")
    except Exception as e:
        logger.error(f"  Crop model FAILED: {e}")

    # Load fertilizer model
    try:
        from tools.fertilizer_tool import _get_model as load_fert
        load_fert()
        logger.info("  Fertilizer model loaded")
    except Exception as e:
        logger.error(f"  Fertilizer model FAILED: {e}")

    # Load disease model (optional — .pth may not exist)
    try:
        from tools.disease_tool import _get_detector as load_disease
        load_disease()
        logger.info("  Disease model loaded")
    except Exception as e:
        logger.warning(f"   Disease model not loaded (train it first): {e}")

    # Initialize LLM engine
    try:
        from llm.llm_engine import get_engine
        engine = get_engine()
        provider = settings.llm_provider
        model_name = (
            settings.ollama_model if provider == "ollama"
            else settings.openai_model if provider == "openai"
            else settings.gemini_model if provider in ("gemini", "google")
            else "rule-based"
        )
        logger.info(f"  LLM engine ready — provider: {provider} / model: {model_name}")
    except Exception as e:
        logger.error(f"  LLM engine FAILED: {e}")

    logger.info("=" * 60)
    logger.info(f"  Server:  http://{settings.host}:{settings.port}")
    logger.info(f"  Docs:    http://{settings.host}:{settings.port}/docs")
    logger.info(f"  LLM:     {settings.llm_provider}")
    logger.info("=" * 60)

    yield

    logger.info("CropSeek LLM — Shutting down.")


app = FastAPI(
    title="CropSeek LLM — Agriculture AI Assistant",
    description=(
        "AI-powered agriculture decision support system. "
        "Provides crop recommendations, fertilizer advice, "
        "plant disease detection, and LLM-powered farming chat."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Request logging
from middleware.logging import log_requests
app.middleware("http")(log_requests)


#  Exception handlers

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        field = " → ".join(str(loc) for loc in err["loc"] if loc != "body")
        errors.append(f"{field}: {err['msg']}")
    return JSONResponse(
        status_code=422,
        content={"success": False, "error": "Validation failed", "detail": errors},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception on {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error. Please try again."},
    )


# Routers

from routes.crop import router as crop_router
from routes.fertilizer import router as fert_router
from routes.disease import router as disease_router
from routes.chat import router as chat_router

app.include_router(crop_router)
app.include_router(fert_router)
app.include_router(disease_router)
app.include_router(chat_router)


# Root & health endpoints
@app.get("/", tags=["System"])
def root():
    return {
        "name":    "CropSeek LLM — Agriculture AI Assistant",
        "version": "1.0.0",
        "status":  "running",
        "docs":    "/docs",
        "llm":     settings.llm_provider,
        "endpoints": {
            "crop":       "POST /api/crop",
            "fertilizer": "POST /api/fertilizer",
            "disease":    "POST /api/disease",
            "chat":       "POST /api/chat",
            "health":     "GET  /health",
        },
    }


@app.get("/health", tags=["System"])
def health():
    crop_loaded = fert_loaded = disease_loaded = False

    try:
        from tools.crop_tool import _get_model
        _get_model()
        crop_loaded = True
    except Exception:
        pass

    try:
        from tools.fertilizer_tool import _get_model
        _get_model()
        fert_loaded = True
    except Exception:
        pass

    try:
        from tools.disease_tool import _get_detector
        _get_detector()
        disease_loaded = True
    except Exception:
        pass

    return {
        "status": "healthy",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "models": {
            "crop":       "loaded" if crop_loaded else "not loaded",
            "fertilizer": "loaded" if fert_loaded else "not loaded",
            "disease":    "loaded" if disease_loaded else "not loaded (train first)",
        },
        "llm": {
            "provider": settings.llm_provider,
            "model": (
                settings.ollama_model if settings.llm_provider == "ollama"
                else settings.openai_model if settings.llm_provider == "openai"
                else settings.gemini_model if settings.llm_provider in ("gemini", "google")
                else "mock/rule-based"
            ),
        },
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level="info",
    )
