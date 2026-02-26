"""
Mock database helpers for the Leave Request Approval Workflow.
Uses JSON files under data/ for a beginner-friendly, no-DB setup.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
EMPLOYEES_FILE = DATA_DIR / "employees.json"
LEAVE_REQUESTS_FILE = DATA_DIR / "leave_requests.json"


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: Any) -> None:
    _ensure_data_dir()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_employees_data() -> dict:
    """Return full employees data: { employees: [...], ... }."""
    return _read_json(EMPLOYEES_FILE, {"employees": []})


def get_employees() -> list[dict]:
    """Return list of all employees."""
    data = get_employees_data()
    return data.get("employees", [])


def get_employee(employee_id: str) -> dict | None:
    """Return one employee by employee_id or None."""
    for emp in get_employees():
        if emp.get("employee_id") == employee_id:
            return emp
    return None


def save_employee(employee_id: str, updates: dict) -> None:
    """Update one employee by employee_id. Merges updates into existing record."""
    data = get_employees_data()
    employees = data.get("employees", [])
    for i, emp in enumerate(employees):
        if emp.get("employee_id") == employee_id:
            employees[i] = {**emp, **updates}
            break
    else:
        return
    data["employees"] = employees
    _write_json(EMPLOYEES_FILE, data)


def get_leave_requests_data() -> dict:
    """Return full leave requests store: { leave_requests: [...], next_request_id: n }."""
    return _read_json(
        LEAVE_REQUESTS_FILE,
        {"leave_requests": [], "next_request_id": 1},
    )


def get_leave_requests() -> list[dict]:
    """Return list of all leave requests."""
    data = get_leave_requests_data()
    return data.get("leave_requests", [])


def get_leave_request(request_id: str) -> dict | None:
    """Return one leave request by request_id or None."""
    for req in get_leave_requests():
        if req.get("request_id") == request_id:
            return req
    return None


def add_leave_request(record: dict) -> None:
    """Append a new leave request."""
    data = get_leave_requests_data()
    requests = data.get("leave_requests", [])
    requests.append(record)
    data["leave_requests"] = requests
    _write_json(LEAVE_REQUESTS_FILE, data)


def update_leave_request(request_id: str, updates: dict) -> None:
    """Update one leave request by request_id. Merges updates."""
    data = get_leave_requests_data()
    requests = data.get("leave_requests", [])
    for i, req in enumerate(requests):
        if req.get("request_id") == request_id:
            requests[i] = {**req, **updates}
            break
    else:
        return
    data["leave_requests"] = requests
    _write_json(LEAVE_REQUESTS_FILE, data)


def get_next_request_id() -> int:
    """Return current next_request_id and increment it for next use."""
    data = get_leave_requests_data()
    n = data.get("next_request_id", 1)
    data["next_request_id"] = n + 1
    _write_json(LEAVE_REQUESTS_FILE, data)
    return n
