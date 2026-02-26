"""State definition for leave request approval workflow."""

from typing import Optional, TypedDict


class LeaveRequestState(TypedDict):
    """State passed between leave request nodes."""

    employee_id: str
    leave_type: str
    start_date: str
    end_date: str
    reason: str
    employee: Optional[dict]
    balance_ok: bool
    request_id: Optional[str]
    manager_email: Optional[str]
    manager_email_sent: bool
    manager_decision: Optional[str]
    manager_comment: Optional[str]
    step: str
