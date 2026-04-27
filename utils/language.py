"""
utils/language.py
Language detection helpers
"""

SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "te": "Telugu",
    "ta": "Tamil",
    "kn": "Kannada",
}


def detect_language(text: str) -> str:
    """
    Detect user language using langdetect.
    Falls back to English on any error.
    """
    try:
        from langdetect import detect
        lang = detect(text)
        return lang if lang in SUPPORTED_LANGUAGES else "en"
    except Exception:
        return "en"
