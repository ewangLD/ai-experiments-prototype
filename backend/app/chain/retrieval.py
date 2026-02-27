"""Span 3: Document retrieval via OpenAI web search."""

from __future__ import annotations

from app.config import openai_client


def retrieve_docs(query: str) -> list[dict]:
    """Search LaunchDarkly docs using OpenAI Responses API with web_search tool.

    Returns a list of {"title": str, "url": str, "content": str}.
    OpenLLMetry auto-instruments this OpenAI call.
    """
    response = openai_client.responses.create(
        model="gpt-4o",
        tools=[
            {
                "type": "web_search_preview",
                "search_context_size": "high",
            }
        ],
        input=f"site:launchdarkly.com {query}",
    )

    documents = []
    content_text = ""

    for item in response.output:
        if item.type == "message":
            for block in item.content:
                if block.type == "output_text":
                    content_text = block.text
                    # Extract citations/annotations if present
                    if hasattr(block, "annotations") and block.annotations:
                        for ann in block.annotations:
                            if hasattr(ann, "url"):
                                documents.append(
                                    {
                                        "title": getattr(ann, "title", ann.url),
                                        "url": ann.url,
                                        "content": "",
                                    }
                                )

    # If we got content but no structured citations, return the whole text as one doc
    if content_text and not documents:
        documents.append(
            {"title": "Search Results", "url": "", "content": content_text}
        )
    elif content_text and documents:
        # Attach the full response text to the first document
        documents[0]["content"] = content_text

    return documents
