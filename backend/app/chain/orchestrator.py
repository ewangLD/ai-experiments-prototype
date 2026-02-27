"""Orchestrates the full agent chain."""

from __future__ import annotations

import asyncio
import json
import uuid
from collections import defaultdict
from collections.abc import AsyncGenerator

from ldclient.context import Context
from opentelemetry import trace, context as otel_context

from app.models import ChatRequest, ChatResponse, QualityMetadata
from app.chain.intent import classify_intent
from app.chain.router import route_query
from app.chain.rewriter import rewrite_query
from app.chain.retrieval import retrieve_docs
from app.chain.generator import generate_response
from app.chain.judge import judge_quality

# In-memory conversation store keyed by session_id
_sessions: dict[str, list[dict]] = defaultdict(list)

# Store trackers for feedback, keyed by response_id.
# In production, use a TTL cache. For this prototype, a simple dict suffices.
_trackers: dict[str, object] = {}

_tracer = trace.get_tracer("ld-support-chatbot.chain")


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _run_step(span_name: str, fn, parent_ctx):
    """Run fn inside an OTel child span, re-attaching the parent context in this thread."""
    ctx = otel_context.attach(parent_ctx)
    try:
        with _tracer.start_as_current_span(span_name):
            return fn()
    finally:
        otel_context.detach(ctx)


async def run_chain_stream(req: ChatRequest) -> AsyncGenerator[str, None]:
    """Execute the chain, yielding SSE events for each step."""
    ld_context = Context.create(req.session_id)

    history = _sessions[req.session_id]
    if req.conversation_history:
        history = [{"role": m.role, "content": m.content} for m in req.conversation_history]

    # Create parent span that lives for the entire chain.
    # We manage it manually so we can yield SSE events between child spans.
    parent_span = _tracer.start_span(
        "Support Chat Request",
        attributes={
            "user.message": req.message,
            "session.id": req.session_id,
        },
    )
    parent_ctx = trace.set_span_in_context(parent_span)

    try:
        # Step 1: Intent classification
        yield _sse("step", {"step": "intent", "status": "running", "label": "Classifying intent..."})
        intent_result = await asyncio.to_thread(
            lambda: _run_step("Classify Intent", lambda: classify_intent(req.message, ld_context), parent_ctx)
        )
        intent = intent_result.get("intent", "general")
        entities = intent_result.get("entities", [])
        yield _sse("step", {"step": "intent", "status": "done", "label": f"Intent: {intent}", "detail": {"intent": intent, "entities": entities}})

        # Step 2: Route decision
        yield _sse("step", {"step": "router", "status": "running", "label": "Deciding approach..."})
        route_result = await asyncio.to_thread(
            lambda: _run_step("Route Query", lambda: route_query(req.message, intent, entities, history, ld_context), parent_ctx)
        )
        route = route_result.get("route", "search")
        route_message = route_result.get("message", "")
        parent_span.set_attribute("chain.route", route)
        yield _sse("step", {"step": "router", "status": "done", "label": f"Route: {route}"})

        response_id = str(uuid.uuid4())
        reply = ""
        documents = []
        quality = {"relevance": 1.0, "faithfulness": 1.0, "pass": True}

        if route in ("direct", "clarify"):
            # Short-circuit: respond directly without doc search
            reply = route_message
            parent_span.set_attribute("chain.intent", intent)
            parent_span.set_attribute("chain.entities", entities)

        else:
            # Full search chain: rewrite → retrieve → generate → judge

            # Step 3: Query rewriting
            yield _sse("step", {"step": "rewrite", "status": "running", "label": "Rewriting search query..."})
            search_query = await asyncio.to_thread(
                lambda: _run_step("Rewrite Search Query", lambda: rewrite_query(req.message, intent, entities, history, ld_context), parent_ctx)
            )
            yield _sse("step", {"step": "rewrite", "status": "done", "label": f"Query: {search_query}"})

            # Step 4: Document retrieval
            yield _sse("step", {"step": "retrieval", "status": "running", "label": "Searching LaunchDarkly docs..."})
            documents = await asyncio.to_thread(
                lambda: _run_step("Search LD Docs", lambda: retrieve_docs(search_query), parent_ctx)
            )
            yield _sse("step", {"step": "retrieval", "status": "done", "label": f"Found {len(documents)} source(s)"})

            # Step 5: Response generation
            yield _sse("step", {"step": "generate", "status": "running", "label": "Generating response..."})
            reply, generator_tracker = await asyncio.to_thread(
                lambda: _run_step("Generate Response", lambda: generate_response(req.message, intent, entities, documents, history, ld_context), parent_ctx)
            )
            if generator_tracker is not None:
                _trackers[response_id] = generator_tracker
            yield _sse("step", {"step": "generate", "status": "done", "label": "Response ready"})

            # Step 6: Quality check
            yield _sse("step", {"step": "judge", "status": "running", "label": "Checking quality..."})
            quality = await asyncio.to_thread(
                lambda: _run_step("Judge Quality", lambda: judge_quality(req.message, reply, documents, ld_context), parent_ctx)
            )
            passed = quality.get("pass", False)
            yield _sse("step", {"step": "judge", "status": "done", "label": f"Quality: {'PASS' if passed else 'FAIL'}"})

            parent_span.set_attribute("chain.intent", intent)
            parent_span.set_attribute("chain.entities", entities)
            parent_span.set_attribute("chain.quality.relevance", quality.get("relevance", 0.0))
            parent_span.set_attribute("chain.quality.faithfulness", quality.get("faithfulness", 0.0))
            parent_span.set_attribute("chain.quality.passed", quality.get("pass", False))

    finally:
        parent_span.end()

    # Update conversation history
    _sessions[req.session_id].append({"role": "user", "content": req.message})
    _sessions[req.session_id].append({"role": "assistant", "content": reply})

    sources = [
        {"title": d.get("title", ""), "url": d.get("url", "")}
        for d in documents
        if d.get("url")
    ]

    result = ChatResponse(
        reply=reply,
        response_id=response_id,
        intent=intent,
        entities=entities,
        quality=QualityMetadata(
            relevance=quality.get("relevance", 0.0),
            faithfulness=quality.get("faithfulness", 0.0),
            passed=quality.get("pass", True),
        ),
        sources=sources,
    )

    yield _sse("result", result.model_dump())


def submit_feedback(response_id: str, kind: str) -> bool:
    """Submit feedback for a previous response. Returns True if tracked successfully."""
    from ldai.tracker import FeedbackKind

    tracker = _trackers.pop(response_id, None)
    if tracker is None:
        return False

    feedback_kind = FeedbackKind.Positive if kind == "positive" else FeedbackKind.Negative

    with _tracer.start_as_current_span(
        "User Feedback",
        attributes={
            "feedback.response_id": response_id,
            "feedback.kind": kind,
        },
    ):
        tracker.track_feedback({"kind": feedback_kind})

    return True


async def run_chain(req: ChatRequest) -> ChatResponse:
    """Non-streaming fallback."""
    result = None
    async for event_str in run_chain_stream(req):
        if event_str.startswith("event: result"):
            data_line = event_str.split("data: ", 1)[1].strip()
            result = ChatResponse.model_validate_json(data_line)
    return result
