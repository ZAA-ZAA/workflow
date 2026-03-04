"""Email -> Task Extractor workflow orchestration."""

from __future__ import annotations

import os

from app.email_task_gmail_api import fetch_unprocessed_gmail_emails
from app.email_task_gmail_imap import fetch_unprocessed_imap_emails
from workflow.nodes.email_task_extractor import (
    EmailTaskExtractorState,
    extract_tasks_agent_node,
    input_validate_node,
    normalize_and_dedupe_node,
    optional_create_calendar_event_node,
    persist_tasks_node,
    send_summary_email_node,
)


def run_email_task_extractor_flow(
    *,
    from_email: str,
    subject: str,
    body: str,
    received_at: str | None = None,
    gmail_message_id: str | None = None,
) -> dict:
    """Run the Email -> Task Extractor workflow for one email payload."""
    state: EmailTaskExtractorState = {
        "from_email": from_email,
        "subject": subject,
        "body": body,
        "received_at": received_at or "",
        "gmail_message_id": gmail_message_id,
        "email_hash": None,
        "duplicate_email": False,
        "tasks_extracted": [],
        "tasks_normalized": [],
        "tasks_persisted": [],
        "calendar_events": [],
        "summary_text": "",
        "errors": [],
        "step": "started",
    }

    state = input_validate_node(state)
    if state.get("step") == "validation_failed":
        return {
            "status": "VALIDATION_FAILED",
            "errors": state.get("errors", []),
            "tasks": [],
            "created_count": 0,
        }

    state = extract_tasks_agent_node(state)
    state = normalize_and_dedupe_node(state)

    if state.get("step") != "duplicate_email":
        state = persist_tasks_node(state)
    else:
        # Persist Gmail message ID even when email hash already exists.
        state = persist_tasks_node({**state, "tasks_normalized": []})

    state = optional_create_calendar_event_node(state)
    state = send_summary_email_node(state)

    return {
        "status": "DUPLICATE_EMAIL" if state.get("duplicate_email") else "COMPLETED",
        "duplicate_email": state.get("duplicate_email", False),
        "email_hash": state.get("email_hash"),
        "extracted_count": len(state.get("tasks_extracted", [])),
        "created_count": len(state.get("tasks_persisted", [])),
        "tasks": state.get("tasks_persisted", []),
        "extracted_tasks": state.get("tasks_normalized", []),
        "calendar_events": state.get("calendar_events", []),
        "summary": state.get("summary_text", ""),
    }


def run_email_task_gmail_poll(
    *,
    max_results: int = 10,
    query: str | None = None,
    allow_interactive_auth: bool = False,
    skip_existing_on_first_run: bool | None = None,
    mode: str | None = None,
) -> dict:
    """Poll Gmail inbox for unprocessed emails and extract tasks."""
    selected_mode = (mode or os.getenv("EMAIL_TASK_GMAIL_MODE", "imap")).strip().lower()
    if selected_mode not in ("imap", "oauth"):
        selected_mode = "imap"

    if selected_mode == "imap":
        fetched = fetch_unprocessed_imap_emails(
            max_results=max_results,
            query=query,
        )
    else:
        fetched = fetch_unprocessed_gmail_emails(
            max_results=max_results,
            query=query,
            allow_interactive_auth=allow_interactive_auth,
            skip_existing_on_first_run=skip_existing_on_first_run,
        )
    if not fetched.get("ok"):
        return {
            "status": "GMAIL_NOT_READY",
            "message": fetched.get("message", "Failed to fetch Gmail emails"),
            "processed_emails": 0,
            "created_tasks": 0,
            "runs": [],
            "mode": fetched.get("mode") or selected_mode,
        }

    runs: list[dict] = []
    created_tasks = 0
    for email in fetched.get("emails", []):
        result = run_email_task_extractor_flow(
            from_email=email.get("from_email", ""),
            subject=email.get("subject", ""),
            body=email.get("body", ""),
            received_at=email.get("received_at"),
            gmail_message_id=email.get("gmail_message_id"),
        )
        created_tasks += int(result.get("created_count", 0))
        runs.append(
            {
                "gmail_message_id": email.get("gmail_message_id"),
                "subject": email.get("subject"),
                "from_email": email.get("from_email"),
                "status": result.get("status"),
                "created_count": result.get("created_count", 0),
            }
        )

    return {
        "status": "COMPLETED",
        "message": fetched.get("message") or "Gmail poll finished",
        "processed_emails": len(fetched.get("emails", [])),
        "created_tasks": created_tasks,
        "runs": runs,
        "query": fetched.get("query"),
        "bootstrapped_skip": int(fetched.get("bootstrapped_skip") or 0),
        "mode": fetched.get("mode") or selected_mode,
    }
