"""
Gmail intake processors for leave workflow:
- Employee emails -> create leave requests
- Manager reply emails -> approve/reject pending requests
"""

from __future__ import annotations

import os
from datetime import datetime

from app.leave_request_db import (
    get_employee,
    get_employee_by_email,
    get_employee_by_name,
    get_employees,
    get_leave_request,
)
from app.leave_request_email import send_leave_email
from app.leave_request_gmail_inbox import (
    fetch_inbox_messages,
    get_last_processed_uid,
    set_last_processed_uid,
)
from app.leave_request_reply_parser import (
    parse_leave_request_email_with_ai,
    parse_manager_reply_with_ai,
)
from workflow.leave_request_workflow import run_manager_reply_flow, run_request_flow


def _known_employee_emails() -> set[str]:
    emails: set[str] = set()
    for emp in get_employees():
        email = (emp.get("email") or "").strip().lower()
        if email:
            emails.add(email)
    return emails


def _known_manager_emails() -> set[str]:
    emails: set[str] = set()
    for emp in get_employees():
        email = (emp.get("manager_email") or "").strip().lower()
        if email:
            emails.add(email)
    return emails


def _skip_existing_on_first_run() -> bool:
    # Default to on to avoid replaying old inbox history when service starts.
    return os.getenv("LEAVE_GMAIL_SKIP_EXISTING_ON_FIRST_RUN", "1").strip().lower() in ("1", "true", "yes")


def _allow_shared_employee_emails() -> bool:
    """
    Test-mode switch: allow one sender email to submit for multiple employee IDs.
    """
    return os.getenv("LEAVE_ALLOW_SHARED_EMPLOYEE_EMAILS", "0").strip().lower() in ("1", "true", "yes")


def _is_iso_date(value: str) -> bool:
    try:
        datetime.strptime((value or "").strip()[:10], "%Y-%m-%d")
        return True
    except Exception:
        return False


def _employee_request_error_email(to_addr: str, missing: list[str], raw_subject: str) -> None:
    details = "\n".join([f"- {item}" for item in missing]) if missing else "- Unknown parsing error"
    body = f"""Hi,

We could not process your leave request email yet.

Missing or invalid details:
{details}

Please resend using this format:
Employee ID: E001
Leave Type: annual or sick
Start Date: YYYY-MM-DD
End Date: YYYY-MM-DD
Reason: optional text

Original subject: {raw_subject}
"""
    send_leave_email(to_addr, "Leave Request Not Processed - Missing Information", body)


def _employee_request_success_email(to_addr: str, request_id: str) -> None:
    body = f"""Hi,

Your leave request has been submitted successfully.

Request ID: {request_id}
Status: PENDING_MANAGER

Your manager has been notified. You can also check via:
GET /leave/status/{request_id}
"""
    send_leave_email(to_addr, "Leave Request Submitted", body)


def process_employee_leave_request_emails(max_emails: int = 30) -> dict:
    """
    Process new employee leave-request emails from Gmail inbox.
    Returns summary counters.
    """
    stream_key = "employee_request_last_uid"
    min_uid = get_last_processed_uid(stream_key)
    rows = fetch_inbox_messages(
        min_uid_exclusive=min_uid,
        max_emails=max_emails,
        # Do not pre-filter heavily; sender and parser checks below are stricter.
        subject_keywords=None,
    )
    if not rows:
        return {"processed": 0, "created": 0, "errors": 0}
    if min_uid == 0 and _skip_existing_on_first_run():
        set_last_processed_uid(stream_key, max(int(r.get("uid") or 0) for r in rows))
        return {"processed": 0, "created": 0, "errors": 0, "bootstrapped_skip": len(rows)}

    processed = 0
    created = 0
    errors = 0
    max_uid_seen = min_uid
    known_employees = _known_employee_emails()

    for row in rows:
        processed += 1
        uid = int(row.get("uid") or 0)
        max_uid_seen = max(max_uid_seen, uid)

        sender = (row.get("from_email") or "").strip().lower()
        subject = (row.get("subject") or "").strip()
        body = (row.get("body") or "").strip()
        combined = (subject + "\n" + body).lower()

        # Ignore unrelated inbox mail from non-employees.
        if sender not in known_employees:
            continue

        # Skip messages that look like manager decisions.
        if "request id" in combined and ("approve" in combined or "reject" in combined or "decision" in combined):
            continue

        parsed = parse_leave_request_email_with_ai(subject, body) or {}
        parsed_emp_id = (parsed.get("employee_id") or "").strip()
        parsed_emp_name = (parsed.get("employee_name") or "").strip()

        employee = get_employee_by_email(sender)
        allow_shared = _allow_shared_employee_emails()
        if employee and parsed_emp_id and employee.get("employee_id") != parsed_emp_id:
            if allow_shared:
                # In test mode, let explicit employee_id override sender mapping.
                employee = get_employee(parsed_emp_id) or employee
            else:
                _employee_request_error_email(
                    sender,
                    [
                        f"employee_id mismatch: email belongs to {employee.get('employee_id')} but email content says {parsed_emp_id}",
                        "please use your own employee ID",
                    ],
                    subject,
                )
                errors += 1
                continue

        if not employee and parsed_emp_id:
            employee = get_employee(parsed_emp_id)
        if not employee and parsed_emp_name:
            employee = get_employee_by_name(parsed_emp_name)

        missing: list[str] = []
        if not employee:
            missing.append("employee identity not recognized (employee_id/name/email)")

        leave_type = (parsed.get("leave_type") or "").strip().lower()
        start_date = (parsed.get("start_date") or "").strip()
        end_date = (parsed.get("end_date") or "").strip()
        reason = (parsed.get("reason") or "").strip()

        if leave_type not in ("annual", "sick"):
            missing.append("leave_type (annual or sick)")
        if not _is_iso_date(start_date):
            missing.append("start_date (YYYY-MM-DD)")
        if not _is_iso_date(end_date):
            missing.append("end_date (YYYY-MM-DD)")

        if missing:
            _employee_request_error_email(sender, missing, subject)
            errors += 1
            continue

        result = run_request_flow(
            employee_id=(employee or {}).get("employee_id", ""),
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
        )

        if result.get("status") == "PENDING_MANAGER":
            request_id = result.get("request_id") or ""
            _employee_request_success_email((employee or {}).get("email") or sender, request_id)
            created += 1
        else:
            msg = result.get("message") or "Unknown validation error"
            _employee_request_error_email(sender, [msg], subject)
            errors += 1

    if max_uid_seen > min_uid:
        set_last_processed_uid(stream_key, max_uid_seen)

    return {"processed": processed, "created": created, "errors": errors}


def _manager_error_email(to_addr: str, reason: str) -> None:
    body = f"""Hi,

Your manager decision email was not processed.

Reason: {reason}

Please include:
- Request ID: LR-xxxx
- Decision: APPROVE or REJECT
- Optional comment
"""
    send_leave_email(to_addr, "Manager Decision Not Processed", body)


def _manager_ack_email(to_addr: str, request_id: str, status: str) -> None:
    body = f"""Hi,

Your decision has been processed.

Request ID: {request_id}
Result: {status}
"""
    send_leave_email(to_addr, "Manager Decision Processed", body)


def process_manager_reply_emails(max_emails: int = 40) -> dict:
    """
    Process new manager decision emails from Gmail inbox.
    Returns summary counters.
    """
    stream_key = "manager_reply_last_uid"
    min_uid = get_last_processed_uid(stream_key)
    rows = fetch_inbox_messages(
        min_uid_exclusive=min_uid,
        max_emails=max_emails,
        # Do not pre-filter heavily; sender and decision-intent checks below apply.
        subject_keywords=None,
    )
    if not rows:
        return {"processed": 0, "applied": 0, "errors": 0}
    if min_uid == 0 and _skip_existing_on_first_run():
        set_last_processed_uid(stream_key, max(int(r.get("uid") or 0) for r in rows))
        return {"processed": 0, "applied": 0, "errors": 0, "bootstrapped_skip": len(rows)}

    processed = 0
    applied = 0
    errors = 0
    max_uid_seen = min_uid
    known_managers = _known_manager_emails()

    for row in rows:
        processed += 1
        uid = int(row.get("uid") or 0)
        max_uid_seen = max(max_uid_seen, uid)

        sender = (row.get("from_email") or "").strip().lower()
        subject = (row.get("subject") or "").strip()
        body = (row.get("body") or "").strip()
        combined = (subject + "\n" + body).lower()

        # Ignore unrelated inbox mail from non-managers.
        if sender not in known_managers:
            continue
        # Only treat as decision mail when it clearly contains decision intent.
        if "request id" not in combined and "approve" not in combined and "reject" not in combined and "decision" not in combined:
            continue

        # Skip messages that look like employee request submissions.
        if "leave type" in combined and "start date" in combined and "end date" in combined and "decision" not in combined:
            continue

        parsed = parse_manager_reply_with_ai(subject, body)
        if not parsed:
            # Ignore non-actionable manager messages quietly.
            continue

        request_id = (parsed.get("request_id") or "").strip().upper()
        decision = (parsed.get("decision") or "").strip().upper()
        comment = (parsed.get("comment") or "").strip()

        if not request_id:
            # Ignore messages without explicit request id to prevent spam loops.
            continue

        req = get_leave_request(request_id)
        if not req:
            # Ignore stale/old request ids from historical inbox content.
            continue

        expected_manager = (req.get("manager_email") or "").strip().lower()
        if expected_manager and expected_manager != sender:
            _manager_error_email(sender, f"You are not the assigned manager for {request_id}")
            errors += 1
            continue

        result = run_manager_reply_flow(request_id=request_id, decision=decision, comment=comment)
        status = result.get("status") or "ERROR"
        if status in ("APPROVED", "REJECTED"):
            _manager_ack_email(sender, request_id, status)
            applied += 1
        else:
            _manager_error_email(sender, result.get("message") or f"Could not apply {decision} for {request_id}")
            errors += 1

    if max_uid_seen > min_uid:
        set_last_processed_uid(stream_key, max_uid_seen)

    return {"processed": processed, "applied": applied, "errors": errors}


def process_all_leave_emails() -> dict:
    requests = process_employee_leave_request_emails()
    replies = process_manager_reply_emails()
    return {
        "employee_requests": requests,
        "manager_replies": replies,
    }
