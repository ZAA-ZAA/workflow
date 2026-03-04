"""Optional Gmail API integration for Email -> Task workflow (OAuth)."""

from __future__ import annotations

import base64
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from app.email_task_store import append_processed_gmail_message_ids, get_email_state

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _decode_base64url(value: str | None) -> str:
    if not value:
        return ""
    try:
        padding = "=" * ((4 - len(value) % 4) % 4)
        raw = base64.urlsafe_b64decode((value + padding).encode("utf-8"))
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return ""


def _extract_header(headers: list[dict], key: str) -> str:
    target = key.lower()
    for header in headers or []:
        if (header.get("name") or "").lower() == target:
            return (header.get("value") or "").strip()
    return ""


def _extract_email_address(from_header: str) -> str:
    text = (from_header or "").strip()
    match = re.search(r"<([^>]+)>", text)
    if match:
        return match.group(1).strip().lower()
    return text.lower()


def _extract_text_body(payload: dict | None) -> str:
    if not payload:
        return ""

    mime_type = (payload.get("mimeType") or "").lower()
    body = payload.get("body") or {}

    if mime_type == "text/plain":
        return _decode_base64url(body.get("data"))

    for part in payload.get("parts") or []:
        candidate = _extract_text_body(part)
        if candidate.strip():
            return candidate.strip()

    if body.get("data"):
        return _decode_base64url(body.get("data"))
    return ""


def _skip_existing_on_first_run() -> bool:
    # Default ON: prevents replaying historical inbox messages on first startup.
    return os.getenv("EMAIL_TASK_GMAIL_SKIP_EXISTING_ON_FIRST_RUN", "1").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _get_gmail_service(allow_interactive_auth: bool = False):
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        return None, "Google API dependencies are missing. Install requirements and rebuild Docker."

    credentials_path = Path(
        os.getenv("EMAIL_TASK_GMAIL_CREDENTIALS_FILE", str(PROJECT_ROOT / "credentials.json"))
    )
    token_path = Path(
        os.getenv("EMAIL_TASK_GMAIL_TOKEN_FILE", str(PROJECT_ROOT / "data" / "gmail_token.json"))
    )

    creds = None
    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as exc:
                return None, f"Failed to refresh Gmail token: {exc}"
        else:
            if not credentials_path.exists():
                return None, (
                    "Gmail OAuth credentials file not found. "
                    f"Expected at: {credentials_path}"
                )
            if not allow_interactive_auth:
                return None, (
                    "No valid Gmail token found. Run first-time OAuth auth to generate token.json "
                    "or call poll with allow_interactive_auth=true in a local environment."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)

        token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(token_path, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())

    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    return service, ""


def fetch_unprocessed_gmail_emails(
    *,
    max_results: int = 10,
    query: str | None = None,
    allow_interactive_auth: bool = False,
    skip_existing_on_first_run: bool | None = None,
) -> dict:
    """
    Fetch unprocessed Gmail messages as email payload objects.
    """
    service, error = _get_gmail_service(allow_interactive_auth=allow_interactive_auth)
    if service is None:
        return {"ok": False, "message": error, "emails": []}

    state = get_email_state()
    already_processed = set(state.get("processed_gmail_message_ids", []))

    user_id = os.getenv("EMAIL_TASK_GMAIL_USER_ID", "me")
    gmail_query = (query or os.getenv("EMAIL_TASK_GMAIL_QUERY", "newer_than:7d")).strip() or None

    try:
        response = (
            service.users()
            .messages()
            .list(userId=user_id, q=gmail_query, maxResults=max_results)
            .execute()
        )
        refs = response.get("messages", []) or []
    except Exception as exc:
        return {"ok": False, "message": f"Gmail list-messages failed: {exc}", "emails": []}

    skip_first_run = _skip_existing_on_first_run() if skip_existing_on_first_run is None else skip_existing_on_first_run
    ref_ids = [(ref.get("id") or "").strip() for ref in refs if (ref.get("id") or "").strip()]
    if not already_processed and ref_ids and skip_first_run:
        added = append_processed_gmail_message_ids(ref_ids)
        return {
            "ok": True,
            "message": "Bootstrapped Gmail state. Skipped existing messages on first run.",
            "emails": [],
            "fetched_count": 0,
            "query": gmail_query,
            "bootstrapped_skip": added,
        }

    refs = list(reversed(refs))
    emails: list[dict] = []
    for ref in refs:
        message_id = (ref.get("id") or "").strip()
        if not message_id or message_id in already_processed:
            continue
        try:
            message = (
                service.users()
                .messages()
                .get(userId=user_id, id=message_id, format="full")
                .execute()
            )
        except Exception:
            continue

        payload = message.get("payload") or {}
        headers = payload.get("headers") or []
        from_raw = _extract_header(headers, "From")
        subject = _extract_header(headers, "Subject")
        date_header = _extract_header(headers, "Date")
        body = _extract_text_body(payload)

        emails.append(
            {
                "gmail_message_id": message_id,
                "from_email": _extract_email_address(from_raw),
                "subject": subject,
                "body": body,
                "received_at": date_header or datetime.now(timezone.utc).isoformat(),
            }
        )

    return {
        "ok": True,
        "message": "Fetched Gmail messages",
        "emails": emails,
        "fetched_count": len(emails),
        "query": gmail_query,
    }
