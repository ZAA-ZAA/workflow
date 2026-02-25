"""Factory for the math helper agent."""

from datetime import datetime, timezone

from agents import Agent
from app.tools import add_numbers, web_search, list_events, send_email


def _now_iso_utc() -> str:
    """Return current UTC timestamp string for instructions."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def create_zoey_agent(model_override: str | None = None) -> Agent:
    """Return a math-focused agent with arithmetic tools attached."""
    instructions = (
        f"You are Zoey a assistant of JM. Current date/time: {_now_iso_utc()}. "
        "You are a concise math tutor. Break problems into steps, "
        "call the add_numbers tool for arithmetic, use the web_search tool for web queries, "
        "and the list_events tool for event management. "
        "Use the send_email tool for messaging; propose subject and body based on user intent,"
        "and always relay the send_email tool result back to the user. Keep answers brief."
    )
    return Agent(
        name="zoey-agent",
        instructions=instructions,
        tools=[add_numbers, web_search, list_events, send_email],
        model=model_override
    )
