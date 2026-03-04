"""
Send leave-related emails. Logs always; optionally sends via Gmail SMTP when
GMAIL_APP_PASSWORD (and optionally SEND_LEAVE_EMAILS_VIA_GMAIL=1) is set.
"""

from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_leave_email(to: str, subject: str, body: str) -> tuple[bool, str]:
    """
    Send an email: always log; if GMAIL_APP_PASSWORD is set, also send via Gmail SMTP.
    Returns (success, message).
    """
    print(f"[Leave Email] To: {to}")
    print(f"[Leave Email] Subject: {subject}")
    print(f"[Leave Email] Body:\n{body[:500]}{'...' if len(body) > 500 else ''}\n")

    use_gmail = os.getenv("SEND_LEAVE_EMAILS_VIA_GMAIL", "").strip().lower() in ("1", "true", "yes")
    password = os.getenv("GMAIL_APP_PASSWORD", "").strip()
    from_addr = os.getenv("GMAIL_FROM", "").strip() or to

    if not use_gmail or not password:
        msg = "Email logged (Gmail not configured; set SEND_LEAVE_EMAILS_VIA_GMAIL=1 and GMAIL_APP_PASSWORD to send)."
        print(f"[Leave Email] Result: {msg}")
        return True, msg

    try:
        msg = MIMEMultipart()
        msg["From"] = from_addr
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(from_addr, password)
            server.sendmail(from_addr, [to], msg.as_string())
        out = "Email sent via Gmail."
        print(f"[Leave Email] Result: {out}")
        return True, out
    except Exception as e:
        err = str(e)
        print(f"[Leave Email] ERROR sending via Gmail: {err}")
        return False, err
