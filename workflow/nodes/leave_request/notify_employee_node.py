"""Send confirmation or rejection email to employee."""

from app.leave_request_db import get_leave_request
from app.leave_request_email import send_leave_email
from .state import LeaveRequestState


def notify_employee_node(state: LeaveRequestState) -> LeaveRequestState:
    """
    Send email to employee: approval confirmation or rejection notice.
    """
    request_id = state.get("request_id")
    decision = (state.get("manager_decision") or "").strip().upper()
    req = get_leave_request(request_id) if request_id else None

    if not req:
        return {**state, "step": "notify_failed"}

    to = req.get("employee_email")
    if not to:
        return {**state, "step": "notify_failed"}

    employee_name = req.get("employee_name", "Employee")
    start = req.get("start_date", "")
    end = req.get("end_date", "")
    leave_type = req.get("leave_type", "")
    comment = (state.get("manager_comment") or "").strip()

    if decision == "APPROVE":
        subject = f"Leave Request Approved: {start} to {end}"
        body = f"""Hi {employee_name},

Your leave request has been approved.

Leave type: {leave_type}
Date range: {start} to {end}
Request ID: {request_id}

Your balance has been updated accordingly.
"""
    else:
        subject = f"Leave Request Not Approved: {start} to {end}"
        body = f"""Hi {employee_name},

Your leave request has not been approved.

Leave type: {leave_type}
Date range: {start} to {end}
Request ID: {request_id}
"""
        if comment:
            body += f"\nManager comment: {comment}\n"

    print("[Leave Workflow] Sending result to employee: " + (to or ""))
    success, message = send_leave_email(to, subject, body)
    if not success:
        print("[Leave Workflow] WARNING: Failed to notify employee: " + message)
        return {**state, "step": "notify_failed"}
    return {
        **state,
        "step": "completed",
    }
