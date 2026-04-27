"""
config.py
Centralized application settings using pydantic-settings
"""

from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):

    # LLM provider
    # Options: openai | ollama | gemini | mock

    llm_provider: str = "gemini"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Groq
    groq_api_key: str = ""
    groq_model: str = "llama3-8b-8192"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:1b"

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

   
    # Server

    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    reload: bool = False

  
    # CORS
    allowed_origins: list = [
        "http://localhost:3000",
        "http://localhost:8000",
        "*",
    ]


    # Model paths

    crop_model_path: str = str(BASE_DIR / "models" / "crop_model.pkl")
    fertilizer_model_path: str = str(BASE_DIR / "models" / "fertilizer_model.pkl")
    fertilizer_encoders_path: str = str(BASE_DIR / "models" / "encoders.pkl")
    fertilizer_features_path: str = str(BASE_DIR / "models" / "feature_names.pkl")
    disease_model_path: str = str(BASE_DIR / "models" / "disease_model.pth")


    # Rate limiting
    rate_limit_per_minute: int = 200
    rate_limit_chat_per_minute: int = 20


    # Memory

    max_chat_history: int = 10


    # Weather
    weather_api_key: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
