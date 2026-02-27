# LaunchDarkly Support Chatbot

A prototype support chatbot with a multi-step agent chain, where each step is traced via LaunchDarkly's LLM observability. Prompts and model settings are managed via LaunchDarkly AI Configs.

## Architecture

```
User message
  │
  ├─ [Span 1] Intent Classification    (AI Config: ld-bot-intent-classifier)
  ├─ [Span 2] Query Rewriting          (AI Config: ld-bot-query-rewriter)
  ├─ [Span 3] Doc Retrieval            (OpenAI web_search)
  ├─ [Span 4] Response Generation      (AI Config: ld-bot-response-generator)
  └─ [Span 5] Quality Check            (AI Config: ld-bot-quality-judge)
```

## Prerequisites

- Python 3.10+
- Node.js 18+
- OpenAI API key
- LaunchDarkly SDK key (with AI Configs enabled)

## Setup

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env`:

```
LAUNCHDARKLY_SDK_KEY=your-ld-sdk-key
OPENAI_API_KEY=your-openai-api-key
```

### 2. LaunchDarkly AI Configs

Create these 4 AI Configs in your LaunchDarkly project:

| Key | Purpose | Suggested Model |
|-----|---------|----------------|
| `ld-bot-intent-classifier` | Classify user intent | gpt-4o-mini |
| `ld-bot-query-rewriter` | Rewrite queries for search | gpt-4o-mini |
| `ld-bot-response-generator` | Generate the final response | gpt-4o |
| `ld-bot-quality-judge` | Score response quality | gpt-4o-mini |

Each config should include a system message with instructions for that step. The code includes sensible defaults that are used as fallbacks.

### 3. Frontend

```bash
cd frontend
npm install
```

## Running

Start both services:

```bash
# Terminal 1 — backend
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload

# Terminal 2 — frontend
cd frontend
npm run dev
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Health check: http://localhost:8000/health

## Verification

1. Open http://localhost:5173
2. Send: "How do I set up feature flags in Python?"
3. Check that the response includes intent classification, sources, and a quality score
4. Check the LaunchDarkly Monitor dashboard for traces with all 5 spans
5. Test multi-turn: follow up with "What about in JavaScript?" to verify context carries over
