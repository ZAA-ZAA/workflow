"""Check employee leave balance for the requested leave type and days."""

from datetime import datetime

from .state import LeaveRequestState


def _parse_date(s: str) -> datetime | None:
    try:
        return datetime.strptime(s.strip()[:10], "%Y-%m-%d")
    except Exception:
        return None


def check_balance_node(state: LeaveRequestState) -> LeaveRequestState:
    """
    Check if employee has enough balance for leave_type and date range.
    Sets balance_ok and step (insufficient_balance if not enough).
    """
    employee = state.get("employee")
    leave_type = state.get("leave_type", "")
    start_date_s = state.get("start_date", "")
    end_date_s = state.get("end_date", "")

    if not employee:
        return {**state, "balance_ok": False, "step": "insufficient_balance"}

    start = _parse_date(start_date_s)
    end = _parse_date(end_date_s)
    if not start or not end or end < start:
        return {**state, "balance_ok": False, "step": "invalid_dates"}

    days = (end - start).days + 1
    if days <= 0:
        return {**state, "balance_ok": False, "step": "invalid_dates"}

    balance_ok = False
    if leave_type == "annual":
        entitlement = employee.get("annual_leave_entitlement", 0)
        used = employee.get("annual_leave_used", 0)
        remaining = entitlement - used
        balance_ok = remaining >= days
    elif leave_type == "sick":
        remaining = employee.get("sick_leave_balance", 0)
        balance_ok = remaining >= days
    else:
        return {**state, "balance_ok": False, "step": "invalid_leave_type"}

    step = "balance_ok" if balance_ok else "insufficient_balance"
    return {
        **state,
        "balance_ok": balance_ok,
        "step": step,
    }
