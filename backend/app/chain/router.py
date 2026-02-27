"""Span 1b: Query router — decides whether to search docs, respond directly, or clarify."""

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
                "You are a routing assistant for a LaunchDarkly support chatbot. "
                "Given the user message, intent classification, and conversation history, decide the best action.\n\n"
                "Routes:\n"
                '- "search": The user has a specific question that requires searching LaunchDarkly documentation. '
                "Use this for feature questions, troubleshooting, integration help, billing questions, etc.\n"
                '- "clarify": The user\'s question is too vague or ambiguous to search for. '
                'Ask a clarifying question to understand what they need. Examples: "help me", "I have a problem", "how does it work"\n'
                '- "direct": The user\'s message doesn\'t need documentation. '
                "Use this for greetings, thanks, goodbyes, or simple conversational messages.\n\n"
                "Respond with JSON only:\n"
                '{"route": "<search|clarify|direct>", "message": "<response if route is clarify or direct, empty string if search>"}'
            ),
        ),
    ],
)


def route_query(
    user_message: str,
    intent: str,
    entities: list[str],
    conversation_history: list[dict],
    context: Context,
) -> dict:
    """Return {"route": "search"|"clarify"|"direct", "message": str}."""
    config = ai_client.completion_config(
        "ld-bot-router",
        context,
        DEFAULT_CONFIG,
        variables={
            "user_message": user_message,
            "intent": intent,
            "entities": ", ".join(entities),
        },
    )
    if not config.enabled:
        return {"route": "search", "message": ""}

    messages = [{"role": m.role, "content": m.content} for m in config.messages]

    # Include recent conversation for context
    for msg in conversation_history[-4:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append(
        {
            "role": "user",
            "content": f"Intent: {intent}\nEntities: {', '.join(entities)}\n\nUser message: {user_message}",
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
        return {"route": "search", "message": ""}
