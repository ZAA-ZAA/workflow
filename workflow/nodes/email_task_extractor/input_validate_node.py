"""Validate incoming email payload for task extraction workflow."""

from __future__ import annotations

from datetime import datetime, timezone

from .state import EmailTaskExtractorState


def input_validate_node(state: EmailTaskExtractorState) -> EmailTaskExtractorState:
    from_email = (state.get("from_email") or "").strip().lower()
    subject = (state.get("subject") or "").strip()
    body = (state.get("body") or "").strip()
    received_at = (state.get("received_at") or "").strip() or datetime.now(timezone.utc).isoformat()
    gmail_message_id = (state.get("gmail_message_id") or "").strip() or None

    if not from_email:
        return {**state, "step": "validation_failed", "errors": ["from_email is required"]}
    if not subject and not body:
        return {
            **state,
            "step": "validation_failed",
            "errors": ["subject or body is required"],
        }

    return {
        **state,
        "from_email": from_email,
        "subject": subject,
        "body": body,
        "received_at": received_at,
        "gmail_message_id": gmail_message_id,
        "step": "validated",
        "errors": [],
    }
