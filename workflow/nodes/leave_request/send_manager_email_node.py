"""Send email to manager with full context and approval instructions."""

import os

from app.leave_request_email import send_leave_email
from .state import LeaveRequestState


def _recent_history_summary(employee: dict, limit: int = 3) -> str:
    history = employee.get("leave_history") or []
    recent = history[-limit:] if len(history) > limit else history
    if not recent:
        return "No recent leave history."

    lines = []
    for h in reversed(recent):
        lines.append(
            f"  - {h.get('start_date', '')} to {h.get('end_date', '')} "
            f"({h.get('leave_type', '')}, {h.get('days', 0)} days) [{h.get('status', '')}]"
        )
    return "\n".join(lines) if lines else "No recent leave history."


def send_manager_email_node(state: LeaveRequestState) -> LeaveRequestState:
    """
    Build and send email to manager with leave context and two response methods:
    - reply to email (primary)
    - API curl override
    """
    request_id = state.get("request_id")
    manager_email = state.get("manager_email")
    employee = state.get("employee")

    if not request_id or not manager_email or not employee:
        return {**state, "manager_email_sent": False, "step": "email_failed"}

    leave_type = state.get("leave_type", "")
    start = state.get("start_date", "")
    end = state.get("end_date", "")
    reason = state.get("reason", "") or "No reason provided."

    annual_remaining = employee.get("annual_leave_entitlement", 0) - employee.get("annual_leave_used", 0)
    sick_balance = employee.get("sick_leave_balance", 0)

    if leave_type == "annual":
        balance_line = (
            f"Annual leave remaining: {annual_remaining} days "
            f"(this request uses days in the given range). Sick leave balance: {sick_balance} days."
        )
    elif leave_type == "sick":
        balance_line = f"Sick leave balance: {sick_balance} days. Annual leave remaining: {annual_remaining} days."
    else:
        balance_line = f"Annual leave remaining: {annual_remaining} days. Sick leave balance: {sick_balance} days."

    recent = _recent_history_summary(employee, 3)
    subject = f"Leave Request Approval: {employee.get('name')} ({state.get('employee_id')}) - {start} to {end}"

    base_url = os.getenv("LEAVE_BASE_URL", "http://localhost:9999").rstrip("/")
    body = f"""Leave request requires your approval.

Employee: {employee.get('name')} (ID: {state.get('employee_id')})
Department: {employee.get('department')}
Leave type: {leave_type}
Date range: {start} to {end}
Reason: {reason}

Current balance:
{balance_line}

Recent leave history (last 3):
{recent}

---
Request ID: {request_id}

HOW TO RESPOND (choose one):

Option 1 - Reply to this email (primary)
Reply with both fields so the system can identify the exact request:
Request ID: {request_id}
Decision: APPROVE or REJECT
Optional Comment: your note

Examples:
Request ID: {request_id}
Decision: APPROVE
Comment: Approved

Request ID: {request_id}
Decision: REJECT
Comment: Peak period

Option 2 - Use the API (override)
APPROVE:
curl -X POST "{base_url}/leave/manager_reply" \\
  -H "Content-Type: application/json" \\
  -d '{{"request_id": "{request_id}", "decision": "APPROVE", "comment": "Optional comment"}}'

REJECT:
curl -X POST "{base_url}/leave/manager_reply" \\
  -H "Content-Type: application/json" \\
  -d '{{"request_id": "{request_id}", "decision": "REJECT", "comment": "Optional reason"}}'
"""

    success, message = send_leave_email(manager_email, subject, body)
    if success:
        print("[Leave Workflow] Email sent to manager: " + manager_email)
        return {**state, "manager_email_sent": True, "step": "pending_manager"}
    else:
        print("[Leave Workflow] ERROR: Failed to send email to manager: " + manager_email + " | " + message)
        return {**state, "manager_email_sent": False, "step": "email_failed"}
