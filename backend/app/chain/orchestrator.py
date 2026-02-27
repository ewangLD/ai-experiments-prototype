"""Orchestrates the full agent chain."""

from __future__ import annotations

import asyncio
from collections import defaultdict

from ldclient.context import Context
from opentelemetry import trace

from app.models import ChatRequest, ChatResponse, QualityMetadata
from app.chain.intent import classify_intent
from app.chain.rewriter import rewrite_query
from app.chain.retrieval import retrieve_docs
from app.chain.generator import generate_response
from app.chain.judge import judge_quality

# In-memory conversation store keyed by session_id
_sessions: dict[str, list[dict]] = defaultdict(list)

_tracer = trace.get_tracer("ld-support-chatbot.chain")


async def run_chain(req: ChatRequest) -> ChatResponse:
    """Execute the full chain: intent → rewrite → retrieve → generate → judge."""
    context = Context.create(req.session_id)

    # Merge incoming history with server-side history
    history = _sessions[req.session_id]
    if req.conversation_history:
        history = [{"role": m.role, "content": m.content} for m in req.conversation_history]

    # All chain steps use synchronous OpenAI calls (tracked by LD),
    # so we run them in a thread to avoid blocking the event loop.

    def _run_sync():
        with _tracer.start_as_current_span(
            "ld-support-chatbot.agent-chain",
            attributes={
                "user.message": req.message,
                "session.id": req.session_id,
            },
        ) as parent_span:
            # Step 1: Intent classification
            with _tracer.start_as_current_span("chain.intent-classification"):
                intent_result = classify_intent(req.message, context)
                intent = intent_result.get("intent", "general")
                entities = intent_result.get("entities", [])

            # Step 2: Query rewriting
            with _tracer.start_as_current_span("chain.query-rewriting"):
                search_query = rewrite_query(req.message, intent, entities, history, context)

            # Step 3: Document retrieval
            with _tracer.start_as_current_span("chain.doc-retrieval") as retrieval_span:
                documents = retrieve_docs(search_query)
                retrieval_span.set_attribute("retrieval.query", search_query)
                retrieval_span.set_attribute("retrieval.result_count", len(documents))

            # Step 4: Response generation
            with _tracer.start_as_current_span("chain.response-generation"):
                reply = generate_response(
                    req.message, intent, entities, documents, history, context
                )

            # Step 5: Quality check
            with _tracer.start_as_current_span("chain.quality-judge"):
                quality = judge_quality(req.message, reply, documents, context)

            parent_span.set_attribute("chain.intent", intent)
            parent_span.set_attribute("chain.entities", entities)
            parent_span.set_attribute("chain.quality.relevance", quality.get("relevance", 0.0))
            parent_span.set_attribute("chain.quality.faithfulness", quality.get("faithfulness", 0.0))
            parent_span.set_attribute("chain.quality.passed", quality.get("pass", False))

            return intent, entities, documents, reply, quality

    intent, entities, documents, reply, quality = await asyncio.to_thread(_run_sync)

    # Update conversation history
    _sessions[req.session_id].append({"role": "user", "content": req.message})
    _sessions[req.session_id].append({"role": "assistant", "content": reply})

    sources = [
        {"title": d.get("title", ""), "url": d.get("url", "")}
        for d in documents
        if d.get("url")
    ]

    return ChatResponse(
        reply=reply,
        intent=intent,
        entities=entities,
        quality=QualityMetadata(
            relevance=quality.get("relevance", 0.0),
            faithfulness=quality.get("faithfulness", 0.0),
            passed=quality.get("pass", False),
        ),
        sources=sources,
    )
