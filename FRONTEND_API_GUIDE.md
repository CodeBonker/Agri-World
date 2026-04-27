# CropSeek LLM — Frontend Developer Guide

## Overview

This is the backend API for an AI-powered agriculture assistant.
Your job is to build a frontend (React / HTML / Vue / anything) that talks to these APIs.

The backend is already running.

---

## Base URL

```
http://localhost:8000
```

> When deployed to production, this will change to a public URL. For now run locally.

---

## How to Run the Backend Locally (one time setup)

```bash
# 1. Clone the repo
git clone <repo-url>
cd cropseek-llm

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Start the server
python main.py
```

Server runs at: http://localhost:8000
Interactive API docs: http://localhost:8000/docs

---

## CORS

All origins are allowed. No CORS issues from any frontend.

---

## API Endpoints

---

### 1. Crop Recommendation

**POST** `/api/crop`

Recommends the best crop to grow based on soil and weather conditions.

**Request Body:**
```json
{
  "N": 90,
  "P": 42,
  "K": 43,
  "temperature": 28,
  "humidity": 82,
  "ph": 6.5,
  "rainfall": 202,
  "month": 7,
  "top_n": 5,
  "location": "Hyderabad"
}
```

**Field Reference:**

| Field | Type | Required | Description |
|---|---|---|---|
| N | number |  | Nitrogen level (0–300 kg/ha) |
| P | number |  | Phosphorus level (0–300 kg/ha) |
| K | number | | Potassium level (0–300 kg/ha) |
| ph | number |  | Soil pH (0–14) |
| temperature | number |  | Temperature °C (auto-filled if location given) |
| humidity | number |  | Humidity % (auto-filled if location given) |
| rainfall | number |  | Rainfall mm (auto-filled if location given) |
| month | integer |  | Month 1–12 (defaults to current month) |
| top_n | integer |  | How many crops to return (1–10, default 5) |
| location | string |  | City name — auto-fetches live weather |

> If you provide `location`, you don't need temperature/humidity/rainfall.

**Success Response (200):**
```json
{
  "success": true,
  "tool": "crop_recommendation",
  "explanation": "Based on your soil and weather conditions, **Rice** is the best choice...",
  "next_action": "Next: Get fertilizer recommendations for your chosen crop.",
  "primary_crop": "rice",
  "season": "kharif",
  "confidence": "high",
  "seasonal_score": 1.0,
  "weather_score": 1.0,
  "why_this_crop_now": "Rice is an excellent fit for Kharif season...",
  "uncertainty_score": 0.6076,
  "top_recommendations": [
    {
      "crop": "rice",
      "composite_score": 0.9443,
      "ml_probability": 0.8987,
      "seasonal_score": 1.0,
      "weather_score": 1.0
    },
    {
      "crop": "jute",
      "composite_score": 0.4651,
      "ml_probability": 0.0275,
      "seasonal_score": 1.0,
      "weather_score": 1.0
    }
  ]
}
```

**Error Response (422):**
```json
{
  "success": false,
  "error": "Validation failed",
  "detail": ["K: Field required", "ph: Field required"]
}
```

---

### 2. Fertilizer Recommendation

**POST** `/api/fertilizer`

Recommends the best fertilizer based on soil nutrients and crop type.

**Request Body:**
```json
{
  "temperature": 28,
  "humidity": 65,
  "moisture": 40,
  "nitrogen": 37,
  "phosphorous": 0,
  "potassium": 0,
  "soil_type": "Sandy",
  "crop_type": "Maize"
}
```

**Field Reference:**

| Field | Type | Required | Description |
|---|---|---|---|
| temperature | number |   | Temperature °C |
| humidity | number |   | Humidity % |
| moisture | number |   | Soil moisture % |
| nitrogen | number |   | Nitrogen level |
| phosphorous | number |   | Phosphorus level |
| potassium | number |   | Potassium level |
| soil_type | string |   | One of: Sandy, Loamy, Black, Red, Clayey |
| crop_type | string |   | e.g. Wheat, Rice, Maize, Cotton, Sugarcane |

**Success Response (200):**
```json
{
  "success": true,
  "tool": "fertilizer_recommendation",
  "explanation": "For **Maize** with soil N=37, P=0, K=0: **DAP** is recommended...",
  "next_action": "Apply fertilizer and monitor soil health weekly.",
  "primary_fertilizer": "DAP",
  "confidence": 0.9267,
  "rule_applied": true,
  "rule_reason": "Critical phosphorus deficiency detected",
  "top_recommendations": [
    { "fertilizer": "Urea", "probability": 0.9267 },
    { "fertilizer": "28-28", "probability": 0.04 },
    { "fertilizer": "20-20", "probability": 0.02 }
  ],
  "input_summary": {
    "nitrogen": 37.0,
    "phosphorous": 0.0,
    "potassium": 0.0,
    "soil_type": "Sandy",
    "crop_type": "Maize"
  }
}
```

---

### 3. Disease Detection

**POST** `/api/disease`

Detects plant disease from a leaf photo.

**Request:** Multipart form upload

```
Content-Type: multipart/form-data
Field name: file
Accepted formats: JPG, JPEG, PNG, BMP, WEBP
Max size: 10 MB
```

**JavaScript fetch example:**
```javascript
const formData = new FormData();
formData.append('file', imageFile); // imageFile from <input type="file">

const response = await fetch('http://localhost:8000/api/disease', {
  method: 'POST',
  body: formData
});
const data = await response.json();
```

**Success Response (200):**
```json
{
  "success": true,
  "tool": "disease_detection",
  "explanation": "  Detected: **Tomato Late Blight** on your **Tomato** plant (confidence: 87%, severity: high).",
  "next_action": "Apply the recommended treatment and re-upload in 7–10 days.",
  "primary_disease": "Tomato - Late blight",
  "crop": "Tomato",
  "confidence": 0.87,
  "is_healthy": false,
  "severity": "high",
  "treatment_recommendations": [
    "Apply fungicides containing metalaxyl immediately.",
    "Remove and destroy infected plants.",
    "Avoid overhead watering."
  ],
  "top_3": [
    { "disease": "Tomato - Late blight", "confidence": 0.87 },
    { "disease": "Tomato - Early blight", "confidence": 0.08 },
    { "disease": "Tomato - healthy", "confidence": 0.03 }
  ]
}
```

**Healthy plant response:**
```json
{
  "success": true,
  "is_healthy": true,
  "primary_disease": "Tomato - healthy",
  "explanation": "  Your **Tomato** plant looks **healthy** (confidence: 94%).",
  "treatment_recommendations": [
    "Plant looks healthy! Continue regular monitoring.",
    "Maintain proper irrigation and fertilization.",
    "Scout for pests and diseases weekly."
  ]
}
```

**Also available — base64 upload (for mobile apps):**

**POST** `/api/disease/base64`
```json
{
  "image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRgAB..."
}
```

---

### 4. AI Chat Assistant

**POST** `/api/chat`

Natural language interface. Send any farming question, get an intelligent response powered by Gemini AI.

**Request Body:**
```json
{
  "query": "My soil has N=90 P=42 K=43 ph=6.5. What crop should I grow?",
  "session_id": "user-123"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| query | string |   | The user's message (max 2000 chars) |
| session_id | string |  | Unique ID per user for conversation memory |

> Use a consistent `session_id` per user so the AI remembers previous messages in the conversation.

**Success Response (200):**
```json
{
  "success": true,
  "session_id": "user-123",
  "intent": "recommend_crop",
  "tool_used": "recommend_crop",
  "explanation": "Based on your soil conditions, **Rice** is the best crop for you right now! Your soil has good NPK levels and the current Kharif season with monsoon rains makes it ideal...",
  "next_action": "Next: Get fertilizer recommendations for rice.",
  "result": { ... },
  "llm_mode": "gemini_tool_call"
}
```

**Rate limit:** 20 requests per minute per IP.

**Session management:**
```
GET    /api/chat/session/{session_id}   → get conversation history
DELETE /api/chat/session/{session_id}   → clear conversation history
```

---

### 5. Health Check

**GET** `/health`

```json
{
  "status": "healthy",
  "models": {
    "crop": "loaded",
    "fertilizer": "loaded",
    "disease": "loaded"
  },
  "llm": {
    "provider": "gemini",
    "model": "gemini-2.5-flash"
  }
}
```

---

## Supported Crops (for reference)

Rice, Wheat, Maize, Cotton, Sugarcane, Chickpea, Kidney Beans, Pigeon Peas,
Mung Bean, Black Gram, Lentil, Pomegranate, Banana, Mango, Grapes,
Watermelon, Muskmelon, Apple, Orange, Papaya, Coconut, Coffee, Jute

## Supported Soil Types

Sandy, Loamy, Black, Red, Clayey

## Supported Disease Classes (38 total)

Apple (scab, black rot, rust, healthy),
Corn (cercospora, rust, blight, healthy),
Grape (black rot, esca, leaf blight, healthy),
Tomato (bacterial spot, early blight, late blight, leaf mold, septoria, spider mites, target spot, yellow leaf curl, mosaic virus, healthy),
Potato (early blight, late blight, healthy),
Strawberry (leaf scorch, healthy),
Peach, Pepper, Soybean, Squash, Raspberry, Blueberry, Cherry, Orange

---

## Suggested UI Pages

| Page | API used |
|---|---|
|  Crop Advisor | POST /api/crop |
|  Fertilizer Advisor | POST /api/fertilizer |
|  Disease Detector | POST /api/disease |
|  AI Chat | POST /api/chat |
|  Dashboard | GET /health |

---

## Example UI Flow

**Crop Advisor page:**
1. Form with fields: N, P, K, pH, Temperature, Humidity, Rainfall, Month (or just a City field)
2. Submit → POST /api/crop
3. Show: primary crop name, season badge, confidence badge, top 5 ranked crops as cards
4. Show the `explanation` text as a friendly summary
5. Show `why_this_crop_now` as a highlighted callout

**Disease Detector page:**
1. Image upload area (drag & drop or click)
2. Preview the image
3. Submit → POST /api/disease (multipart)
4. Show: disease name, confidence bar, severity badge (green/yellow/red)
5. Show treatment recommendations as a checklist
6. If healthy → show green success state

**Chat page:**
1. Chat bubble UI (like WhatsApp)
2. Generate a random `session_id` on page load (e.g. uuid)
3. Send user message → POST /api/chat with session_id
4. Show `explanation` as the AI response bubble
5. Support follow-up questions (session memory is handled by backend)

---

## Notes for the Frontend Developer

- The `explanation` field in every response is already formatted in Markdown (`**bold**`, bullet points). You can render it with a markdown library or just display as plain text.
- The `is_healthy` boolean on disease response lets you show green vs red UI states easily.
- The `confidence` field is a float 0–1. Multiply by 100 for percentage display.
- The `season` field will be one of: `kharif`, `rabi`, `zaid` — you can show these as colored badges.
- The `rule_applied` boolean on fertilizer tells you whether it was an AI/ML decision or a hard agronomic rule — useful to show different UI treatment.
- All error responses have `"success": false` and a `"detail"` field explaining what went wrong.
