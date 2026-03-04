"""Task extraction node that calls the dedicated email task agent."""

from __future__ import annotations

from app.agents.email_task_agent import create_email_task_agent, extract_tasks_from_email
from .state import EmailTaskExtractorState


def extract_tasks_agent_node(state: EmailTaskExtractorState) -> EmailTaskExtractorState:
    # Instantiate agent for clear workflow ownership, even when heuristics are local.
    _ = create_email_task_agent()

    tasks = extract_tasks_from_email(
        subject=state.get("subject", ""),
        body=state.get("body", ""),
        from_email=state.get("from_email", ""),
        received_at=state.get("received_at"),
    )
    return {
        **state,
        "tasks_extracted": tasks,
        "step": "tasks_extracted",
    }
