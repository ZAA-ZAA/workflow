import json
import os
import threading
import time

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from openai import OpenAI

from agents import execute_tool_by_name, get_tool_specs
from app.agents.zoey_agent import create_zoey_agent
from app.email_task_store import list_tasks, mark_task_done
from app.leave_request_db import get_employee, get_leave_request
from app.leave_request_gmail_processor import process_all_leave_emails
from workflow.basic_workflow import run_workflow
from workflow.email_task_workflow import run_email_task_extractor_flow, run_email_task_gmail_poll
from workflow.leave_request_workflow import run_manager_reply_flow, run_request_flow, run_request_flow_with_wait

app = FastAPI()
_GMAIL_POLLER_STARTED = False
_GMAIL_POLLER_INTERVAL_SECONDS = 20
_GMAIL_POLLER_THREAD: threading.Thread | None = None
_GMAIL_POLLER_STOP_EVENT = threading.Event()
_GMAIL_POLLER_LAST_SUMMARY: dict | None = None
_GMAIL_POLLER_LAST_RUN_AT: float | None = None
_GMAIL_POLLER_CYCLE_COUNT: int = 0


class ChatRequest(BaseModel):
    prompt: str


class ZoeyChatRequest(BaseModel):
    prompt: str
    model: str | None = None


class MathWorkflowRequest(BaseModel):
    num1: float
    num2: float


class LeaveRequestRequest(BaseModel):
    employee_id: str
    leave_type: str
    start_date: str
    end_date: str
    reason: str = ""


class ManagerReplyRequest(BaseModel):
    request_id: str
    decision: str
    comment: str = ""


class EmailTaskExtractRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    subject: str = ""
    from_email: str = Field(alias="from")
    body: str = ""
    received_at: str | None = None


class EmailTaskMarkDoneRequest(BaseModel):
    task_id: str


class EmailTaskGmailPollRequest(BaseModel):
    max_results: int = 10
    query: str | None = None
    allow_interactive_auth: bool = False


def _get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # Fail fast with a helpful error when the key is missing.
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)


def _gmail_intake_enabled() -> bool:
    return os.getenv("ENABLE_GMAIL_LEAVE_INTAKE", "1").strip().lower() in ("1", "true", "yes")


def _gmail_intake_loop() -> None:
    global _GMAIL_POLLER_LAST_SUMMARY, _GMAIL_POLLER_LAST_RUN_AT, _GMAIL_POLLER_CYCLE_COUNT
    print(f"[Leave Gmail] Loop running. Interval: {_GMAIL_POLLER_INTERVAL_SECONDS}s")
    while not _GMAIL_POLLER_STOP_EVENT.is_set():
        try:
            _GMAIL_POLLER_CYCLE_COUNT += 1
            summary = process_all_leave_emails()
            _GMAIL_POLLER_LAST_SUMMARY = summary
            _GMAIL_POLLER_LAST_RUN_AT = time.time()
            req = summary.get("employee_requests", {})
            rep = summary.get("manager_replies", {})
            if any(
                [
                    req.get("processed", 0),
                    req.get("created", 0),
                    req.get("errors", 0),
                    rep.get("processed", 0),
                    rep.get("applied", 0),
                    rep.get("errors", 0),
                ]
            ):
                print(f"[Leave Gmail] Poll summary: {summary}")
            else:
                print(f"[Leave Gmail] Poll tick #{_GMAIL_POLLER_CYCLE_COUNT}: no new leave emails")
        except Exception as exc:
            print(f"[Leave Gmail] Poller error: {exc}")
        _GMAIL_POLLER_STOP_EVENT.wait(_GMAIL_POLLER_INTERVAL_SECONDS)
    print("[Leave Gmail] Loop stopped.")


@app.on_event("startup")
def start_gmail_intake_poller():
    # Auto-start continuous polling when app starts.
    started = _start_gmail_intake_poller()
    print(f"[Leave Gmail] Startup poller state: {started}")


def _start_gmail_intake_poller(interval_seconds: int | None = None, force: bool = False) -> dict:
    global _GMAIL_POLLER_STARTED, _GMAIL_POLLER_INTERVAL_SECONDS, _GMAIL_POLLER_THREAD
    if not _gmail_intake_enabled() and not force:
        return {"started": False, "enabled": False, "message": "Gmail intake disabled by env"}
    if interval_seconds is not None and interval_seconds > 0:
        _GMAIL_POLLER_INTERVAL_SECONDS = int(interval_seconds)
    if _GMAIL_POLLER_STARTED:
        return {
            "started": True,
            "enabled": _gmail_intake_enabled(),
            "interval_seconds": _GMAIL_POLLER_INTERVAL_SECONDS,
            "message": "Gmail poller already running",
        }
    _GMAIL_POLLER_STOP_EVENT.clear()
    thread = threading.Thread(target=_gmail_intake_loop, daemon=True, name="leave-gmail-poller")
    thread.start()
    _GMAIL_POLLER_THREAD = thread
    _GMAIL_POLLER_STARTED = True
    return {
        "started": True,
        "enabled": _gmail_intake_enabled(),
        "interval_seconds": _GMAIL_POLLER_INTERVAL_SECONDS,
        "message": "Gmail poller started",
    }


def _stop_gmail_intake_poller() -> dict:
    global _GMAIL_POLLER_STARTED, _GMAIL_POLLER_THREAD
    if not _GMAIL_POLLER_STARTED:
        return {"stopped": False, "message": "Gmail poller is not running"}
    _GMAIL_POLLER_STOP_EVENT.set()
    _GMAIL_POLLER_STARTED = False
    _GMAIL_POLLER_THREAD = None
    return {"stopped": True, "message": "Gmail poller stopping"}


@app.get("/health")
def health_check():
    """Return a simple health status response."""
    return {"status": "ok"}


@app.post("/agent/chat")
def chat(request: ChatRequest):
    """Minimal chat endpoint that forwards the prompt to OpenAI."""
    client = _get_openai_client()
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Swap to another model if preferred.
            messages=[{"role": "user", "content": request.prompt}],
        )
        # Return the first choice text content.
        return {"reply": response.choices[0].message.content}
    except Exception as exc:  # Broad catch to relay useful error info.
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/agent/zoey/chat")
def zoey_chat(request: ZoeyChatRequest):
    """Chat with the Zoey agent, which can call math tools."""
    agent = create_zoey_agent(model_override=request.model)
    client = _get_openai_client()

    messages = [
        {"role": "system", "content": agent.instructions},
        {"role": "user", "content": request.prompt},
    ]
    tools = get_tool_specs(agent.tools)
    model = agent.model or "gpt-4o-mini"

    try:
        first = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        first_message = first.choices[0].message

        # If the model decides to invoke a tool, execute and follow up.
        if first_message.tool_calls:
            messages.append(
                {
                    "role": "assistant",
                    "content": first_message.content or "",
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": call.function.name,
                                "arguments": call.function.arguments,
                            },
                        }
                        for call in first_message.tool_calls
                    ],
                }
            )

            for call in first_message.tool_calls:
                args = json.loads(call.function.arguments or "{}")
                result = execute_tool_by_name(agent.tools, call.function.name, args)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": str(result),
                    }
                )

            follow_up = client.chat.completions.create(
                model=model,
                messages=messages,
            )
            return {"reply": follow_up.choices[0].message.content}

        # No tool use; return the first reply.
        return {"reply": first_message.content}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/leave/request")
def leave_request(request: LeaveRequestRequest, wait: bool = False):
    """
    API override path for creating a leave request directly via JSON.
    Default behavior is non-blocking and returns PENDING_MANAGER immediately.
    Use ?wait=true if you explicitly want this HTTP call to block until a
    manager decision is observed.
    """
    if wait:
        result = run_request_flow_with_wait(
            employee_id=request.employee_id,
            leave_type=request.leave_type,
            start_date=request.start_date,
            end_date=request.end_date,
            reason=request.reason,
        )
    else:
        result = run_request_flow(
            employee_id=request.employee_id,
            leave_type=request.leave_type,
            start_date=request.start_date,
            end_date=request.end_date,
            reason=request.reason,
        )
    if result.get("status") not in ("PENDING_MANAGER", "APPROVED", "REJECTED") and result.get("request_id") is None:
        raise HTTPException(status_code=400, detail=result.get("message", "Leave request failed"))
    return result


@app.post("/leave/gmail/process")
def leave_gmail_process():
    """
    One-shot Gmail processing cycle (employee requests + manager replies).
    """
    summary = process_all_leave_emails()
    return {
        "poller": {
            "started": _GMAIL_POLLER_STARTED,
            "enabled": _gmail_intake_enabled(),
            "interval_seconds": _GMAIL_POLLER_INTERVAL_SECONDS,
            "message": "one-shot completed",
        },
        "summary": summary,
    }


@app.get("/leave/gmail/poller/status")
def leave_gmail_poller_status():
    """
    Returns Gmail poller runtime status so operators can verify auto mode.
    """
    return {
        "enabled_by_env": _gmail_intake_enabled(),
        "running": _GMAIL_POLLER_STARTED,
        "interval_seconds": _GMAIL_POLLER_INTERVAL_SECONDS,
        "cycle_count": _GMAIL_POLLER_CYCLE_COUNT,
        "last_run_at_unix": _GMAIL_POLLER_LAST_RUN_AT,
        "last_summary": _GMAIL_POLLER_LAST_SUMMARY,
    }


@app.post("/leave/gmail/poller/start")
def leave_gmail_poller_start(force: bool = False, interval_seconds: int | None = None):
    """
    Start Gmail background poller manually.
    Use force=true to start even if ENABLE_GMAIL_LEAVE_INTAKE is off.
    """
    return _start_gmail_intake_poller(interval_seconds=interval_seconds, force=force)


@app.post("/leave/gmail/poller/stop")
def leave_gmail_poller_stop():
    """Stop Gmail background poller."""
    return _stop_gmail_intake_poller()


@app.post("/leave/manager_reply")
def leave_manager_reply(request: ManagerReplyRequest):
    """
    Manager submits APPROVE or REJECT for a request. Workflow then updates
    balance (if approved), records decision, and emails the employee.
    """
    result = run_manager_reply_flow(
        request_id=request.request_id,
        decision=request.decision,
        comment=request.comment,
    )
    if result.get("status") in ("NOT_FOUND", "INVALID_DECISION", "ALREADY_PROCESSED"):
        raise HTTPException(status_code=400, detail=result.get("message", "Invalid reply"))
    return result


@app.get("/leave/status/{request_id}")
def leave_status(request_id: str):
    """Return the current status and details of a leave request."""
    req = get_leave_request(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    return req


@app.get("/leave/employees/{employee_id}")
def leave_employee(employee_id: str):
    """Return employee balances and recent leave history."""
    emp = get_employee(employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    history = emp.get("leave_history") or []
    return {
        "employee_id": emp.get("employee_id"),
        "name": emp.get("name"),
        "email": emp.get("email"),
        "department": emp.get("department"),
        "annual_leave_entitlement": emp.get("annual_leave_entitlement"),
        "annual_leave_used": emp.get("annual_leave_used"),
        "annual_leave_remaining": (emp.get("annual_leave_entitlement") or 0) - (emp.get("annual_leave_used") or 0),
        "sick_leave_balance": emp.get("sick_leave_balance"),
        "leave_history": history[-10:],
    }


@app.post("/workflow/math")
def math_workflow(request: MathWorkflowRequest):
    """
    Execute the basic math workflow with two numbers.
    
    This workflow performs all 4 basic math operations:
    - Addition
    - Subtraction
    - Multiplication
    - Division (with zero handling)
    """
    try:
        # Run the workflow
        result = run_workflow(request.num1, request.num2)
        
        # Return the results
        return {
            "num1": result["num1"],
            "num2": result["num2"],
            "results": {
                "addition": result["add_result"],
                "subtraction": result["subtract_result"],
                "multiplication": result["multiply_result"],
                "division": result["divide_result"],
            },
            "status": result["step"]
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/email-task/extract")
def email_task_extract(request: EmailTaskExtractRequest):
    """
    Mode A (simulated Gmail): send subject/from/body manually and extract tasks.
    """
    result = run_email_task_extractor_flow(
        from_email=request.from_email,
        subject=request.subject,
        body=request.body,
        received_at=request.received_at,
    )
    if result.get("status") == "VALIDATION_FAILED":
        raise HTTPException(status_code=400, detail=result.get("errors", ["Invalid input"]))
    return result


@app.get("/email-task/tasks")
def email_task_list(status: str | None = None):
    """
    List tasks from mock storage (optionally filtered by status).
    """
    rows = list_tasks(status=status)
    return {
        "count": len(rows),
        "tasks": rows,
    }


@app.post("/email-task/mark_done")
def email_task_mark_done(request: EmailTaskMarkDoneRequest):
    """
    Mark one extracted task as DONE.
    """
    updated = mark_task_done(request.task_id)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Task not found: {request.task_id}")
    return {"status": "DONE", "task": updated}


@app.post("/email-task/gmail/poll")
def email_task_gmail_poll(request: EmailTaskGmailPollRequest):
    """
    Mode B (optional): poll Gmail API for new messages and extract tasks.
    """
    result = run_email_task_gmail_poll(
        max_results=request.max_results,
        query=request.query,
        allow_interactive_auth=request.allow_interactive_auth,
    )
    if result.get("status") == "GMAIL_NOT_READY":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result
