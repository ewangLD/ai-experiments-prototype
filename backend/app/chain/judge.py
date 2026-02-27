"""Span 5: Quality check (LLM-as-judge)."""

from __future__ import annotations

import json

from ldclient.context import Context
from ldai import AICompletionConfigDefault, LDMessage, ModelConfig, ProviderConfig

from app.config import ai_client, openai_client

DEFAULT_CONFIG = AICompletionConfigDefault(
    enabled=True,
    model=ModelConfig(name="gpt-4o-mini", parameters={"temperature": 0}),
    provider=ProviderConfig("openai"),
    messages=[
        LDMessage(
            role="system",
            content=(
                "You are a quality judge for a LaunchDarkly support chatbot. "
                "Evaluate the assistant's response against the user's question and source documents.\n\n"
                "Score on two dimensions (0.0 to 1.0):\n"
                "- relevance: Does the response address the user's question?\n"
                "- faithfulness: Is the response grounded in the provided source documents?\n\n"
                "A response passes if both scores are >= 0.6.\n\n"
                "Respond with JSON only:\n"
                '{"relevance": <float>, "faithfulness": <float>, "pass": <bool>}'
            ),
        ),
    ],
)


def judge_quality(
    user_message: str,
    response_text: str,
    documents: list[dict],
    context: Context,
) -> dict:
    """Return {"relevance": float, "faithfulness": float, "pass": bool}."""
    config = ai_client.completion_config(
        "ld-bot-quality-judge",
        context,
        DEFAULT_CONFIG,
    )
    if not config.enabled:
        return {"relevance": 1.0, "faithfulness": 1.0, "pass": True}

    docs_text = "\n\n".join(
        f"[{d.get('title', 'Source')}]\n{d.get('content', '')}" for d in documents
    ) or "No documents."

    messages = [{"role": m.role, "content": m.content} for m in config.messages]
    messages.append(
        {
            "role": "user",
            "content": (
                f"User question: {user_message}\n\n"
                f"Assistant response: {response_text}\n\n"
                f"Source documents:\n{docs_text}"
            ),
        }
    )

    result = config.tracker.track_openai_metrics(
        lambda: openai_client.chat.completions.create(
            model=config.model.name,
            messages=messages,
            temperature=config.model.get_parameter("temperature") or 0,
            response_format={"type": "json_object"},
        )
    )

    try:
        return json.loads(result.choices[0].message.content)
    except (json.JSONDecodeError, IndexError):
        return {"relevance": 0.0, "faithfulness": 0.0, "pass": False}
