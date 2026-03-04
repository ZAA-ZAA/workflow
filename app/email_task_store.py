"""JSON-backed storage for email task extractor workflow."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TASKS_FILE = DATA_DIR / "tasks.json"
EMAIL_STATE_FILE = DATA_DIR / "email_state.json"
_LOCK = threading.RLock()


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path: Path, data: Any) -> None:
    _ensure_data_dir()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def ensure_email_task_store() -> None:
    """Create tasks/state files if they do not exist yet."""
    with _LOCK:
        if not TASKS_FILE.exists():
            _write_json(TASKS_FILE, {"tasks": []})
        if not EMAIL_STATE_FILE.exists():
            _write_json(
                EMAIL_STATE_FILE,
                {
                    "processed_email_hashes": [],
                    "processed_gmail_message_ids": [],
                    "last_processed_gmail_message_id": None,
                },
            )


def get_tasks_data() -> dict:
    with _LOCK:
        ensure_email_task_store()
        data = _read_json(TASKS_FILE, {"tasks": []})
        if not isinstance(data, dict):
            return {"tasks": []}
        if not isinstance(data.get("tasks"), list):
            data["tasks"] = []
        return data


def list_tasks(status: str | None = None) -> list[dict]:
    tasks = get_tasks_data().get("tasks", [])
    if not status:
        return tasks
    normalized = status.strip().upper()
    return [task for task in tasks if (task.get("status") or "").upper() == normalized]


def add_tasks(tasks: list[dict]) -> list[dict]:
    """Append tasks that do not already exist by task_id."""
    if not tasks:
        return []
    with _LOCK:
        data = get_tasks_data()
        existing = data.get("tasks", [])
        existing_ids = {task.get("task_id") for task in existing}
        created: list[dict] = []
        for task in tasks:
            task_id = task.get("task_id")
            if not task_id or task_id in existing_ids:
                continue
            existing.append(task)
            existing_ids.add(task_id)
            created.append(task)
        data["tasks"] = existing
        _write_json(TASKS_FILE, data)
        return created


def mark_task_done(task_id: str) -> dict | None:
    """Set one task status to DONE and return the updated record."""
    normalized_id = (task_id or "").strip()
    if not normalized_id:
        return None
    with _LOCK:
        data = get_tasks_data()
        tasks = data.get("tasks", [])
        updated_task: dict | None = None
        for i, task in enumerate(tasks):
            if task.get("task_id") != normalized_id:
                continue
            updated = {
                **task,
                "status": "DONE",
                "done_at": datetime.now(timezone.utc).isoformat(),
            }
            tasks[i] = updated
            updated_task = updated
            break
        if updated_task is None:
            return None
        data["tasks"] = tasks
        _write_json(TASKS_FILE, data)
        return updated_task


def get_email_state() -> dict:
    with _LOCK:
        ensure_email_task_store()
        state = _read_json(
            EMAIL_STATE_FILE,
            {
                "processed_email_hashes": [],
                "processed_gmail_message_ids": [],
                "last_processed_gmail_message_id": None,
            },
        )
        if not isinstance(state, dict):
            return {
                "processed_email_hashes": [],
                "processed_gmail_message_ids": [],
                "last_processed_gmail_message_id": None,
            }
        state.setdefault("processed_email_hashes", [])
        state.setdefault("processed_gmail_message_ids", [])
        state.setdefault("last_processed_gmail_message_id", None)
        return state


def save_email_state(state: dict) -> None:
    with _LOCK:
        normalized = {
            "processed_email_hashes": list(state.get("processed_email_hashes", [])),
            "processed_gmail_message_ids": list(state.get("processed_gmail_message_ids", [])),
            "last_processed_gmail_message_id": state.get("last_processed_gmail_message_id"),
        }
        _write_json(EMAIL_STATE_FILE, normalized)


def has_processed_email_hash(email_hash: str) -> bool:
    normalized = (email_hash or "").strip()
    if not normalized:
        return False
    state = get_email_state()
    return normalized in set(state.get("processed_email_hashes", []))


def append_processed_email_hash(email_hash: str, max_items: int = 1000) -> None:
    normalized = (email_hash or "").strip()
    if not normalized:
        return
    with _LOCK:
        state = get_email_state()
        hashes = [h for h in state.get("processed_email_hashes", []) if isinstance(h, str)]
        if normalized not in hashes:
            hashes.append(normalized)
        if len(hashes) > max_items:
            hashes = hashes[-max_items:]
        state["processed_email_hashes"] = hashes
        save_email_state(state)


def has_processed_gmail_message_id(message_id: str) -> bool:
    normalized = (message_id or "").strip()
    if not normalized:
        return False
    state = get_email_state()
    return normalized in set(state.get("processed_gmail_message_ids", []))


def append_processed_gmail_message_id(message_id: str, max_items: int = 2000) -> None:
    normalized = (message_id or "").strip()
    if not normalized:
        return
    with _LOCK:
        state = get_email_state()
        ids = [v for v in state.get("processed_gmail_message_ids", []) if isinstance(v, str)]
        if normalized not in ids:
            ids.append(normalized)
        if len(ids) > max_items:
            ids = ids[-max_items:]
        state["processed_gmail_message_ids"] = ids
        state["last_processed_gmail_message_id"] = normalized
        save_email_state(state)


def append_processed_gmail_message_ids(message_ids: list[str], max_items: int = 2000) -> int:
    """
    Append multiple Gmail message ids and return how many were newly added.
    """
    cleaned = []
    for value in message_ids:
        normalized = (value or "").strip()
        if normalized:
            cleaned.append(normalized)
    if not cleaned:
        return 0

    with _LOCK:
        state = get_email_state()
        ids = [v for v in state.get("processed_gmail_message_ids", []) if isinstance(v, str)]
        existing = set(ids)
        added = 0
        for message_id in cleaned:
            if message_id in existing:
                continue
            ids.append(message_id)
            existing.add(message_id)
            added += 1
        if len(ids) > max_items:
            ids = ids[-max_items:]
        state["processed_gmail_message_ids"] = ids
        state["last_processed_gmail_message_id"] = ids[-1] if ids else state.get("last_processed_gmail_message_id")
        save_email_state(state)
        return added
