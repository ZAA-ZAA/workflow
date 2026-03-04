"""Persist normalized tasks and update email processing state."""

from __future__ import annotations

from app.email_task_store import (
    add_tasks,
    append_processed_email_hash,
    append_processed_gmail_message_id,
)
from .state import EmailTaskExtractorState


def persist_tasks_node(state: EmailTaskExtractorState) -> EmailTaskExtractorState:
    persisted = add_tasks(state.get("tasks_normalized", []))

    email_hash = state.get("email_hash")
    if email_hash:
        append_processed_email_hash(email_hash)

    gmail_message_id = state.get("gmail_message_id")
    if gmail_message_id:
        append_processed_gmail_message_id(gmail_message_id)

    return {
        **state,
        "tasks_persisted": persisted,
        "step": "persisted",
    }
