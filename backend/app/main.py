from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.config import ld_client
from app.models import ChatRequest, ChatResponse, FeedbackRequest
from app.chain.orchestrator import run_chain, run_chain_stream, submit_feedback


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    ld_client.close()


app = FastAPI(title="LD Support Chatbot", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    return await run_chain(req)


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    return StreamingResponse(
        run_chain_stream(req),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/feedback")
async def feedback(req: FeedbackRequest):
    tracked = submit_feedback(req.response_id, req.kind)
    return {"tracked": tracked}


@app.get("/health")
async def health():
    return {"status": "ok", "ld_initialized": ld_client.is_initialized()}
