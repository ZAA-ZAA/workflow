"""
Apply manager decision: on APPROVE deduct balance and append to leave_history;
on REJECT just update request. Updates JSON store.
"""

from app.leave_request_db import get_employee, get_leave_request, save_employee, update_leave_request
from .state import LeaveRequestState


def _days_between(start: str, end: str) -> int:
    from datetime import datetime
    try:
        s = datetime.strptime(start.strip()[:10], "%Y-%m-%d")
        e = datetime.strptime(end.strip()[:10], "%Y-%m-%d")
        return max(0, (e - s).days + 1)
    except Exception:
        return 0


def apply_decision_node(state: LeaveRequestState) -> LeaveRequestState:
    """
    Apply APPROVE or REJECT: update leave request record; on APPROVE deduct
    balance and add to employee leave_history.
    """
    request_id = state.get("request_id")
    decision = (state.get("manager_decision") or "").strip().upper()
    comment = (state.get("manager_comment") or "").strip()

    req = get_leave_request(request_id) if request_id else None
    if not req or req.get("status") != "PENDING_MANAGER":
        return {**state, "step": "decision_failed"}

    if decision not in ("APPROVE", "REJECT"):
        return {**state, "step": "invalid_decision"}

    update_leave_request(request_id, {
        "status": "APPROVED" if decision == "APPROVE" else "REJECTED",
        "manager_decision": decision,
        "manager_comment": comment or None,
    })

    if decision == "APPROVE":
        print("[Leave Workflow] Applying decision: APPROVE (deducting balance, updating history)")
        employee_id = req.get("employee_id")
        emp = get_employee(employee_id) if employee_id else None
        if emp:
            days = _days_between(req.get("start_date", ""), req.get("end_date", ""))
            leave_type = req.get("leave_type", "annual")
            history = list(emp.get("leave_history") or [])
            history.append({
                "request_id": request_id,
                "leave_type": leave_type,
                "start_date": req.get("start_date"),
                "end_date": req.get("end_date"),
                "days": days,
                "status": "APPROVED",
            })
            updates = {"leave_history": history}
            if leave_type == "annual":
                updates["annual_leave_used"] = emp.get("annual_leave_used", 0) + days
            elif leave_type == "sick":
                updates["sick_leave_balance"] = max(0, emp.get("sick_leave_balance", 0) - days)
            save_employee(employee_id, updates)

    else:
        print("[Leave Workflow] Applying decision: REJECT (no balance change)")
    return {
        **state,
        "step": "approved" if decision == "APPROVE" else "rejected",
    }
