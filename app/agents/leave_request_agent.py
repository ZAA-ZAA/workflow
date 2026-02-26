"""Leave Request agent — assists the leave approval workflow (e.g. summaries for managers)."""

from agents import Agent


def create_leave_request_agent(model_override: str | None = None) -> Agent:
    """
    Return an agent that helps with leave request context: e.g. summarizing
    an employee's leave situation for a manager. No tools; can be used from
    workflow nodes to generate short summaries or suggestions.
    """
    instructions = (
        "You are a Leave Request assistant. You help summarize employee leave information "
        "for managers: balance, recent history, and request details. Keep responses brief and factual. "
        "When given employee details and a leave request, produce a short paragraph suitable for "
        "inclusion in an approval email. Do not make up data; use only what is provided."
    )
    return Agent(
        name="leave-request-agent",
        instructions=instructions,
        tools=[],
        model=model_override,
    )
