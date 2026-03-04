"""Mock summary sender node (console log for demo)."""

from __future__ import annotations

from .state import EmailTaskExtractorState


def send_summary_email_node(state: EmailTaskExtractorState) -> EmailTaskExtractorState:
    from_email = state.get("from_email", "")
    subject = state.get("subject", "")
    created_count = len(state.get("tasks_persisted", []))
    extracted_count = len(state.get("tasks_extracted", []))
    duplicate = bool(state.get("duplicate_email"))

    if duplicate:
        summary = "Duplicate email detected. No new tasks were saved."
    else:
        summary = f"Extracted {extracted_count} task(s), saved {created_count} new task(s)."

    log_message = (
        f"[Email Task Workflow] Summary to {from_email}: {summary} "
        f"(subject='{subject}')"
    )
    print(log_message)

    return {
        **state,
        "summary_text": summary,
        "step": "completed",
    }
