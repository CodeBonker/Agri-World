"""
routes/chat.py
LLM-powered natural language chat endpoint.
Rate limited to 20 requests/minute per IP for now
"""

import logging
import asyncio
from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from schemas.requests import ChatRequest
from llm.llm_engine import get_engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["LLM Chat"])
limiter = Limiter(key_func=get_remote_address)


@router.post(
    "/chat",
    summary="Natural language agricultural assistant (LLM-powered)",
    response_description="Human-readable explanation with tool result",
)
@limiter.limit("20/minute")
async def chat(request: Request, req: ChatRequest):
    """
    Input: Natural language query

    Backends:
    - ollama: Uses local Llama model via Ollama for tool calling
    - openai/Gemini: Uses GPT function-calling
    - mock:   Rule-based extraction (offline, no LLM needed)
    """
    try:
        logger.info(f"Chat: query={req.query[:80]}... session={req.session_id}")
        engine = get_engine()

        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: engine.chat(
                query=req.query,
                session_id=req.session_id,
                pre_parsed_params=req.parameters,
            ),
        )

        if response is None:
            raise HTTPException(status_code=500, detail="Chat engine returned no response")

        if not response.get("success", True):
            detail = response.get("error") or response.get("explanation") or "Chat processing failed"
            llm_mode = response.get("llm_mode", "")
            status_code = 400 if llm_mode.startswith("ollama_tool") else 500
            raise HTTPException(status_code=status_code, detail=detail)

        logger.info(f"Chat success: tool={response.get('tool_used')}, mode={response.get('llm_mode')}")
        return response

    except HTTPException:
        raise
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Request cancelled")
    except Exception as e:
        logger.exception(f"Unexpected error in chat: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@router.delete(
    "/chat/session/{session_id}",
    summary="Clear chat memory for a session",
)
def clear_session(session_id: str):
    engine = get_engine()
    engine.clear_session(session_id)
    return {"success": True, "message": f"Session '{session_id}' cleared."}


@router.get(
    "/chat/session/{session_id}",
    summary="Retrieve chat history for a session",
)
def get_session(session_id: str):
    engine = get_engine()
    history = engine.get_session_history(session_id)
    return {"session_id": session_id, "message_count": len(history), "history": history}
