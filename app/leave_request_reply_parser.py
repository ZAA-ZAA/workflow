"""
Parse leave-related emails with AI:
- manager reply parsing (decision + optional request_id + comment)
- employee leave request parsing (employee identity + leave details)
"""

from __future__ import annotations

import json
import os
import re

from openai import OpenAI


def _call_json_parser(prompt: str) -> dict | None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You output only valid JSON. No markdown, no explanation."},
                {"role": "user", "content": prompt},
            ],
        )
        text = (response.choices[0].message.content or "").strip()
        if text.startswith("```"):
            text = re.sub(r"^```\\w*\\n?", "", text)
            text = re.sub(r"\\n?```\\s*$", "", text)
        return json.loads(text)
    except Exception as e:
        print(f"[Leave Parser] AI parse error: {e}")
        return None


def _extract_request_id_fallback(text: str) -> str:
    match = re.search(r"\bLR-\d{1,20}\b", text or "", flags=re.IGNORECASE)
    return (match.group(0).upper() if match else "").strip()


def parse_manager_reply_with_ai(email_subject: str, email_body: str) -> dict | None:
    """
    Parse manager reply email into decision, request_id, and comment.
    Returns {"request_id": "...", "decision": "APPROVE|REJECT", "comment": "..."}.
    """
    prompt = f"""You are a leave-request manager reply parser.
Extract decision, target request_id, and comment.

Email subject:
{email_subject[:500]}

Email reply:
---
{email_body[:2000]}
---

Respond with ONLY a single JSON object, no other text:
{{"request_id": "LR-0001 or empty string if missing", "decision": "APPROVE or REJECT", "comment": "optional short comment or empty string"}}

Rules:
- APPROVE if the manager agrees (e.g. approved, yes, ok, sure, granted, accept).
- REJECT if the manager disagrees (e.g. rejected, no, denied, not approved).
- Ignore typos and variations; pick the clearest intent.
- If unclear decision, use REJECT.
- comment: brief reason or empty string."""

    data = _call_json_parser(prompt)
    if not data:
        return None

    decision = (data.get("decision") or "").strip().upper()
    if decision not in ("APPROVE", "REJECT"):
        return None

    request_id = (data.get("request_id") or "").strip().upper()
    if request_id and not re.fullmatch(r"LR-\d{1,20}", request_id):
        request_id = ""
    if not request_id:
        request_id = _extract_request_id_fallback(email_subject + "\n" + email_body)

    return {
        "request_id": request_id,
        "decision": decision,
        "comment": (data.get("comment") or "").strip()[:500],
    }


def parse_leave_request_email_with_ai(email_subject: str, email_body: str) -> dict | None:
    """
    Parse employee leave request email into normalized fields.
    Returns:
    {
      "employee_id": "...|''",
      "employee_name": "...|''",
      "leave_type": "annual|sick|''",
      "start_date": "YYYY-MM-DD|''",
      "end_date": "YYYY-MM-DD|''",
      "reason": "...|''"
    }
    """
    prompt = f"""You are a leave-request intake parser.
Extract leave request fields from an employee email.

Email subject:
{email_subject[:500]}

Email body:
---
{email_body[:3000]}
---

Respond with ONLY a single JSON object:
{{
  "employee_id": "string or empty",
  "employee_name": "string or empty",
  "leave_type": "annual or sick or empty",
  "start_date": "YYYY-MM-DD or empty",
  "end_date": "YYYY-MM-DD or empty",
  "reason": "string or empty"
}}

Rules:
- Convert leave_type to annual or sick only.
- start_date/end_date must be ISO format YYYY-MM-DD.
- If unclear, set field to empty string.
- Do not invent values."""

    data = _call_json_parser(prompt)
    if not data:
        return None

    leave_type = (data.get("leave_type") or "").strip().lower()
    if leave_type not in ("annual", "sick"):
        leave_type = ""

    return {
        "employee_id": (data.get("employee_id") or "").strip(),
        "employee_name": (data.get("employee_name") or "").strip(),
        "leave_type": leave_type,
        "start_date": (data.get("start_date") or "").strip()[:10],
        "end_date": (data.get("end_date") or "").strip()[:10],
        "reason": (data.get("reason") or "").strip()[:1000],
    }
