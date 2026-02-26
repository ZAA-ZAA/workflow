"""
Leave Request Approval Workflow.

Single-curl flow (default): run start to finish — validate, check balance,
create request, email manager, then WAIT for manager reply (via Gmail inbox
or via POST /leave/manager_reply). When reply is received, apply decision and
notify employee, then return.

Alternative: POST /leave/manager_reply from another terminal to submit
APPROVE/REJECT without using email; the waiting request will see the update.
"""

from __future__ import annotations

import os
import time

from app.leave_request_db import get_leave_request, update_leave_request
from app.leave_request_gmail_inbox import get_latest_manager_reply_from_gmail
from app.leave_request_reply_parser import parse_manager_reply_with_ai
from workflow.nodes.leave_request import (
    LeaveRequestState,
    input_validate_node,
    check_balance_node,
    create_request_node,
    send_manager_email_node,
    apply_decision_node,
    notify_employee_node,
)


def run_request_flow(
    employee_id: str,
    leave_type: str,
    start_date: str,
    end_date: str,
    reason: str = "",
) -> dict:
    """
    Run the leave request flow up to "pending manager". Returns dict with
    request_id, status, and optional message.
    """
    state: LeaveRequestState = {
        "employee_id": employee_id,
        "leave_type": leave_type,
        "start_date": start_date,
        "end_date": end_date,
        "reason": reason,
        "employee": None,
        "balance_ok": False,
        "request_id": None,
        "manager_email": None,
        "manager_email_sent": False,
        "manager_decision": None,
        "manager_comment": None,
        "step": "started",
    }

    print("[Leave Workflow] Leave request received: employee_id=" + employee_id + ", leave_type=" + leave_type + ", dates " + start_date + " to " + end_date)
    state = input_validate_node(state)
    if state.get("step") == "validation_failed":
        print("[Leave Workflow] Step: validation_failed")
        return {"request_id": None, "status": "VALIDATION_FAILED", "message": "Missing or invalid input."}
    if state.get("step") == "employee_not_found":
        print("[Leave Workflow] Step: employee_not_found")
        return {"request_id": None, "status": "EMPLOYEE_NOT_FOUND", "message": f"Employee {employee_id} not found."}

    state = check_balance_node(state)
    if state.get("step") == "insufficient_balance":
        print("[Leave Workflow] Step: insufficient_balance")
        return {"request_id": None, "status": "INSUFFICIENT_BALANCE", "message": "Not enough leave balance."}
    if state.get("step") == "invalid_dates":
        print("[Leave Workflow] Step: invalid_dates")
        return {"request_id": None, "status": "INVALID_DATES", "message": "Invalid date range."}
    if state.get("step") == "invalid_leave_type":
        print("[Leave Workflow] Step: invalid_leave_type")
        return {"request_id": None, "status": "INVALID_LEAVE_TYPE", "message": "Leave type must be annual or sick."}

    print("[Leave Workflow] Step: creating leave request")
    state = create_request_node(state)
    if state.get("step") == "create_failed":
        print("[Leave Workflow] Step: create_failed")
        return {"request_id": None, "status": "CREATE_FAILED", "message": "Could not create request."}

    print("[Leave Workflow] Step: sending email to manager")
    state = send_manager_email_node(state)
    request_id = state.get("request_id")
    print("[Leave Workflow] Step: pending_manager (request_id=" + str(request_id) + ")")
    return {
        "request_id": request_id,
        "status": "PENDING_MANAGER",
        "message": "Request created; manager has been emailed. Awaiting manager reply via POST /leave/manager_reply.",
    }


def run_request_flow_with_wait(
    employee_id: str,
    leave_type: str,
    start_date: str,
    end_date: str,
    reason: str = "",
    poll_interval_seconds: int = 15,
    timeout_seconds: int | None = None,
) -> dict:
    """
    Run the full leave workflow start-to-finish: validate, check balance,
    create request, send email to manager, then wait for manager reply.
    Reply can come from: (1) Gmail — we poll inbox and parse with AI, or
    (2) POST /leave/manager_reply (curl from another terminal). When we
    get a decision, apply it and notify the employee, then return.
    """
    if timeout_seconds is None:
        timeout_seconds = int(os.getenv("LEAVE_WAIT_TIMEOUT_SECONDS", "600"))
    print("[Leave Workflow] ---------- Leave request workflow started ----------")
    result = run_request_flow(employee_id, leave_type, start_date, end_date, reason)
    if result.get("status") != "PENDING_MANAGER":
        print("[Leave Workflow] Workflow ended early: " + str(result.get("status")))
        return result
    request_id = result.get("request_id")
    if not request_id:
        return result
    req = get_leave_request(request_id)
    manager_email = (req or {}).get("manager_email", "")
    print("[Leave Workflow] Waiting for manager's reply (poll every " + str(poll_interval_seconds) + "s, timeout " + str(timeout_seconds) + "s)...")
    print("[Leave Workflow]   Manager can: (1) Reply to the email, or (2) Use curl POST /leave/manager_reply")
    started = time.monotonic()
    poll_count = 0
    while (time.monotonic() - started) < timeout_seconds:
        time.sleep(poll_interval_seconds)
        poll_count += 1
        req = get_leave_request(request_id)
        if not req:
            print("[Leave Workflow] ERROR: Request not found.")
            return {"request_id": request_id, "status": "ERROR", "message": "Request not found."}
        status = req.get("status", "")
        if status != "PENDING_MANAGER":
            print("[Leave Workflow] Manager reply received via API (curl). Status: " + status)
            print("[Leave Workflow] Workflow complete: " + status)
            return {
                "request_id": request_id,
                "status": status,
                "message": "Manager reply received (via API).",
                "leave_request": req,
            }
        if poll_count % 4 == 1 or poll_count == 1:
            print("[Leave Workflow] Still waiting for manager reply... (poll #" + str(poll_count) + ")")
        body = get_latest_manager_reply_from_gmail(manager_email, request_id)
        if body:
            print("[Leave Workflow] Reply email found in Gmail. Parsing with AI...")
            parsed = parse_manager_reply_with_ai(body)
            if parsed and parsed.get("decision") in ("APPROVE", "REJECT"):
                print("[Leave Workflow] Manager reply via email: " + parsed["decision"])
                update_leave_request(request_id, {
                    "manager_decision": parsed["decision"],
                    "manager_comment": parsed.get("comment") or "",
                })
                req = get_leave_request(request_id)
                if not req:
                    print("[Leave Workflow] ERROR: Request not found after update.")
                    return {"request_id": request_id, "status": "ERROR", "message": "Request not found."}
                state: LeaveRequestState = {
                    "employee_id": req.get("employee_id", ""),
                    "leave_type": req.get("leave_type", ""),
                    "start_date": req.get("start_date", ""),
                    "end_date": req.get("end_date", ""),
                    "reason": req.get("reason", ""),
                    "employee": None,
                    "balance_ok": True,
                    "request_id": request_id,
                    "manager_email": req.get("manager_email"),
                    "manager_email_sent": True,
                    "manager_decision": parsed["decision"],
                    "manager_comment": parsed.get("comment") or None,
                    "step": "manager_replied",
                }
                print("[Leave Workflow] Applying decision and notifying employee...")
                state = apply_decision_node(state)
                if state.get("step") in ("decision_failed", "invalid_decision"):
                    print("[Leave Workflow] ERROR: Failed to apply decision.")
                    return {"request_id": request_id, "status": "ERROR", "message": "Failed to apply decision."}
                state = notify_employee_node(state)
                final_status = "APPROVED" if parsed["decision"] == "APPROVE" else "REJECTED"
                print("[Leave Workflow] Workflow complete: " + final_status)
                return {
                    "request_id": request_id,
                    "status": final_status,
                    "message": "Manager reply received via email; decision applied and employee notified.",
                    "leave_request": get_leave_request(request_id),
                }
            else:
                print("[Leave Workflow] Could not parse reply (unclear decision). Will retry on next poll.")
    print("[Leave Workflow] Timeout waiting for manager reply.")
    return {
        "request_id": request_id,
        "status": "TIMEOUT",
        "message": f"Wait for manager reply timed out after {timeout_seconds}s. Use POST /leave/manager_reply to submit decision.",
    }


def run_manager_reply_flow(request_id: str, decision: str, comment: str = "") -> dict:
    """
    Run the flow after manager reply: apply decision, notify employee.
    Returns dict with status and optional message.
    """
    print("[Leave Workflow] Manager reply received via API (curl). Decision: " + (decision or "").strip().upper())
    req = get_leave_request(request_id)
    if not req:
        print("[Leave Workflow] ERROR: Request not found: " + request_id)
        return {"status": "NOT_FOUND", "message": f"Request {request_id} not found."}
    if req.get("status") != "PENDING_MANAGER":
        print("[Leave Workflow] ERROR: Request already processed: " + str(req.get("status")))
        return {"status": "ALREADY_PROCESSED", "message": f"Request already in status {req.get('status')}."}

    decision_upper = (decision or "").strip().upper()
    if decision_upper not in ("APPROVE", "REJECT"):
        return {"status": "INVALID_DECISION", "message": "decision must be APPROVE or REJECT."}

    print("[Leave Workflow] Applying decision and notifying employee...")
    state: LeaveRequestState = {
        "employee_id": req.get("employee_id", ""),
        "leave_type": req.get("leave_type", ""),
        "start_date": req.get("start_date", ""),
        "end_date": req.get("end_date", ""),
        "reason": req.get("reason", ""),
        "employee": None,
        "balance_ok": True,
        "request_id": request_id,
        "manager_email": req.get("manager_email"),
        "manager_email_sent": True,
        "manager_decision": decision_upper,
        "manager_comment": (comment or "").strip() or None,
        "step": "manager_replied",
    }

    state = apply_decision_node(state)
    if state.get("step") in ("decision_failed", "invalid_decision"):
        return {"status": state.get("step", "ERROR"), "message": "Could not apply decision."}

    state = notify_employee_node(state)
    final_status = "APPROVED" if decision_upper == "APPROVE" else "REJECTED"
    print("[Leave Workflow] Workflow complete: " + final_status)
    return {
        "request_id": request_id,
        "status": "APPROVED" if decision_upper == "APPROVE" else "REJECTED",
        "message": "Decision applied and employee notified.",
    }
