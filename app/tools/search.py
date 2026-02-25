"""Search tool leveraging OpenAI's built-in web_search capability."""

import os
from typing import Optional

from openai import OpenAI

from agents import function_tool


@function_tool
def web_search(query: str, search_context_size: str = "medium", model: Optional[str] = None) -> str:
    """Search the web via OpenAI's Responses API and return a concise answer with sources.

    search_context_size must be one of: low, medium, high.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=api_key)
    model_name = model or "gpt-4o-mini"

    if search_context_size == "auto":  # backward compatibility
        search_context_size = "medium"

    if search_context_size not in {"low", "medium", "high"}:
        raise ValueError("search_context_size must be one of: low, medium, high")

    response = client.responses.create(
        model=model_name,
        input=query,
        tools=[
            {
                "type": "web_search",
                "search_context_size": search_context_size,
            }
        ],
        tool_choice="auto",
    )

    # Prefer the high-level output text when available.
    if getattr(response, "output_text", None):
        return response.output_text

    # Fallback to string form.
    return str(response)
