"""Validate leave request input and load employee."""

from app.leave_request_db import get_employee
from .state import LeaveRequestState


def input_validate_node(state: LeaveRequestState) -> LeaveRequestState:
    """
    Validate input fields and load employee. Sets employee or fails step.
    """
    employee_id = (state.get("employee_id") or "").strip()
    leave_type = (state.get("leave_type") or "").strip().lower()
    start_date = (state.get("start_date") or "").strip()
    end_date = (state.get("end_date") or "").strip()
    reason = (state.get("reason") or "").strip()

    if not employee_id or not leave_type or not start_date or not end_date:
        return {
            **state,
            "step": "validation_failed",
            "employee": None,
        }

    allowed = ("annual", "sick")
    if leave_type not in allowed:
        return {
            **state,
            "step": "validation_failed",
            "employee": None,
        }

    employee = get_employee(employee_id)
    if not employee:
        return {
            **state,
            "step": "employee_not_found",
            "employee": None,
        }

    return {
        **state,
        "employee_id": employee_id,
        "leave_type": leave_type,
        "start_date": start_date,
        "end_date": end_date,
        "reason": reason,
        "employee": employee,
        "step": "validated",
    }
