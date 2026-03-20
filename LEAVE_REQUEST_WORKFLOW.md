# Leave Request Approval Workflow

This document explains **only** the Leave Request workflow in this project:

- How the workflow is structured
- Which files are involved
- How Gmail + AI are used for requests and approvals
- How to run and test everything with `curl`

It is designed to be **beginner-friendly** and match your existing math workflow style.

---

## 1. High-level overview

The leave workflow automates this process:

1. **Employee submits a leave request** (via Gmail email or REST API).
2. **System validates** the request and checks **leave balances**.
3. **System creates a leave record** in a JSON "database".
4. **System emails the manager** with full details and two response options:
   - Reply to the email (primary)
   - Use a `curl` API call (override)
5. **Manager decision is processed** (via Gmail intake or API).
6. **System updates balances and history** and then **emails the employee** with the result.

Everything is implemented as a **LangGraph-like linear workflow** with small, focused nodes.

---

## 2. Files and directories

### Core workflow code

- `workflow/leave_request_workflow.py`
  - `run_request_flow(...)`
  - `run_request_flow_with_wait(...)`
  - `run_manager_reply_flow(...)`

- `workflow/nodes/leave_request/`
  - `state.py` – defines `LeaveRequestState` (shared state between nodes)
  - `input_validate_node.py` – validates input + loads employee
  - `check_balance_node.py` – checks annual/sick leave balance
  - `create_request_node.py` – creates JSON record with `PENDING_MANAGER`
  - `send_manager_email_node.py` – emails manager with context + instructions
  - `apply_decision_node.py` – applies APPROVE/REJECT, updates balances/history
  - `notify_employee_node.py` – emails employee with result

### Mock database + email helpers

- `app/leave_request_db.py`
  - JSON "DB" under `data/` (no real database)
  - Functions: `get_employee`, `get_leave_request`, `add_leave_request`, `update_leave_request`, etc.

- `data/employees.json`
  - Sample employees with:
    - `employee_id`, `name`, `email`, `manager_email`, `department`
    - `annual_leave_entitlement`, `annual_leave_used`, `sick_leave_balance`
    - `leave_history` (list of past leaves)

- `data/leave_requests.json`
  - Stores leave requests:
    - `request_id`, `employee_id`, `employee_name`, emails
    - `leave_type`, `start_date`, `end_date`, `days`, `status`
    - `manager_decision`, `manager_comment`

- `app/leave_request_email.py`
  - `send_leave_email(to, subject, body)` – logs emails and, if Gmail is configured, sends via SMTP.

### Gmail + AI integration

- `app/leave_request_gmail_inbox.py`
  - Low-level Gmail IMAP helper
  - Reads messages from the `GMAIL_FROM` inbox

- `app/leave_request_reply_parser.py`
  - Uses OpenAI (`OPENAI_API_KEY`) to **parse emails into structured JSON**:
    - `parse_leave_request_email_with_ai(...)` – employee requests
    - `parse_manager_reply_with_ai(...)` – manager decisions

- `app/leave_request_gmail_processor.py`
  - High-level **Gmail intake** logic:
    - `process_employee_leave_request_emails()` – emails from employees
    - `process_manager_reply_emails()` – emails from managers
    - `process_all_leave_emails()` – does both

### API endpoints (FastAPI)

Defined in `main.py`:

- `POST /leave/request` – create a leave request via JSON
- `POST /leave/manager_reply` – manager decision via JSON
- `POST /leave/gmail/process` – one-shot Gmail processing
- `GET /leave/gmail/poller/status` – background poller status
- `POST /leave/gmail/poller/start` – start background poller
- `POST /leave/gmail/poller/stop` – stop background poller
- `GET /leave/status/{request_id}` – check leave status
- `GET /leave/employees/{employee_id}` – view balances + history

---

## 3. Workflow steps and nodes

### 3.1 `run_request_flow(...)` – create request and email manager

Called by:

- `POST /leave/request` (with `wait=false`, default)
- Gmail intake (employee request emails)

Steps:

1. **`input_validate_node`**
   - Checks required fields:
     - `employee_id`, `leave_type`, `start_date`, `end_date`
   - Validates `leave_type` is `annual` or `sick`.
   - Loads the employee from `data/employees.json`.
   - If invalid → returns status like `VALIDATION_FAILED` or `EMPLOYEE_NOT_FOUND`.

2. **`check_balance_node`**
   - Parses dates and computes `days` in the range (inclusive).
   - For `annual`:
     - Uses `annual_leave_entitlement - annual_leave_used` for remaining days.
   - For `sick`:
     - Uses `sick_leave_balance` for remaining days.
   - Returns:
     - `balance_ok=True` and `step='balance_ok'` if enough
     - Or `INSUFFICIENT_BALANCE`, `INVALID_DATES`, or `INVALID_LEAVE_TYPE`.

3. **`create_request_node`**
   - Creates a unique `request_id` like `LR-<timestamp><sequence>`.
   - Writes the record to `data/leave_requests.json` with `status='PENDING_MANAGER'`.

4. **`send_manager_email_node`**
   - Builds a detailed email to `manager_email`:
     - Employee name/ID, department
     - Leave type, dates, reason
     - Current balances and recent history (last 2–3 leaves)
     - `Request ID: LR-xxxx`
     - **Two response options:**
       - **Option 1 – Reply to this email** with:
         - `Request ID: LR-xxxx`
         - `Decision: APPROVE or REJECT`
         - `Optional Comment: ...`
       - **Option 2 – Use the API** (curl to `POST /leave/manager_reply`).
   - Uses `send_leave_email` (logs to console and optionally sends via Gmail).
   - On success → `step='pending_manager'` and `status='PENDING_MANAGER'`.

Return value (on success):

```json
{
  "request_id": "LR-...",
  "status": "PENDING_MANAGER",
  "message": "Request created; manager has been emailed. Awaiting manager reply via email or POST /leave/manager_reply."
}
```

### 3.2 `run_request_flow_with_wait(...)` – optional blocking wait

- Called by `POST /leave/request?wait=true`.
- Internally calls `run_request_flow(...)` **first**.
- Then enters a loop:
  - Every `poll_interval_seconds` (default 15s):
    - Reloads the request from JSON.
    - If `status != PENDING_MANAGER` → returns final result.
    - Otherwise prints `Still waiting for manager reply...`.
  - If `timeout_seconds` is `None`, waits indefinitely.
  - If `timeout_seconds` is set and exceeded → returns with message `Still waiting for manager decision.` and the current request record.

This is mostly for **experiments**; in practice you’ll usually use the non-blocking default and rely on Gmail + the manager API.

### 3.3 `run_manager_reply_flow(...)` – apply decision

Called by:

- `POST /leave/manager_reply` (curl or client)
- Gmail intake (manager reply emails)

Steps:

1. Validates that the request exists and is still `PENDING_MANAGER`.
2. Validates `decision` is `APPROVE` or `REJECT`.
3. Builds a `LeaveRequestState` with that decision and calls:
   - `apply_decision_node` → updates request record + balances/history
   - `notify_employee_node` → emails the employee
4. Returns:

```json
{
  "request_id": "LR-...",
  "status": "APPROVED" or "REJECTED",
  "message": "Decision applied and employee notified."
}
```

---

## 4. Gmail + AI flows

### 4.1 Employee request via Gmail

File: `app/leave_request_gmail_processor.py` → `process_employee_leave_request_emails()`

1. Reads messages from the `GMAIL_FROM` inbox via `fetch_inbox_messages(...)`.
2. Filters by **known employee emails** (`data/employees.json`).
3. Uses `parse_leave_request_email_with_ai(...)` to extract:
   - `employee_id` or `employee_name`
   - `leave_type` (annual/sick)
   - `start_date`, `end_date`
   - `reason`
4. Resolves the employee by ID, email, or name.
5. Calls `run_request_flow(...)`.
6. Sends an email back to the employee:
   - Success → "Leave Request Submitted" with the new `request_id`.
   - Error → "Leave Request Not Processed" with missing/invalid fields.

You can trigger this via:

```bash
curl -X POST "http://localhost:9999/leave/gmail/process?start_loop=false"
```

Or let the background poller run automatically on app startup.

### 4.2 Manager decision via Gmail

Same file: `process_manager_reply_emails()`

1. Reads messages from `GMAIL_FROM` inbox.
2. Filters by **known manager emails** (`manager_email` fields in employees).
3. Looks for messages that clearly contain decision intent (`request id`, `approve`, `reject`, etc.).
4. Uses `parse_manager_reply_with_ai(...)` to extract:
   - `request_id`
   - `decision` (APPROVE/REJECT)
   - `comment`
5. Ensures:
   - The request exists.
   - The sender matches the assigned `manager_email` for that request.
6. Calls `run_manager_reply_flow(...)`.
7. Sends an email back to the manager:
   - Success → "Manager Decision Processed".
   - Error → "Manager Decision Not Processed" with reason.

You can process a batch of manager replies via:

```bash
curl -X POST "http://localhost:9999/leave/gmail/process?start_loop=false"
```

### 4.3 Background poller

File: `main.py`

On startup the app calls `_start_gmail_intake_poller()` (unless disabled by env). The poller:

- Periodically calls `process_all_leave_emails()`.
- Logs summaries like:
  - `[Leave Gmail] Loop running. Interval: 20s`
  - `[Leave Gmail] Poll summary: {"employee_requests": {...}, "manager_replies": {...}}`

Control endpoints:

- Start/force: `POST /leave/gmail/poller/start`
- Status: `GET /leave/gmail/poller/status`
- Stop: `POST /leave/gmail/poller/stop`

Env variables (see `.env.example`):

- `ENABLE_GMAIL_LEAVE_INTAKE=1` – enable/disable background poller
- `LEAVE_GMAIL_POLL_SECONDS=20` – poll interval
- `LEAVE_GMAIL_SKIP_EXISTING_ON_FIRST_RUN=1` – skip old inbox history on first run
- `LEAVE_GMAIL_IMAP_TIMEOUT_SECONDS=20` – IMAP timeout
- `LEAVE_ALLOW_SHARED_EMPLOYEE_EMAILS=0` – test mode for shared inboxes

---

## 5. Email formats (what to actually type)

### 5.1 Employee leave request email

Send an email **from the employee’s email address** (matching `data/employees.json`) to `GMAIL_FROM`.

**Simple template (recommended):**

```text
Subject: Leave request for March 10 to March 12

Employee ID: E001
Leave Type: annual
Start Date: 2026-03-10
End Date: 2026-03-12
Reason: Family trip
```

**More natural language (AI parser friendly):**

```text
Subject: Need leave next week

Hi, this is Zoen Aldueza (E001). I want to file annual leave from 2026-03-10 to 2026-03-12 for a family trip. Thank you.
```

### 5.2 Manager decision email

Reply to the manager notification email (so the subject already includes context) and include:

```text
Request ID: LR-12345678
Decision: APPROVE or REJECT
Optional Comment: short note here
```

Examples:

```text
Request ID: LR-12345678
Decision: APPROVE
Comment: Approved
```

```text
Request ID: LR-98765432
Decision: REJECT
Comment: Peak period, please move dates
```

The AI parser is also tolerant of more natural phrasing, as long as `LR-xxxx` and clear approval/rejection intent are present somewhere in the subject/body.

---

## 6. API endpoints and curl examples

Assuming Docker on port **9999**:

### 6.1 Create a leave request (JSON)

```bash
curl -X POST "http://localhost:9999/leave/request" \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": "E001",
    "leave_type": "annual",
    "start_date": "2025-03-01",
    "end_date": "2025-03-03",
    "reason": "Family trip"
  }'
```

**Response (example):**

```json
{
  "request_id": "LR-...",
  "status": "PENDING_MANAGER",
  "message": "Request created; manager has been emailed. Awaiting manager reply via email or POST /leave/manager_reply."
}
```

**Blocking version:**

```bash
curl -X POST "http://localhost:9999/leave/request?wait=true" \
  -H "Content-Type: application/json" \
  -d '{"employee_id":"E001","leave_type":"annual","start_date":"2025-03-01","end_date":"2025-03-03","reason":"Trip"}'
```

### 6.2 Manager reply via API

```bash
curl -X POST "http://localhost:9999/leave/manager_reply" \
  -H "Content-Type: application/json" \
  -d '{"request_id": "LR-...", "decision": "APPROVE", "comment": "Approved"}'
```

### 6.3 Process Gmail inbox once

```bash
curl -X POST "http://localhost:9999/leave/gmail/process?start_loop=false"
```

### 6.4 Check request status

```bash
curl "http://localhost:9999/leave/status/LR-..."
```

### 6.5 View employee balances and history

```bash
curl "http://localhost:9999/leave/employees/E001"
```

---

## 7. Environment variables recap

In `.env` (see `.env.example`):

- `OPENAI_API_KEY` – required for all AI parsing (Zoey, leave parsers).
- `GMAIL_FROM` – Gmail address used to send and read leave emails.
- `GMAIL_APP_PASSWORD` – Gmail App Password (not your normal password).
- `SEND_LEAVE_EMAILS_VIA_GMAIL=1` – actually send via Gmail; otherwise just log.
- `LEAVE_BASE_URL` – base URL used in manager email curl examples (default `http://localhost:9999`).
- `ENABLE_GMAIL_LEAVE_INTAKE` – enable background Gmail poller.
- `LEAVE_GMAIL_POLL_SECONDS` – poll interval.
- `LEAVE_GMAIL_SKIP_EXISTING_ON_FIRST_RUN` – skip old inbox mail.
- `LEAVE_GMAIL_IMAP_TIMEOUT_SECONDS` – IMAP timeout.
- `LEAVE_ALLOW_SHARED_EMPLOYEE_EMAILS` – test mode for shared inboxes.

---

## 8. Troubleshooting tips

- **No emails are sent**
  - Check console for `[Leave Email]` logs.
  - Make sure `SEND_LEAVE_EMAILS_VIA_GMAIL=1`, `GMAIL_FROM`, and `GMAIL_APP_PASSWORD` are set.
  - Confirm App Password is valid and IMAP/SMTP access is allowed.

- **Employee email not processed**
  - Check `/leave/gmail/process` response for `errors`.
  - Verify sender address matches `data/employees.json`.
  - Check that required fields are present (`leave_type`, `start_date`, `end_date`).

- **Manager email not processed**
  - Ensure `Request ID: LR-xxxx` appears in the email.
  - Ensure the email is sent **from the manager_email** configured for that employee.
  - Check `/leave/gmail/process` or poller logs for parse errors.

- **Status stays `PENDING_MANAGER`**
  - Use `GET /leave/status/{request_id}` to inspect the record.
  - Verify that manager replies really reference that `request_id`.
  - Use API override: `POST /leave/manager_reply`.

---

This markdown file documents everything about your **Leave Request Approval Workflow** without touching your math or converter workflows. It is safe to ship with your repo for demos or academic submissions.

