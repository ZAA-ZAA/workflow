"""State definition for Email -> Task Extractor workflow."""

from __future__ import annotations

from typing import TypedDict


class EmailTaskExtractorState(TypedDict):
    from_email: str
    subject: str
    body: str
    received_at: str
    gmail_message_id: str | None
    email_hash: str | None
    duplicate_email: bool
    tasks_extracted: list[dict]
    tasks_normalized: list[dict]
    tasks_persisted: list[dict]
    calendar_events: list[dict]
    summary_text: str
    errors: list[str]
    step: str
