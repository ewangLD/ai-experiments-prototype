"""Span 2: Query rewriting for search."""

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
                "You are a search query optimizer for LaunchDarkly documentation. "
                "Given a user message and conversation context, produce a concise search query "
                "optimized for finding relevant LaunchDarkly documentation.\n\n"
                "Respond with JSON only:\n"
                '{"query": "<optimized search query>"}'
            ),
        ),
    ],
)


def rewrite_query(
    user_message: str,
    intent: str,
    entities: list[str],
    conversation_history: list[dict],
    context: Context,
) -> str:
    """Return an optimized search query string."""
    config = ai_client.completion_config(
        "ld-bot-query-rewriter",
        context,
        DEFAULT_CONFIG,
        variables={
            "user_message": user_message,
            "intent": intent,
            "entities": ", ".join(entities),
        },
    )
    if not config.enabled:
        return user_message

    messages = [{"role": m.role, "content": m.content} for m in config.messages]

    # Include recent conversation for context
    for msg in conversation_history[-4:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": user_message})

    result = config.tracker.track_openai_metrics(
        lambda: openai_client.chat.completions.create(
            model=config.model.name,
            messages=messages,
            temperature=config.model.get_parameter("temperature") or 0,
            response_format={"type": "json_object"},
        )
    )

    try:
        return json.loads(result.choices[0].message.content).get("query", user_message)
    except (json.JSONDecodeError, IndexError):
        return user_message
