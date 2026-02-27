from __future__ import annotations

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    conversation_history: list[ChatMessage] = Field(default_factory=list)


class QualityMetadata(BaseModel):
    relevance: float = 0.0
    faithfulness: float = 0.0
    passed: bool = True


class ChatResponse(BaseModel):
    reply: str
    response_id: str = ""
    intent: str = ""
    entities: list[str] = Field(default_factory=list)
    quality: QualityMetadata = Field(default_factory=QualityMetadata)
    sources: list[dict] = Field(default_factory=list)


class FeedbackRequest(BaseModel):
    response_id: str
    kind: str  # "positive" or "negative"
