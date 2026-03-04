"""Optional calendar integration stub for tasks with due date/time."""

from __future__ import annotations

from .state import EmailTaskExtractorState


def optional_create_calendar_event_node(state: EmailTaskExtractorState) -> EmailTaskExtractorState:
    events: list[dict] = []
    for task in state.get("tasks_persisted", []):
        if not task.get("due_date"):
            continue
        events.append(
            {
                "task_id": task.get("task_id"),
                "status": "NOT_IMPLEMENTED",
                "message": (
                    "Calendar event stub only. Plug Google Calendar events.insert here "
                    "when OAuth credentials are available."
                ),
            }
        )

    return {
        **state,
        "calendar_events": events,
        "step": "calendar_stubbed",
    }
