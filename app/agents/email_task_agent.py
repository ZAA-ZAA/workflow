"""Email task extraction agent used by the Email -> Task workflow."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

from agents import Agent

_MONTH_TO_NUMBER = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

_WEEKDAY_TO_NUMBER = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def create_email_task_agent(model_override: str | None = None) -> Agent:
    """Return a dedicated agent container for email task extraction."""
    instructions = (
        "You extract actionable tasks from emails. "
        "For each task, output title, optional description, due date/time if known, and priority. "
        "Use LOW/MEDIUM/HIGH priority, keep titles concise, and do not invent details."
    )
    return Agent(
        name="email-task-agent",
        instructions=instructions,
        tools=[],
        model=model_override,
    )


def extract_tasks_from_email(
    *,
    subject: str,
    body: str,
    from_email: str,
    received_at: str | None = None,
) -> list[dict]:
    """
    Extract 0..N tasks from one email using lightweight heuristics.
    """
    clean_subject = (subject or "").strip()
    clean_body = (body or "").strip()
    clean_from = (from_email or "").strip()
    received = (received_at or "").strip() or datetime.now(timezone.utc).isoformat()

    lines = _candidate_lines(clean_subject, clean_body)
    if not lines:
        return []

    global_due_date, global_due_time = _parse_due_date_and_time(f"{clean_subject}\n{clean_body}")
    tasks: list[dict] = []
    seen_titles: set[str] = set()

    for line in lines:
        due_date, due_time = _parse_due_date_and_time(line)
        if due_date is None and global_due_date is not None:
            due_date = global_due_date
            due_time = due_time or global_due_time
        priority = _infer_priority(line, due_date=due_date)
        title = _build_title(line)
        if not title:
            continue
        key = title.lower()
        if key in seen_titles:
            continue
        seen_titles.add(key)
        description = line.strip()
        tasks.append(
            {
                "title": title,
                "description": description if description.lower() != title.lower() else "",
                "due_date": due_date,
                "due_time": due_time,
                "priority": priority,
                "source_email": {
                    "from": clean_from,
                    "subject": clean_subject,
                    "received_at": received,
                },
                "status": "PENDING",
            }
        )

    return tasks


def _candidate_lines(subject: str, body: str) -> list[str]:
    lines: list[str] = []
    for raw in body.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        normalized = re.sub(r"^[\-\*\u2022]+\s*", "", stripped)
        normalized = re.sub(r"^\d+[.)]\s*", "", normalized)
        segments = [normalized]
        if "." in normalized or ";" in normalized:
            segments = [piece.strip() for piece in re.split(r"[.;]\s*", normalized) if piece.strip()]
        for segment in segments:
            if _looks_like_task(segment):
                lines.append(segment)

    if not lines:
        sentences = re.split(r"(?<=[.!?])\s+", body)
        for sentence in sentences:
            candidate = sentence.strip()
            if candidate and _looks_like_task(candidate):
                lines.append(candidate)

    if not lines and _looks_like_task(subject):
        lines.append(subject.strip())
    return lines[:20]


def _looks_like_task(text: str) -> bool:
    lowered = (text or "").strip().lower()
    if not lowered:
        return False
    verbs = (
        "submit",
        "send",
        "prepare",
        "finish",
        "review",
        "update",
        "follow up",
        "book",
        "schedule",
        "pay",
        "renew",
        "draft",
        "fix",
        "complete",
        "share",
        "create",
    )
    due_cues = ("by ", "before ", "tomorrow", "today", "friday", "monday", "asap", "eod")
    polite_cues = ("please ", "kindly ", "need to ", "must ", "todo", "to do")
    return any(cue in lowered for cue in verbs + due_cues + polite_cues)


def _build_title(text: str, max_len: int = 90) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    cleaned = re.sub(r"^(please|kindly)\s+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(by|before)\s+(today|tomorrow|eod)\b.*$", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = cleaned.rstrip(" .")
    if len(cleaned) > max_len:
        return cleaned[: max_len - 3].rstrip() + "..."
    return cleaned


def _infer_priority(text: str, due_date: str | None) -> str:
    lowered = (text or "").lower()
    high_markers = ("asap", "urgent", "immediately", "eod", "critical", "high priority")
    medium_markers = ("tomorrow", "this week", "by ", "before ", "soon")

    if any(marker in lowered for marker in high_markers):
        return "HIGH"
    if due_date:
        try:
            due = datetime.strptime(due_date, "%Y-%m-%d").date()
            delta = (due - date.today()).days
            if delta <= 1:
                return "HIGH"
            if delta <= 4:
                return "MEDIUM"
        except Exception:
            pass
    if any(marker in lowered for marker in medium_markers):
        return "MEDIUM"
    return "LOW"


def _parse_due_date_and_time(text: str) -> tuple[str | None, str | None]:
    lowered = (text or "").lower()
    found_date: date | None = None
    found_time: str | None = None
    today = date.today()

    iso_match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", lowered)
    if iso_match:
        try:
            found_date = date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))
        except Exception:
            found_date = None

    if found_date is None:
        month_match = re.search(
            r"\b("
            + "|".join(_MONTH_TO_NUMBER.keys())
            + r")\s+(\d{1,2})(?:,?\s*(\d{4}))?\b",
            lowered,
        )
        if month_match:
            month_token = month_match.group(1)
            day_num = int(month_match.group(2))
            year_num = int(month_match.group(3)) if month_match.group(3) else today.year
            month_num = _MONTH_TO_NUMBER[month_token]
            try:
                candidate = date(year_num, month_num, day_num)
                if month_match.group(3) is None and candidate < today:
                    candidate = date(year_num + 1, month_num, day_num)
                found_date = candidate
            except Exception:
                found_date = None

    if found_date is None and "tomorrow" in lowered:
        found_date = today + timedelta(days=1)
    if found_date is None and "today" in lowered:
        found_date = today

    if found_date is None:
        for weekday_name, weekday_idx in _WEEKDAY_TO_NUMBER.items():
            if weekday_name in lowered:
                delta = (weekday_idx - today.weekday()) % 7
                found_date = today + timedelta(days=delta)
                break

    if "eod" in lowered and found_time is None:
        found_time = "17:00"
        if found_date is None:
            found_date = today

    twelve_hour = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", lowered)
    if twelve_hour:
        hour = int(twelve_hour.group(1))
        minute = int(twelve_hour.group(2) or 0)
        period = twelve_hour.group(3).lower()
        if period == "pm" and hour != 12:
            hour += 12
        if period == "am" and hour == 12:
            hour = 0
        found_time = f"{hour:02d}:{minute:02d}"

    if found_time is None:
        twenty_four_hour = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", lowered)
        if twenty_four_hour:
            found_time = f"{int(twenty_four_hour.group(1)):02d}:{int(twenty_four_hour.group(2)):02d}"

    due_date_iso = found_date.isoformat() if found_date else None
    return due_date_iso, found_time
