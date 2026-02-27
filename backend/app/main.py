from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import ld_client
from app.models import ChatRequest, ChatResponse
from app.chain.orchestrator import run_chain


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


@app.get("/health")
async def health():
    return {"status": "ok", "ld_initialized": ld_client.is_initialized()}
