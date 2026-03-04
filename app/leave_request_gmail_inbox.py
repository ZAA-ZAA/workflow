"""
Read leave-related emails from Gmail inbox via IMAP.
Uses GMAIL_FROM + GMAIL_APP_PASSWORD.
"""

from __future__ import annotations

import email
import imaplib
import json
import os
import re
import threading
from email.header import decode_header
from pathlib import Path

STATE_FILE = Path(__file__).resolve().parent.parent / "data" / "gmail_inbox_state.json"
_STATE_LOCK = threading.RLock()


def _decode_mime(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", errors="replace")
        except Exception:
            return value.decode("latin-1", errors="replace")
    decoded_parts = decode_header(value)
    chunks: list[str] = []
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            enc = encoding or "utf-8"
            try:
                chunks.append(part.decode(enc, errors="replace"))
            except Exception:
                chunks.append(part.decode("latin-1", errors="replace"))
        else:
            chunks.append(part)
    return "".join(chunks)


def _extract_email_address(from_value: str) -> str:
    text = (from_value or "").strip()
    match = re.search(r"<([^>]+)>", text)
    if match:
        return match.group(1).strip().lower()
    return text.lower()


def _get_body(msg: email.message.Message) -> str:
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() != "text/plain":
                continue
            try:
                payload = part.get_payload(decode=True)
                body = (payload or b"").decode("utf-8", errors="replace")
            except Exception:
                body = ""
            if body.strip():
                break
    else:
        try:
            payload = msg.get_payload(decode=True)
            body = (payload or b"").decode("utf-8", errors="replace") if payload else ""
        except Exception:
            body = str(msg.get_payload() or "")
    return (body or "").strip()


def _imap_configured() -> bool:
    use_gmail = os.getenv("SEND_LEAVE_EMAILS_VIA_GMAIL", "").strip().lower() in ("1", "true", "yes")
    from_addr = os.getenv("GMAIL_FROM", "").strip()
    password = os.getenv("GMAIL_APP_PASSWORD", "").strip()
    return bool(use_gmail and from_addr and password)


def _load_state() -> dict:
    with _STATE_LOCK:
        if not STATE_FILE.exists():
            return {}
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {}


def _save_state(data: dict) -> None:
    with _STATE_LOCK:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


def get_last_processed_uid(stream_key: str) -> int:
    state = _load_state()
    value = state.get(stream_key, 0)
    try:
        return int(value)
    except Exception:
        return 0


def set_last_processed_uid(stream_key: str, uid: int) -> None:
    with _STATE_LOCK:
        state = _load_state()
        state[stream_key] = int(uid)
        _save_state(state)


def fetch_inbox_messages(
    min_uid_exclusive: int = 0,
    max_emails: int = 50,
    from_email: str | None = None,
    subject_keywords: list[str] | None = None,
) -> list[dict]:
    """
    Fetch Gmail inbox messages newer than min_uid_exclusive.
    Returns list of dicts: {uid, from_email, from_raw, subject, body} sorted by UID asc.
    """
    if not _imap_configured():
        return []

    expected_from = (from_email or "").strip().lower()
    keywords = [(k or "").strip().lower() for k in (subject_keywords or []) if (k or "").strip()]

    from_addr = os.getenv("GMAIL_FROM", "").strip()
    password = os.getenv("GMAIL_APP_PASSWORD", "").strip()

    timeout_seconds = int(os.getenv("LEAVE_GMAIL_IMAP_TIMEOUT_SECONDS", "20"))
    try:
        with imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=timeout_seconds) as imap:
            imap.login(from_addr, password)
            imap.select("INBOX")
            status, data = imap.uid("search", None, "ALL")
            if status != "OK" or not data or not data[0]:
                return []

            ids = [int(x) for x in data[0].split() if x.isdigit()]
            ids = [uid for uid in ids if uid > min_uid_exclusive]
            if not ids:
                return []
            ids = ids[-max_emails:] if len(ids) > max_emails else ids

            rows: list[dict] = []
            for uid in ids:
                try:
                    fetch_status, msg_data = imap.uid("fetch", str(uid), "(RFC822)")
                    if fetch_status != "OK" or not msg_data:
                        continue
                    raw = msg_data[0][1]
                    msg = email.message_from_bytes(raw)
                    from_raw = _decode_mime(msg.get("From", ""))
                    sender = _extract_email_address(from_raw)
                    if expected_from and sender != expected_from:
                        continue
                    subject = _decode_mime(msg.get("Subject", ""))
                    if keywords:
                        lowered = (subject + "\n" + _get_body(msg)).lower()
                        if not any(k in lowered for k in keywords):
                            continue
                    body = _get_body(msg)
                    rows.append(
                        {
                            "uid": uid,
                            "from_email": sender,
                            "from_raw": from_raw,
                            "subject": subject,
                            "body": body,
                        }
                    )
                except Exception:
                    continue
            return rows
    except Exception as e:
        print(f"[Leave Gmail] IMAP read error: {e}")
        return []


def get_latest_manager_reply_from_gmail(
    manager_email: str,
    request_id: str | None = None,
    max_emails: int = 20,
) -> str | None:
    """
    Backward-compatible helper: get the latest reply body from a manager.
    If request_id is provided, subject/body must include that request id.
    """
    rows = fetch_inbox_messages(
        min_uid_exclusive=0,
        max_emails=max_emails,
        from_email=(manager_email or "").strip().lower(),
    )
    if not rows:
        return None

    rid = (request_id or "").strip().upper()
    for row in reversed(rows):
        subject = (row.get("subject") or "")
        body = (row.get("body") or "")
        text = f"{subject}\n{body}".upper()
        if rid and rid not in text:
            continue
        return body
    return None
