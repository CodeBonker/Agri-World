"""
llm/llm_engine.py
LLM routing engine supporting: openai | ollama | gemini | mock (rule-based fallback)

Key responsibilities:
  - Route queries to the correct LLM backend
  - Parse tool-call JSON from LLM responses
  - Execute tools via TOOL_REGISTRY
  - Generate farmer-friendly explanations
  - Maintain per-session conversation memory
"""

import json
import re
import datetime
import logging
import httpx
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from tools.crop_tool import CROP_TOOL_SCHEMA, crop_tool
from tools.fertilizer_tool import FERTILIZER_TOOL_SCHEMA, fertilizer_tool
from tools.disease_tool import DISEASE_TOOL_SCHEMA, disease_tool
from tools.weather_tool import weather_tool
from utils.language import detect_language

TOOL_REGISTRY = {
    "recommend_crop":       crop_tool,
    "recommend_fertilizer": fertilizer_tool,
    "detect_disease":       disease_tool,
    "get_weather":          weather_tool,
}

ALL_TOOL_SCHEMAS = [CROP_TOOL_SCHEMA, FERTILIZER_TOOL_SCHEMA, DISEASE_TOOL_SCHEMA]

# OpenAI lazy init 
_openai_client = None

def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        try:
            from openai import OpenAI
            from config import get_settings
            s = get_settings()
            if not s.openai_api_key or s.openai_api_key.startswith("sk-your"):
                raise ValueError("No valid OPENAI_API_KEY configured.")
            _openai_client = OpenAI(api_key=s.openai_api_key)
        except Exception as e:
            logger.warning(f"OpenAI unavailable: {e}")
            _openai_client = None
    return _openai_client


#  Session memory 

class MemoryStore:
    def __init__(self, max_history: int = 10):
        self._sessions: Dict[str, List[Dict]] = {}
        self.max_history = max_history

    def get(self, session_id: str) -> List[Dict]:
        return self._sessions.get(session_id, [])

    def append(self, session_id: str, role: str, content: str):
        history = self._sessions.setdefault(session_id, [])
        history.append({"role": role, "content": content})
        if len(history) > self.max_history:
            self._sessions[session_id] = history[-self.max_history:]

    def clear(self, session_id: str):
        self._sessions.pop(session_id, None)


_memory = MemoryStore()


#  System prompts 

SYSTEM_PROMPT = """You are an expert agricultural AI assistant.

Help farmers with:
1. Crop recommendations (soil NPK, pH, temperature, humidity, rainfall)
2. Fertilizer recommendations (soil type, crop, NPK levels)
3. Plant disease diagnosis (image analysis)
4. Live weather-based crop planning (location)

Rules:
- ALWAYS call the appropriate tool when agricultural data is provided.
- Extract parameters carefully from user messages.
- Respond in friendly, farmer-appropriate language.
- Always explain WHY a recommendation was made.
- Always mention season (Kharif/Rabi/Zaid).
- If user provides location but no weather, use get_weather first.

Language: Respond in the SAME language as the user.
Detected language: {language}

Today: {today} | Month: {month}
"""

OLLAMA_SYSTEM_PROMPT = """You are Agri-World, an expert agricultural assistant.

Tools available:
- recommend_crop: Recommend crops based on NPK, pH, temperature, humidity, rainfall.
- recommend_fertilizer: Recommend fertilizer based on crop, soil type, and NPK.
- detect_disease: Detect plant diseases from leaf images.
- get_weather: Fetch live weather using city name.

Rules:
- Soil/weather data given → call recommend_crop
- Fertilizer question → call recommend_fertilizer
- Disease/image mentioned → call detect_disease
- Location given but no weather values → call get_weather first

Language: Always respond in the SAME language as the user.
Detected language: {language}

Tool-call format (STRICT JSON only):
{{"tool": "tool_name", "parameters": {{...}}}}

Example:
{{"tool": "recommend_crop", "parameters": {{"N": 90, "P": 42, "K": 43, "temperature": 28, "humidity": 82, "ph": 6.5, "rainfall": 202}}}}

If no tool needed: respond in plain text.
Always explain results simply. Always mention season (Kharif/Rabi/Zaid).

Today: {today} | Month: {month}
"""


# Intent detection (mock fallback) 
INTENT_PATTERNS = {
    "recommend_crop": [
        r"\bplant\b", r"\bcrop\b", r"\bgrow\b", r"\bsow\b", r"\bcultivate\b",
        r"\bwhat.*(plant|grow|sow)\b", r"\bwhich crop\b", r"\bbest crop\b",
    ],
    "recommend_fertilizer": [
        r"\bfertilizer\b", r"\bfertiliser\b", r"\bnpk\b", r"\bnitrogen\b",
        r"\bphosphor\b", r"\bpotassium\b", r"\bnutrient\b", r"\bdeficien\b",
        r"\burea\b", r"\bdap\b", r"\bmop\b",
    ],
    "detect_disease": [
        r"\bdisease\b", r"\bsick\b", r"\binfect\b", r"\bblight\b",
        r"\bleaf.*(spot|curl|yellow)\b", r"\bpest\b", r"\bmold\b", r"\brot\b",
    ],
}


def detect_intent(query: str) -> Optional[str]:
    q = query.lower()
    scores = {tool: sum(1 for p in patterns if re.search(p, q)) for tool, patterns in INTENT_PATTERNS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else None


# Parameter extraction 

def _extract_number(query: str, patterns: List[str], default=None):
    for p in patterns:
        m = re.search(p, query, re.IGNORECASE)
        if m:
            return float(m.group(1))
    return default

MONTH_NAMES = {
    "january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
    "july":7,"august":8,"september":9,"october":10,"november":11,"december":12,
}

def extract_crop_params(query: str) -> dict:
    q = query
    params = {
        "N":           _extract_number(q, [r"N[=:\s]+(\d+\.?\d*)", r"nitrogen[=:\s]+(\d+\.?\d*)"]),
        "P":           _extract_number(q, [r"P[=:\s]+(\d+\.?\d*)", r"phospho[a-z]*[=:\s]+(\d+\.?\d*)"]),
        "K":           _extract_number(q, [r"K[=:\s]+(\d+\.?\d*)", r"potassium[=:\s]+(\d+\.?\d*)"]),
        "temperature": _extract_number(q, [r"temp(?:erature)?[=:\s]+(\d+\.?\d*)", r"(\d+\.?\d*)\s*°?[Cc]"]),
        "humidity":    _extract_number(q, [r"humid(?:ity)?[=:\s]+(\d+\.?\d*)"]),
        "ph":          _extract_number(q, [r"p[Hh][=:\s]+(\d+\.?\d*)"]),
        "rainfall":    _extract_number(q, [r"rain(?:fall)?[=:\s]+(\d+\.?\d*)"]),
    }
    for name, num in MONTH_NAMES.items():
        if name in q.lower():
            params["month"] = num
            break
    else:
        m = re.search(r"month[=:\s]+(\d+)", q, re.IGNORECASE)
        if m:
            params["month"] = int(m.group(1))
    return {k: v for k, v in params.items() if v is not None}


def extract_fertilizer_params(query: str) -> dict:
    q = query
    params = {
        "nitrogen":    _extract_number(q, [r"N[=:\s]+(\d+\.?\d*)", r"nitrogen[=:\s]+(\d+\.?\d*)"]),
        "phosphorous": _extract_number(q, [r"P[=:\s]+(\d+\.?\d*)", r"phospho[a-z]*[=:\s]+(\d+\.?\d*)"]),
        "potassium":   _extract_number(q, [r"K[=:\s]+(\d+\.?\d*)", r"potassium[=:\s]+(\d+\.?\d*)"]),
        "temperature": _extract_number(q, [r"temp(?:erature)?[=:\s]+(\d+\.?\d*)"]),
        "humidity":    _extract_number(q, [r"humid(?:ity)?[=:\s]+(\d+\.?\d*)"]),
        "moisture":    _extract_number(q, [r"moisture[=:\s]+(\d+\.?\d*)"]),
    }
    soil_match = re.search(r"\b(black|clayey|loamy|red|sandy)\b", q, re.IGNORECASE)
    if soil_match:
        params["soil_type"] = soil_match.group(1).title()
    crop_match = re.search(
        r"\b(wheat|rice|maize|cotton|sugarcane|soybean|barley|potato|tomato|onion|mustard|groundnut|pulses|millets|ragi|jowar|bajra)\b",
        q, re.IGNORECASE,
    )
    if crop_match:
        params["crop_type"] = crop_match.group(1).title()
    return {k: v for k, v in params.items() if v is not None}


# Explanation generation 

SEASON_CROP_REASON = {
    "kharif": "Kharif season (June–October) brings monsoon rains and warm temperatures — ideal for this crop.",
    "rabi":   "Rabi season (November–March) provides cool temperatures and low humidity — perfect conditions.",
    "zaid":   "Zaid season (March–June) offers warm and dry conditions that suit this crop's growth cycle.",
}


def _build_seasonal_reason(crop: str, season: str, seasonal_score: float, weather_score: float) -> str:
    season_context = SEASON_CROP_REASON.get(season.lower(), f"the {season} season")
    score_label = "excellent" if seasonal_score >= 0.8 else ("good" if seasonal_score >= 0.5 else "moderate")
    return (
        f"{crop.title()} is a {score_label} fit for {season_context} "
        f"(seasonal fit: {seasonal_score:.0%}, weather fit: {weather_score:.0%})."
    )


def generate_explanation(tool: str, result: dict) -> str:
    if tool == "recommend_crop":
        if not result.get("success", True):
            return f"Could not determine the best crop. Error: {result.get('error', 'unknown')}"
        rankings = result.get("top_recommendations", [])
        crop_name = result.get("primary_crop") or (rankings[0].get("crop") if rankings else "unknown")
        crop = str(crop_name).strip().capitalize()
        season = result.get("season", "current")
        conf = result.get("confidence", "medium")
        top3 = ", ".join(r["crop"].capitalize() for r in rankings[:3])
        top_data = rankings[0] if rankings else {}
        seasonal_score = top_data.get("seasonal_score", 0.5)
        weather_score = top_data.get("weather_score", 0.5)
        why_now = _build_seasonal_reason(crop, season, seasonal_score, weather_score)
        if conf == "high":
            return (
                f"Based on your soil and weather conditions, **{crop}** is the best choice. "
                f"{why_now} Other good alternatives: {top3}. "
                f"Aim to sow within the optimal window to maximize yield."
            )
        return (
            f"Your conditions show mixed signals. **{crop}** scores highest overall. "
            f"{why_now} But {top3} are also viable — consult your local Krishi Vigyan Kendra."
        )

    elif tool == "recommend_fertilizer":
        if not result.get("success", True):
            return f"Fertilizer prediction failed. Error: {result.get('error', 'unknown')}"
        fert = result.get("primary_fertilizer", "unknown")
        conf = result.get("confidence", 0)
        rule = result.get("rule_applied", False)
        tops = result.get("top_recommendations", [])
        top_str = ", ".join(f"{t['fertilizer']} ({t['probability']:.0%})" for t in tops[:3])
        npk = result.get("input_summary", {})
        n, p, k = npk.get("nitrogen", "?"), npk.get("phosphorous", "?"), npk.get("potassium", "?")
        crop = npk.get("crop_type", "your crop")
        source = "agronomic rules (critical NPK deficiency)" if rule else f"ML prediction ({conf:.0%} confidence)"
        return (
            f"For **{crop}** with soil N={n}, P={p}, K={k}: "
            f"**{fert}** is recommended based on {source}. "
            f"Full ranking: {top_str}. "
            f"Apply in split doses and monitor soil response over 2–3 weeks."
        )

    elif tool == "detect_disease":
        if not result.get("success", True):
            return f"Disease detection failed. Error: {result.get('error', 'unknown')}"
        disease = result.get("primary_disease", "unknown").replace("___", " — ").replace("_", " ")
        crop = result.get("crop", "plant")
        conf = result.get("confidence", 0)
        healthy = result.get("is_healthy", False)
        severity = result.get("severity", "moderate")
        recs = result.get("treatment_recommendations", [])
        recs_str = "\n  • " + "\n  • ".join(recs) if recs else ""
        if healthy:
            return (
                f" Your **{crop}** plant looks **healthy** (confidence: {conf:.0%}). "
                f"No disease detected. Continue regular monitoring."
            )
        return (
            f"  Detected: **{disease}** on your **{crop}** plant "
            f"(confidence: {conf:.0%}, severity: **{severity}**).\n"
            f"Recommended actions:{recs_str}\n"
            f"Act quickly — early intervention reduces crop loss significantly."
        )

    return "Analysis complete. See the full result for details."


def suggest_next_action(tool: str, result: dict) -> str:
    if tool == "recommend_crop":
        return "Next: Get fertilizer recommendations for your chosen crop using POST /api/fertilizer."
    elif tool == "recommend_fertilizer":
        return "Next: Apply fertilizer and monitor soil health weekly. Upload a leaf photo to /api/disease for early disease checks."
    elif tool == "detect_disease":
        if result.get("is_healthy", False):
            return "Next: Check fertilizer requirements or get a crop recommendation for next season."
        return "Next: Apply the recommended treatment and re-upload a photo in 7–10 days to monitor recovery."
    return "Consult your local agricultural extension office for further guidance."


# Ollama client 

class OllamaClient:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model
        try:
            r = httpx.get(f"{self.base_url}/api/tags", timeout=5)
            if r.status_code != 200:
                raise ConnectionError(f"Ollama responded with {r.status_code}")
            logger.info(f" Ollama connected at {self.base_url} — model: {self.model}")
        except Exception as e:
            raise ConnectionError(f"Cannot reach Ollama at {self.base_url}: {e}")

    def chat(self, messages: list, temperature: float = 0.3) -> str:
        payload = {"model": self.model, "messages": messages, "stream": False, "options": {"temperature": temperature}}
        try:
            resp = httpx.post(f"{self.base_url}/api/chat", json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                if "message" in data and isinstance(data["message"], dict):
                    content = data["message"].get("content")
                    if content:
                        return str(content)
                for key in ("content", "response"):
                    if data.get(key):
                        return str(data[key])
            raise ValueError(f"Could not extract content from Ollama response: {data}")
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Ollama HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            raise RuntimeError(f"Ollama request failed: {e}")


_ollama_client: Optional[OllamaClient] = None

def _get_ollama_client() -> Optional[OllamaClient]:
    global _ollama_client
    if _ollama_client is None:
        try:
            from config import get_settings
            s = get_settings()
            _ollama_client = OllamaClient(base_url=s.ollama_base_url, model=s.ollama_model)
        except Exception as e:
            logger.warning(f"Ollama unavailable: {e}")
            _ollama_client = None
    return _ollama_client


#  LLM Engine 
class LLMEngine:
    def __init__(self):
        from config import get_settings
        self.settings = get_settings()

    def chat(self, query: str, session_id: Optional[str] = None, pre_parsed_params: Optional[dict] = None) -> dict:
        user_language = detect_language(query)
        provider = self.settings.llm_provider.lower()

        if provider == "openai":
            client = _get_openai_client()
            if client:
                return self._run_with_openai(query, session_id, client, user_language)

        elif provider == "ollama":
            ollama = _get_ollama_client()
            if ollama:
                return self._run_with_ollama(query, session_id, ollama, user_language)

        elif provider in ("gemini", "google"):
            return self._run_with_gemini(query, session_id, user_language)

        return self._run_mock(query, session_id, pre_parsed_params)

    #  Ollama backend 
    def _run_with_ollama(self, query: str, session_id: Optional[str], ollama: OllamaClient, user_language: str) -> dict:
        today = datetime.date.today()
        system = OLLAMA_SYSTEM_PROMPT.format(today=today, month=today.month, language=user_language)
        tool_desc = json.dumps(ALL_TOOL_SCHEMAS, indent=2)
        system_with_tools = (
            system + f"\n\nAvailable tools:\n{tool_desc}\n"
            + "\nIMPORTANT: If you need a tool, respond ONLY with JSON:\n"
            + '{"tool":"recommend_crop","parameters":{"N":90,"P":42}}\n'
            + "Otherwise respond normally."
        )
        messages = [{"role": "system", "content": system_with_tools}]
        if session_id:
            messages.extend(_memory.get(session_id))
        messages.append({"role": "user", "content": query})

        try:
            raw_response = ollama.chat(messages=messages, temperature=0.2)
        except Exception as e:
            logger.exception(f"Ollama failed: {e}")
            return self._run_mock(query, session_id, None, error_context=str(e))

        # Parse tool JSON
        tool_json = None
        stripped = raw_response.strip()
        if stripped.startswith("{"):
            tool_json = stripped
        else:
            match = re.search(r'\{.*"tool".*"parameters".*\}', raw_response, re.DOTALL)
            if match:
                tool_json = match.group(0)

        parsed = None
        if tool_json:
            try:
                parsed = json.loads(tool_json)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse tool JSON: {e}")
                return {
                    "success": False, "session_id": session_id, "intent": "unknown",
                    "tool_used": "unknown", "explanation": "Ollama returned malformed tool JSON.",
                    "next_action": "Please try again.", "result": None,
                    "llm_mode": "ollama_tool_parse_error", "error": str(e),
                }

        if parsed:
            tool_name = parsed.get("tool")
            tool_params = parsed.get("parameters", {})
            if tool_name not in TOOL_REGISTRY:
                return {
                    "success": False, "session_id": session_id, "intent": tool_name or "unknown",
                    "tool_used": tool_name or "unknown",
                    "explanation": f"Unsupported tool '{tool_name}'.",
                    "next_action": "Use a supported tool.", "result": None,
                    "llm_mode": "ollama_tool_parse_error",
                    "error": f"Unsupported tool '{tool_name}'.",
                }
            try:
                tool_result = TOOL_REGISTRY[tool_name](tool_params)
                explain_messages = messages + [
                    {"role": "assistant", "content": raw_response},
                    {"role": "user", "content": (
                        f"The tool returned:\n{json.dumps(tool_result, indent=2)}\n\n"
                        "Explain this to the farmer in simple language. Mention season if relevant. Do not return JSON."
                    )},
                ]
                explanation = ollama.chat(explain_messages, temperature=0.4)
            except Exception as e:
                logger.exception(f"Tool execution failed: {e}")
                return {
                    "success": False, "session_id": session_id, "intent": tool_name,
                    "tool_used": tool_name, "explanation": "Tool execution failed.",
                    "next_action": "Please retry.", "result": None,
                    "llm_mode": "ollama_tool_error", "error": str(e),
                }

            if session_id:
                _memory.append(session_id, "user", query)
                _memory.append(session_id, "assistant", explanation)

            return {
                "success": True, "session_id": session_id, "intent": tool_name,
                "tool_used": tool_name, "explanation": explanation,
                "next_action": suggest_next_action(tool_name, tool_result),
                "result": tool_result, "llm_mode": "ollama_tool_call",
            }

        # Plain text fallback
        if session_id:
            _memory.append(session_id, "user", query)
            _memory.append(session_id, "assistant", raw_response)

        return {
            "success": True, "session_id": session_id, "intent": "general",
            "tool_used": "none", "explanation": raw_response,
            "next_action": "Provide soil details or upload a plant image.",
            "result": None, "llm_mode": "ollama_text",
        }

    #  OpenAI backend 
    def _run_with_openai(self, query: str, session_id: Optional[str], client, user_language: str) -> dict:
        today = datetime.date.today()
        system = SYSTEM_PROMPT.format(today=today, month=today.month, language=user_language)
        messages = [{"role": "system", "content": system}]
        if session_id:
            messages.extend(_memory.get(session_id))
        messages.append({"role": "user", "content": query})
        openai_tools = [{"type": "function", "function": schema} for schema in ALL_TOOL_SCHEMAS]

        try:
            response = client.chat.completions.create(
                model=self.settings.openai_model,
                messages=messages,
                tools=openai_tools,
                tool_choice="auto",
                temperature=0.3,
            )
            msg = response.choices[0].message

            if msg.tool_calls:
                tc = msg.tool_calls[0]
                tool_name = tc.function.name
                tool_params = json.loads(tc.function.arguments)
                tool_fn = TOOL_REGISTRY.get(tool_name)
                if tool_fn is None:
                    raise ValueError(f"Unknown tool: {tool_name}")
                tool_result = tool_fn(tool_params)
                explanation = generate_explanation(tool_name, tool_result)
                next_action = suggest_next_action(tool_name, tool_result)
                if session_id:
                    _memory.append(session_id, "user", query)
                    _memory.append(session_id, "assistant", explanation)
                return {
                    "success": True, "session_id": session_id, "intent": tool_name,
                    "tool_used": tool_name, "explanation": explanation,
                    "next_action": next_action, "result": tool_result,
                    "llm_mode": "openai_tool_call",
                }

            text = msg.content or "I could not determine the correct action."
            if session_id:
                _memory.append(session_id, "user", query)
                _memory.append(session_id, "assistant", text)
            return {
                "success": True, "session_id": session_id, "intent": "general",
                "tool_used": "none", "explanation": text,
                "next_action": "Ask about crops, fertilizer, or upload a plant image.",
                "result": None, "llm_mode": "openai_text",
            }

        except Exception as e:
            logger.exception("OpenAI failed, switching to mock")
            return self._run_mock(query, session_id, None, error_context=str(e))

    # Gemini backend 
    def _run_with_gemini(self, query: str, session_id: Optional[str], user_language: str) -> dict:
        """
        Gemini backend using google-generativeai SDK.
        Uses prompt-based JSON tool calling (same pattern as Ollama).
        Supports: gemini-2.0-flash, gemini-1.5-flash, gemini-1.5-pro
        """
        try:
            import google.generativeai as genai
        except ImportError:
            logger.error("google-generativeai not installed. Run: pip install google-generativeai")
            return self._run_mock(query, session_id, None, error_context="google-generativeai not installed")

        api_key = self.settings.gemini_api_key
        if not api_key:
            logger.error("GEMINI_API_KEY not set in .env")
            return self._run_mock(query, session_id, None, error_context="GEMINI_API_KEY not configured")

        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(self.settings.gemini_model)
        except Exception as e:
            logger.error(f"Gemini init failed: {e}")
            return self._run_mock(query, session_id, None, error_context=str(e))

        today = datetime.date.today()
        tool_desc = json.dumps(ALL_TOOL_SCHEMAS, indent=2)

        system_prompt = f"""You are KrishiAI, an expert agricultural assistant.

You have access to these tools:
{tool_desc}

Rules:
- If user gives soil/weather data (NPK, pH, temperature, humidity, rainfall) → call recommend_crop
- If user asks about fertilizer → call recommend_fertilizer
- If user mentions plant disease or leaf problem → call detect_disease
- If user gives a city/location but no weather values → call get_weather first

Language: Always respond in the SAME language as the user.
Detected language: {user_language}

IMPORTANT — Tool call format (strict JSON, nothing else):
{{"tool": "tool_name", "parameters": {{...}}}}

Examples:
{{"tool": "recommend_crop", "parameters": {{"N": 90, "P": 42, "K": 43, "temperature": 28, "humidity": 82, "ph": 6.5, "rainfall": 202}}}}
{{"tool": "recommend_fertilizer", "parameters": {{"temperature": 28, "humidity": 65, "moisture": 40, "nitrogen": 37, "phosphorous": 0, "potassium": 0, "soil_type": "Sandy", "crop_type": "Maize"}}}}
{{"tool": "get_weather", "parameters": {{"city": "Hyderabad"}}}}

If no tool is needed, respond in plain conversational text.
Always explain results simply for farmers. Always mention season (Kharif/Rabi/Zaid).

Today: {today} | Month: {today.month}
"""

        # Build conversation history for Gemini
        history = []
        if session_id:
            for msg in _memory.get(session_id):
                role = "user" if msg["role"] == "user" else "model"
                history.append({"role": role, "parts": [msg["content"]]})

        try:
            chat_session = model.start_chat(history=history)
            full_prompt = f"{system_prompt}\n\nUser: {query}"
            response = chat_session.send_message(full_prompt)
            raw_response = response.text
            logger.debug(f"Gemini raw response (first 300): {raw_response[:300]}")
        except Exception as e:
            logger.exception(f"Gemini API call failed: {e}")
            return self._run_mock(query, session_id, None, error_context=str(e))

    
        tool_json = None
        stripped = raw_response.strip()
 
        if stripped.startswith("```"):
            stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
            stripped = re.sub(r"\s*```$", "", stripped.strip())

        if stripped.startswith("{"):
            tool_json = stripped
        else:
            match = re.search(r'\{[^{}]*"tool"[^{}]*"parameters"[^{}]*\}', raw_response, re.DOTALL)
            if not match:
                match = re.search(r'\{.*?"tool".*?"parameters".*?\}', raw_response, re.DOTALL)
            if match:
                tool_json = match.group(0)

        parsed = None
        if tool_json:
            try:
                parsed = json.loads(tool_json)
            except json.JSONDecodeError as e:
                logger.warning(f"Gemini tool JSON parse failed: {e} — treating as plain text")

        # Execute tool if parsed successfully
        if parsed and parsed.get("tool") in TOOL_REGISTRY:
            tool_name = parsed["tool"]
            tool_params = parsed.get("parameters", {})

            try:
                tool_result = TOOL_REGISTRY[tool_name](tool_params)

               
                explain_prompt = (
                    f"The tool '{tool_name}' returned this result:\n"
                    f"{json.dumps(tool_result, indent=2)}\n\n"
                    f"Explain this to a farmer in simple, friendly language. "
                    f"Mention the season (Kharif/Rabi/Zaid) if relevant. "
                    f"Respond in {user_language} language. Do NOT return JSON."
                )
                try:
                    explain_resp = chat_session.send_message(explain_prompt)
                    explanation = explain_resp.text
                except Exception:
                    explanation = generate_explanation(tool_name, tool_result)

                next_action = suggest_next_action(tool_name, tool_result)

                if session_id:
                    _memory.append(session_id, "user", query)
                    _memory.append(session_id, "assistant", explanation)

                return {
                    "success": True,
                    "session_id": session_id,
                    "intent": tool_name,
                    "tool_used": tool_name,
                    "explanation": explanation,
                    "next_action": next_action,
                    "result": tool_result,
                    "llm_mode": "gemini_tool_call",
                }

            except Exception as e:
                logger.exception(f"Gemini tool execution failed: {e}")
                return self._run_mock(query, session_id, None, error_context=str(e))

        # Plain text response 
        if session_id:
            _memory.append(session_id, "user", query)
            _memory.append(session_id, "assistant", raw_response)

        return {
            "success": True,
            "session_id": session_id,
            "intent": "general",
            "tool_used": "none",
            "explanation": raw_response,
            "next_action": "Provide soil details (NPK, pH, temperature, humidity, rainfall) for crop recommendations.",
            "result": None,
            "llm_mode": "gemini_text",
        }

    # Mock / rule-based fallback 
    def _run_mock(self, query: str, session_id: Optional[str], pre_parsed_params: Optional[dict] = None, error_context: str = None) -> dict:
        intent = detect_intent(query)

        if intent is None:
            reply = (
                "Hello! I'm your agriculture AI assistant. I can help with:\n"
                "  • **Crop recommendations** — tell me your soil NPK, pH, temp, humidity, rainfall\n"
                "  • **Fertilizer advice** — tell me your soil type, crop, and NPK levels\n"
                "  • **Disease detection** — upload a plant leaf image to /api/disease\n"
                "What would you like help with?"
            )
            if session_id:
                _memory.append(session_id, "user", query)
                _memory.append(session_id, "assistant", reply)
            return {
                "success": True, "session_id": session_id, "intent": "general",
                "tool_used": "none", "explanation": reply,
                "next_action": "Provide soil details or upload an image.",
                "result": None, "llm_mode": "mock_no_intent",
            }

        if pre_parsed_params:
            params = pre_parsed_params
        elif intent == "recommend_crop":
            params = extract_crop_params(query)
        elif intent == "recommend_fertilizer":
            params = extract_fertilizer_params(query)
        elif intent == "detect_disease":
            return {
                "success": False, "session_id": session_id, "intent": "detect_disease",
                "tool_used": "detect_disease",
                "explanation": "Please upload a plant image for disease detection via POST /api/disease.",
                "next_action": "Upload a leaf image.", "result": None, "llm_mode": "mock_rule_based",
            }
        else:
            params = {}

        tool_fn = TOOL_REGISTRY.get(intent)
        tool_result = tool_fn(params) if tool_fn else {}
        explanation = generate_explanation(intent, tool_result)
        next_action = suggest_next_action(intent, tool_result)

        if session_id:
            _memory.append(session_id, "user", query)
            _memory.append(session_id, "assistant", explanation)

        mode = "mock_fallback" if error_context else "mock_rule_based"
        result = {
            "success": True, "session_id": session_id, "intent": intent,
            "tool_used": intent, "explanation": explanation,
            "next_action": next_action, "result": tool_result, "llm_mode": mode,
        }
        if error_context:
            result["llm_error"] = error_context
            result["note"] = f"LLM ({self.settings.llm_provider}) unavailable. Using rule-based fallback."
        return result

    def clear_session(self, session_id: str):
        _memory.clear(session_id)

    def get_session_history(self, session_id: str) -> List[Dict]:
        return _memory.get(session_id)


# Singleton 
_engine_instance: Optional[LLMEngine] = None

def get_engine() -> LLMEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = LLMEngine()
    return _engine_instance
