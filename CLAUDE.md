# LaunchDarkly Support Chatbot — Project Context

## What This Is

A prototype LaunchDarkly support chatbot with a 5-step traced agent chain. Each step is an LLM call managed by a LaunchDarkly AI Config, with full observability via the LD Observability SDK.

## Architecture

```
User message → FastAPI backend → 5-step chain → Response + quality metadata
                                    │
                                    ├─ Classify Intent (gpt-4o-mini)
                                    ├─ Rewrite Search Query (gpt-4o-mini)
                                    ├─ Search LD Docs (gpt-4o + web_search)
                                    ├─ Generate Response (gpt-4o)
                                    └─ Judge Quality (gpt-4o-mini)
```

Frontend is React + Vite + TypeScript. Backend is Python/FastAPI.

## Key Files

- `backend/app/config.py` — LD SDK + ObservabilityPlugin + OpenAI client init
- `backend/app/chain/orchestrator.py` — Runs the chain with SSE streaming + OTel parent span
- `backend/app/chain/{intent,rewriter,retrieval,generator,judge}.py` — Individual chain steps
- `backend/app/main.py` — FastAPI with `/chat` (sync) and `/chat/stream` (SSE) endpoints
- `frontend/src/components/ChatWindow.tsx` — Main chat UI consuming SSE stream
- `frontend/src/components/ChainProgress.tsx` — Live chain step progress display
- `frontend/src/api/chat.ts` — SSE client parsing step/result events

## LaunchDarkly AI Configs

Created via API in the `default` project:

| Key | Purpose |
|-----|---------|
| `ld-bot-intent-classifier` | Classify intent + extract entities |
| `ld-bot-query-rewriter` | Rewrite user query for doc search |
| `ld-bot-response-generator` | Generate final response (uses `{{intent}}`, `{{docs}}`, `{{entities}}` Mustache vars) |
| `ld-bot-quality-judge` | Score relevance + faithfulness |

Each chain step has a hardcoded `AICompletionConfigDefault` fallback in case the AI Config isn't available.

## LD SDK Integration Pattern

```python
from ldai import LDAIClient, AICompletionConfigDefault, LDMessage, ModelConfig, ProviderConfig
from ldobserve import ObservabilityConfig, ObservabilityPlugin

# Init: SDK key goes into Config with ObservabilityPlugin
ldclient.set_config(Config(sdk_key, plugins=[ObservabilityPlugin(ObservabilityConfig(...))]))
ld_client = ldclient.get()
ai_client = LDAIClient(ld_client)

# Per-call: get config variation, then track the OpenAI call
config = ai_client.completion_config("config-key", context, default_config, variables={...})
result = config.tracker.track_openai_metrics(lambda: openai_client.chat.completions.create(...))
```

`track_openai_metrics` is synchronous — wraps a sync callable, records duration + tokens + success/error.

## Troubleshooting Log

### Traces not appearing in LD dashboard
- Initial worry: `trace_sampled=False` in Python logs. This is just the logging format from LoggingInstrumentor — it doesn't mean spans are dropped.
- Confirmed `TracerProvider` is the real SDK one (not no-op) by inspecting `trace.get_tracer_provider()`.
- Traces were actually exporting fine — just needed to click "Run query" in the Traces UI.

### Traces not linked together (separate traces per LLM call)
- **First time:** No parent span wrapping the chain steps. Fixed by adding `_tracer.start_as_current_span("Support Chat Request")` around all steps.
- **Second time (after SSE refactor):** Each step ran in a separate thread via `asyncio.to_thread`, so OTel context didn't propagate. Fixed by:
  1. Creating the parent span manually with `_tracer.start_span()`
  2. Capturing its context: `parent_ctx = trace.set_span_in_context(parent_span)`
  3. Re-attaching in each worker thread: `otel_context.attach(parent_ctx)` before creating child spans
  4. Manually ending: `parent_span.end()` in a `finally` block

### Doc retrieval not finding LD docs
- `gpt-4o-mini` with `web_search_preview` tool couldn't find LD docs — returned "no relevant results" even for pages that exist.
- Even `gpt-4o` failed when the prompt said "search docs.launchdarkly.com" — the model interpreted it too literally.
- **Fix:** Use `gpt-4o` with `site:launchdarkly.com {query}` as the input and `search_context_size: "high"`. This works reliably.

### OpenAI quota errors (429)
- Updating the API key in `.env` requires restarting the server — `--reload` watches file changes but the OpenAI client is created at import time in `config.py`.

## Running

```bash
# Backend
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload

# Frontend
cd frontend && npm run dev
```

Backend: http://localhost:8000, Frontend: http://localhost:5173

## Environment Variables (backend/.env)

```
LAUNCHDARKLY_SDK_KEY=...
LAUNCHDARKLY_API_KEY=...      # REST API token for managing AI Configs
LAUNCHDARKLY_PROJECT_KEY=default
OPENAI_API_KEY=...
```

## GitHub

Repo: https://github.com/ewangLD/ai-experiments-prototype (public, under ewangLD work account)
