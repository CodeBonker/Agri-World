# AGENTS.md

## Project Summary
This repository is a FastAPI backend for agriculture decision support with:
- Crop recommendation (`/api/crop`)
- Fertilizer recommendation (`/api/fertilizer`)
- Plant disease detection (`/api/disease`, `/api/disease/base64`)
- LLM chat orchestration (`/api/chat`)

Core stack: FastAPI, scikit-learn, PyTorch, SlowAPI, OpenWeatherMap, optional LLM providers (Gemini/OpenAI/Ollama/mock fallback).

## Repository Map
- `main.py`: app entrypoint, middleware, startup model loading, health endpoints.
- `config.py`: environment-backed settings.
- `routes/`: HTTP endpoints.
- `schemas/`: request/response models.
- `tools/`: tool wrappers used by routes and LLM engine.
- `core/`: ML/DL logic (crop/fertilizer/disease).
- `llm/`: routing engine + tool orchestration + session memory.
- `services/weather_service.py`: OpenWeatherMap integration.
- `scripts/`: model training/downloading scripts.
- `models/`: runtime artifacts (`*.pkl`, `*.pth`).
- `data/`: training datasets.

## Local Runbook
1. Create venv and install deps:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```
2. Create `.env` from `env.example` and set keys.
3. Ensure model files exist:
```bash
python scripts/train_models.py
python scripts/download_disease_model.py
```
4. Run server:
```bash
python main.py
```
5. Validate service:
- Swagger: `http://localhost:8000/docs`
- Health: `GET /health`

## Required Runtime Inputs
- Crop: `N`, `P`, `K`, `ph`, plus either explicit weather (`temperature`, `humidity`, `rainfall`) or `location` for live weather fetch.
- Fertilizer: weather/moisture + NPK + `soil_type` + `crop_type`.
- Disease: image file upload or base64 image.
- Chat: natural language query, optional `session_id`.

## Operational Notes
- Startup eagerly loads crop/fertilizer/disease models; missing model files cause endpoint failures but app still starts.
- Crop endpoint can auto-fill weather from OpenWeatherMap when `location` is provided.
- Chat memory is in-process only (`MemoryStore`), not persistent/shared across workers.
- Rate limits: default 200/min globally and 20/min on `/api/chat`.

## Known Codebase Gotchas
- `llm/llm_engine.py` defines `get_weather` in registry, but `ALL_TOOL_SCHEMAS` excludes weather schema, so OpenAI function-calling does not expose weather as a tool.
- `scripts/train_disease_model.py` trains/saves a ResNet18 state dict, while `core/disease_detector.py` loads MobileNetV2 architecture. These artifacts are not directly compatible.
- `scripts/download_disease_model.py` uses Linux-style `local_dir="/tmp/hf_disease"` (works on Linux; may be awkward on Windows environments).
- Optional dependencies appear to be used but are not listed in `requirements.txt`:
  - `google-generativeai` (Gemini backend)
  - `huggingface_hub` (model download script)

## Safe Change Guidance For Agents
- Keep route contracts stable; frontend integration depends on current response keys (`success`, `tool`, `explanation`, `next_action`, `raw`/`result`).
- When modifying schemas, update route usage and docs together.
- For LLM behavior changes, verify fallback path (`mock`) still works with missing keys/services.
- For model-path changes, keep defaults aligned across `config.py`, `tools/*`, and training scripts.
- Avoid introducing blocking work in async routes; use thread executor pattern as already implemented.

## Suggested Validation After Changes
```bash
python -m compileall .
python main.py
```
Then manually verify:
- `GET /health`
- `POST /api/crop`
- `POST /api/fertilizer`
- `POST /api/chat`

## If You Need To Extend
- Add new ML capability in `core/`.
- Wrap it in `tools/` with a tool schema.
- Register in `llm/tool_registry.py` (and `llm/llm_engine.py` tool maps/schemas).
- Expose via new route in `routes/` and matching request/response schema.
