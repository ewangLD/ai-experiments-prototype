"""Span 1: Intent classification."""

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
                "You are an intent classifier for a LaunchDarkly support chatbot. "
                "Classify the user message into exactly one category and extract key entities.\n\n"
                "Categories: billing, feature-question, troubleshooting, integration, general\n\n"
                "Respond with JSON only:\n"
                '{"intent": "<category>", "entities": ["<entity1>", ...]}'
            ),
        ),
    ],
)


def classify_intent(
    user_message: str, context: Context
) -> dict:
    """Return {"intent": str, "entities": list[str]}."""
    config = ai_client.completion_config(
        "ld-bot-intent-classifier",
        context,
        DEFAULT_CONFIG,
        variables={"user_message": user_message},
    )
    if not config.enabled:
        return {"intent": "general", "entities": []}

    messages = [{"role": m.role, "content": m.content} for m in config.messages]
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
        return json.loads(result.choices[0].message.content)
    except (json.JSONDecodeError, IndexError):
        return {"intent": "general", "entities": []}
