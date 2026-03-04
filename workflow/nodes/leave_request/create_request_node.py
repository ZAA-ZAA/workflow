"""Create leave request record and store with PENDING_MANAGER status."""

import time

from app.leave_request_db import add_leave_request, get_leave_request, get_next_request_id
from .state import LeaveRequestState


def _days_between(start: str, end: str) -> int:
    from datetime import datetime
    try:
        s = datetime.strptime(start.strip()[:10], "%Y-%m-%d")
        e = datetime.strptime(end.strip()[:10], "%Y-%m-%d")
        return max(0, (e - s).days + 1)
    except Exception:
        return 0


def create_request_node(state: LeaveRequestState) -> LeaveRequestState:
    """
    Create a new leave request record and save to JSON. Sets request_id and manager_email.
    """
    employee = state.get("employee")
    if not employee:
        return {**state, "step": "create_failed"}

    # Build a collision-resistant numeric request id so old inbox replies
    # cannot accidentally match newly created requests after restarts.
    request_id = ""
    for _ in range(5):
        seq = get_next_request_id()
        candidate = f"LR-{int(time.time())}{seq:04d}"
        if not get_leave_request(candidate):
            request_id = candidate
            break
    if not request_id:
        return {**state, "step": "create_failed"}
    days = _days_between(state.get("start_date", ""), state.get("end_date", ""))

    record = {
        "request_id": request_id,
        "employee_id": state.get("employee_id"),
        "employee_name": employee.get("name"),
        "employee_email": employee.get("email"),
        "manager_email": employee.get("manager_email"),
        "leave_type": state.get("leave_type"),
        "start_date": state.get("start_date"),
        "end_date": state.get("end_date"),
        "reason": state.get("reason"),
        "days": days,
        "status": "PENDING_MANAGER",
        "manager_decision": None,
        "manager_comment": None,
    }
    add_leave_request(record)

    return {
        **state,
        "request_id": request_id,
        "manager_email": employee.get("manager_email"),
        "step": "request_created",
    }
