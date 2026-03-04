"""Normalize extracted tasks, assign stable IDs, and dedupe duplicates."""

from __future__ import annotations

import hashlib

from app.email_task_store import has_processed_email_hash, list_tasks
from .state import EmailTaskExtractorState


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _task_id_from(email_hash: str, title: str, due_date: str | None, due_time: str | None) -> str:
    digest = hashlib.sha1(
        f"{email_hash}|{title.lower()}|{due_date or ''}|{due_time or ''}".encode("utf-8")
    ).hexdigest()
    return f"task-{digest[:12]}"


def normalize_and_dedupe_node(state: EmailTaskExtractorState) -> EmailTaskExtractorState:
    source_key = (
        f"{state.get('subject', '').strip().lower()}|"
        f"{state.get('body', '').strip().lower()}"
    )
    email_hash = _hash_text(source_key)

    if has_processed_email_hash(email_hash):
        return {
            **state,
            "email_hash": email_hash,
            "duplicate_email": True,
            "tasks_normalized": [],
            "step": "duplicate_email",
        }

    existing_task_ids = {task.get("task_id") for task in list_tasks()}
    normalized: list[dict] = []
    local_seen: set[str] = set()
    for task in state.get("tasks_extracted", []):
        title = (task.get("title") or "").strip()
        if not title:
            continue

        due_date = task.get("due_date")
        due_time = task.get("due_time")
        task_id = _task_id_from(email_hash, title, due_date, due_time)
        if task_id in local_seen or task_id in existing_task_ids:
            continue
        local_seen.add(task_id)

        priority = (task.get("priority") or "LOW").strip().upper()
        if priority not in ("LOW", "MEDIUM", "HIGH"):
            priority = "LOW"

        normalized.append(
            {
                "task_id": task_id,
                "title": title,
                "description": (task.get("description") or "").strip(),
                "due_date": due_date or None,
                "due_time": due_time or None,
                "priority": priority,
                "source_email": task.get("source_email")
                or {
                    "from": state.get("from_email", ""),
                    "subject": state.get("subject", ""),
                    "received_at": state.get("received_at", ""),
                },
                "status": "PENDING",
            }
        )

    return {
        **state,
        "email_hash": email_hash,
        "duplicate_email": False,
        "tasks_normalized": normalized,
        "step": "normalized",
    }
