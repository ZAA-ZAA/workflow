"""
Parse manager email reply with AI: extract APPROVE/REJECT and optional comment.
Handles typos, variations (approved, yes, ok → APPROVE; rejected, no → REJECT).
"""

from __future__ import annotations

import json
import os
import re

from openai import OpenAI


def parse_manager_reply_with_ai(email_body: str) -> dict | None:
    """
    Use OpenAI to parse manager reply email into decision and comment.
    Returns {"decision": "APPROVE"|"REJECT", "comment": "..."} or None on failure.
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    prompt = f"""You are a leave-request reply parser. Extract the manager's decision from this email reply.

Email reply:
---
{email_body[:2000]}
---

Respond with ONLY a single JSON object, no other text:
{{"decision": "APPROVE" or "REJECT", "comment": "optional short comment or empty string"}}

Rules:
- APPROVE if the manager agrees (e.g. approved, yes, ok, sure, granted, accept).
- REJECT if the manager disagrees (e.g. rejected, no, denied, not approved).
- Ignore typos and variations; pick the clearest intent.
- If unclear or ambiguous, use REJECT.
- comment: brief reason or empty string."""

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
        # Strip markdown code block if present
        if text.startswith("```"):
            text = re.sub(r"^```\w*\n?", "", text)
            text = re.sub(r"\n?```\s*$", "", text)
        data = json.loads(text)
        decision = (data.get("decision") or "").strip().upper()
        if decision not in ("APPROVE", "REJECT"):
            return None
        return {
            "decision": decision,
            "comment": (data.get("comment") or "").strip()[:500],
        }
    except Exception as e:
        print(f"[Leave Parser] AI parse error: {e}")
        return None
