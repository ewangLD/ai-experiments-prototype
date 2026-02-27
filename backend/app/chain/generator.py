"""Span 4: Response generation."""

from __future__ import annotations

from ldclient.context import Context
from ldai import AICompletionConfigDefault, LDMessage, ModelConfig, ProviderConfig

from app.config import ai_client, openai_client

DEFAULT_CONFIG = AICompletionConfigDefault(
    enabled=True,
    model=ModelConfig(name="gpt-4o", parameters={"temperature": 0.3}),
    provider=ProviderConfig("openai"),
    messages=[
        LDMessage(
            role="system",
            content=(
                "You are a helpful LaunchDarkly support assistant. "
                "Answer the user's question using the provided documentation context. "
                "Be accurate, concise, and cite sources when possible.\n\n"
                "Intent: {{intent}}\n"
                "Documentation context:\n{{docs}}\n\n"
                "If the documentation doesn't contain enough information to answer, "
                "say so honestly and suggest where to find more help."
            ),
        ),
    ],
)


def generate_response(
    user_message: str,
    intent: str,
    entities: list[str],
    documents: list[dict],
    conversation_history: list[dict],
    context: Context,
) -> str:
    """Generate the final response using retrieved docs and intent."""
    docs_text = "\n\n".join(
        f"[{d.get('title', 'Source')}]({d.get('url', '')})\n{d.get('content', '')}"
        for d in documents
    ) or "No documentation found."

    config = ai_client.completion_config(
        "ld-bot-response-generator",
        context,
        DEFAULT_CONFIG,
        variables={
            "intent": intent,
            "docs": docs_text,
            "entities": ", ".join(entities),
        },
    )
    if not config.enabled:
        return "I'm sorry, I'm unable to help right now. Please try again later."

    messages = [{"role": m.role, "content": m.content} for m in config.messages]

    # Add conversation history
    for msg in conversation_history[-6:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": user_message})

    result = config.tracker.track_openai_metrics(
        lambda: openai_client.chat.completions.create(
            model=config.model.name,
            messages=messages,
            temperature=config.model.get_parameter("temperature") or 0.3,
        )
    )

    return result.choices[0].message.content or "I couldn't generate a response."
