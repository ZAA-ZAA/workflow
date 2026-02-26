"""
Read manager reply from Gmail inbox via IMAP.
Uses GMAIL_FROM + GMAIL_APP_PASSWORD (same as sending).
Replies to our leave-request email go to GMAIL_FROM inbox; we search for
recent emails FROM manager_email with subject containing "Leave Request".
"""

from __future__ import annotations

import email
import imaplib
import os
import re


def _decode_mime(s: str | bytes | None) -> str:
    if s is None:
        return ""
    if isinstance(s, str):
        return s
    if isinstance(s, bytes):
        try:
            return s.decode("utf-8", errors="replace")
        except Exception:
            return s.decode("latin-1", errors="replace")
    return str(s)


def _get_body(msg: email.message.Message) -> str:
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                try:
                    payload = part.get_payload(decode=True)
                    body = (payload or b"").decode("utf-8", errors="replace")
                except Exception:
                    pass
                if body.strip():
                    break
    else:
        try:
            payload = msg.get_payload(decode=True)
            body = (payload or b"").decode("utf-8", errors="replace") if payload else ""
        except Exception:
            body = str(msg.get_payload() or "")
    return (body or "").strip()


def get_latest_manager_reply_from_gmail(
    manager_email: str,
    request_id: str | None = None,
    max_emails: int = 20,
) -> str | None:
    """
    Connect to Gmail IMAP as GMAIL_FROM, search for recent emails FROM
    manager_email with subject containing "Leave Request" or "Re:", fetch
    the latest one's body. Returns body text or None if none found or not configured.
    """
    from_addr = os.getenv("GMAIL_FROM", "").strip()
    password = os.getenv("GMAIL_APP_PASSWORD", "").strip()
    use_gmail = os.getenv("SEND_LEAVE_EMAILS_VIA_GMAIL", "").strip().lower() in ("1", "true", "yes")

    if not use_gmail or not password or not from_addr:
        return None

    manager_email = (manager_email or "").strip().lower()
    if not manager_email:
        return None

    try:
        with imaplib.IMAP4_SSL("imap.gmail.com", 993) as imap:
            imap.login(from_addr, password)
            imap.select("INBOX")
            # Search for recent emails (last few dozen)
            _, data = imap.search(None, "ALL")
            if not data or not data[0]:
                return None
            ids = data[0].split()
            ids = ids[-max_emails:] if len(ids) > max_emails else ids
            latest_body = None
            for uid in reversed(ids):
                try:
                    _, msg_data = imap.fetch(uid, "(RFC822)")
                    if not msg_data:
                        continue
                    raw = msg_data[0][1]
                    msg = email.message_from_bytes(raw)
                    from_str = _decode_mime(msg.get("From", ""))
                    # Check if from manager (address often in <...>)
                    if manager_email not in from_str.lower():
                        continue
                    subj = _decode_mime(msg.get("Subject", ""))
                    if "leave request" not in subj.lower() and "re:" not in subj.lower():
                        continue
                    body = _get_body(msg)
                    if body:
                        latest_body = body
                        break
                except Exception:
                    continue
            return latest_body
    except Exception as e:
        print(f"[Leave Gmail] IMAP read error: {e}")
        return None
