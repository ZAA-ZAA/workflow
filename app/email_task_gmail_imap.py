"""IMAP-based Gmail intake for Email -> Task workflow (leave-workflow style)."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from app.leave_request_gmail_inbox import (
    fetch_inbox_messages,
    get_last_processed_uid,
    set_last_processed_uid,
)


def _skip_existing_on_first_run() -> bool:
    return os.getenv("EMAIL_TASK_GMAIL_SKIP_EXISTING_ON_FIRST_RUN", "1").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _imap_configured() -> bool:
    # Reuses same Gmail IMAP auth settings used by leave workflow.
    use_gmail = os.getenv("SEND_LEAVE_EMAILS_VIA_GMAIL", "").strip().lower() in ("1", "true", "yes")
    from_addr = os.getenv("GMAIL_FROM", "").strip()
    password = os.getenv("GMAIL_APP_PASSWORD", "").strip()
    return bool(use_gmail and from_addr and password)


def _imap_stream_key() -> str:
    return os.getenv("EMAIL_TASK_IMAP_STREAM_KEY", "email_task_imap_last_uid").strip() or "email_task_imap_last_uid"


def _subject_keywords_from_query(query: str | None) -> list[str] | None:
    # IMAP path does not support Gmail query DSL; allow simple comma-separated keywords as fallback.
    if not query:
        return None
    if ":" in query:
        return None
    parts = [part.strip() for part in query.split(",")]
    values = [part for part in parts if part]
    return values or None


def fetch_unprocessed_imap_emails(
    *,
    max_results: int = 10,
    query: str | None = None,
) -> dict:
    """
    Fetch unprocessed Gmail messages via IMAP using app password auth.
    """
    if not _imap_configured():
        return {
            "ok": False,
            "message": (
                "IMAP is not configured. Set SEND_LEAVE_EMAILS_VIA_GMAIL=1, "
                "GMAIL_FROM, and GMAIL_APP_PASSWORD."
            ),
            "emails": [],
        }

    stream_key = _imap_stream_key()
    min_uid = get_last_processed_uid(stream_key)
    rows = fetch_inbox_messages(
        min_uid_exclusive=min_uid,
        max_emails=max(1, int(max_results)),
        subject_keywords=_subject_keywords_from_query(query),
    )

    if not rows:
        return {
            "ok": True,
            "message": "No new IMAP messages",
            "emails": [],
            "fetched_count": 0,
            "query": query,
            "mode": "imap",
        }

    max_uid_seen = max(int(row.get("uid") or 0) for row in rows)
    if min_uid == 0 and _skip_existing_on_first_run():
        set_last_processed_uid(stream_key, max_uid_seen)
        return {
            "ok": True,
            "message": "Bootstrapped IMAP state. Skipped existing messages on first run.",
            "emails": [],
            "fetched_count": 0,
            "query": query,
            "mode": "imap",
            "bootstrapped_skip": len(rows),
        }

    emails: list[dict] = []
    for row in rows:
        uid = int(row.get("uid") or 0)
        emails.append(
            {
                "gmail_message_id": f"imap-uid-{uid}",
                "from_email": (row.get("from_email") or "").strip().lower(),
                "subject": row.get("subject") or "",
                "body": row.get("body") or "",
                "received_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    if max_uid_seen > min_uid:
        set_last_processed_uid(stream_key, max_uid_seen)

    return {
        "ok": True,
        "message": "Fetched IMAP messages",
        "emails": emails,
        "fetched_count": len(emails),
        "query": query,
        "mode": "imap",
    }
