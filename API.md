# Math Workflow API

## Leave Workflow Update (March 3, 2026)

The leave workflow now supports two methods for each step:

1. Request creation:
   - Method A (primary): employee sends Gmail email; AI parses details.
   - Method B (override): call `POST /leave/request`.
2. Manager decision:
   - Method A (primary): manager replies by Gmail; AI parses decision.
   - Method B (override): call `POST /leave/manager_reply`.

`POST /leave/request` is non-blocking by default and returns `PENDING_MANAGER`.
Requests stay pending until a valid manager decision is received.

### Gmail intake endpoint

- `POST /leave/gmail/process`
  - Starts continuous Gmail loop (default) and processes inbox immediately.
  - Use `start_loop=false` for one-shot processing only.
- `GET /leave/gmail/poller/status`
  - Check if loop is running and last cycle summary.
- `POST /leave/gmail/poller/start`
  - Start loop explicitly (optional).
- `POST /leave/gmail/poller/stop`
  - Stop loop.

### Gmail background processing

- Enabled when loop is started and `ENABLE_GMAIL_LEAVE_INTAKE=1`.
- Poll interval default: `LEAVE_GMAIL_POLL_SECONDS=20`
- First-run backlog guard: `LEAVE_GMAIL_SKIP_EXISTING_ON_FIRST_RUN=1` (default)
  - Skips historical inbox messages the first time so old emails are not reprocessed.

### Can employees/managers write in normal sentences?

Yes. AI parsing is enabled, so they do not need to follow an exact rigid template.
But these fields must still be present in the text:

- Employee request required details:
  - employee identity (`Employee ID` or identifiable email/name)
  - leave type (`annual` or `sick`)
  - start date (`YYYY-MM-DD`)
  - end date (`YYYY-MM-DD`)
- Manager reply required details:
  - `Request ID` (for example `LR-0001`)
  - decision (`APPROVE` or `REJECT`)

If required details are missing/invalid, the system sends an error email asking for corrections.

The math workflow is now available as a REST API endpoint in the FastAPI application!

## ðŸš€ Quick Start

### 1. Start the Server

**Using Docker (Recommended):**
```bash
docker-compose up
```

**Or locally:**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 2. Test the Endpoint

**Using the test scripts:**
```bash
# Bash script
./test_workflow_api.sh

# Python script
python test_workflow_api.py
```

**Or manually with curl:**
```bash
curl -X POST "http://localhost:8000/workflow/math" \
  -H "Content-Type: application/json" \
  -d '{"num1": 10, "num2": 5}'
```

## ðŸ“¡ API Endpoint

### POST `/workflow/math`

Execute the basic math workflow with two numbers.

**Request Body:**
```json
{
  "num1": 10,
  "num2": 5
}
```

**Parameters:**
- `num1` (float, required): First number
- `num2` (float, required): Second number

**Response:**
```json
{
  "num1": 10,
  "num2": 5,
  "results": {
    "addition": 15.0,
    "subtraction": 5.0,
    "multiplication": 50.0,
    "division": "2.0"
  },
  "status": "completed"
}
```

**Response Fields:**
- `num1`: First input number
- `num2`: Second input number
- `results`: Object containing all calculation results
  - `addition`: Sum of num1 + num2
  - `subtraction`: Difference of num1 - num2
  - `multiplication`: Product of num1 Ã— num2
  - `division`: Quotient of num1 Ã· num2 (string to handle division by zero)
- `status`: Workflow completion status

## ðŸ“‹ Examples

### Example 1: Basic Calculation
```bash
curl -X POST "http://localhost:8000/workflow/math" \
  -H "Content-Type: application/json" \
  -d '{"num1": 10, "num2": 5}'
```

**Response:**
```json
{
  "num1": 10,
  "num2": 5,
  "results": {
    "addition": 15.0,
    "subtraction": 5.0,
    "multiplication": 50.0,
    "division": "2.0"
  },
  "status": "completed"
}
```

### Example 2: Decimal Numbers
```bash
curl -X POST "http://localhost:8000/workflow/math" \
  -H "Content-Type: application/json" \
  -d '{"num1": 7.5, "num2": 2.5}'
```

**Response:**
```json
{
  "num1": 7.5,
  "num2": 2.5,
  "results": {
    "addition": 10.0,
    "subtraction": 5.0,
    "multiplication": 18.75,
    "division": "3.0"
  },
  "status": "completed"
}
```

### Example 3: Division by Zero
```bash
curl -X POST "http://localhost:8000/workflow/math" \
  -H "Content-Type: application/json" \
  -d '{"num1": 15, "num2": 0}'
```

**Response:**
```json
{
  "num1": 15,
  "num2": 0,
  "results": {
    "addition": 15.0,
    "subtraction": 15.0,
    "multiplication": 0.0,
    "division": "Cannot divide by zero"
  },
  "status": "completed"
}
```

### Example 4: Negative Numbers
```bash
curl -X POST "http://localhost:8000/workflow/math" \
  -H "Content-Type: application/json" \
  -d '{"num1": -8, "num2": 4}'
```

**Response:**
```json
{
  "num1": -8,
  "num2": 4,
  "results": {
    "addition": -4.0,
    "subtraction": -12.0,
    "multiplication": -32.0,
    "division": "-2.0"
  },
  "status": "completed"
}
```

## ðŸ Using Python

```python
import requests

url = "http://localhost:8000/workflow/math"
payload = {"num1": 10, "num2": 5}

response = requests.post(url, json=payload)
result = response.json()

print(f"Addition: {result['results']['addition']}")
print(f"Subtraction: {result['results']['subtraction']}")
print(f"Multiplication: {result['results']['multiplication']}")
print(f"Division: {result['results']['division']}")
```

## ðŸŒ Interactive API Docs

FastAPI provides automatic interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

You can test the endpoint directly from the Swagger UI!

## ðŸ” Other Endpoints

The API also includes:
- `GET /health` - Health check endpoint
- `POST /agent/chat` - Basic OpenAI chat
- `POST /agent/zoey/chat` - Zoey agent with tool calling
- Leave Request Workflow: `POST /leave/request`, `POST /leave/manager_reply`, `POST /leave/gmail/process`, `GET /leave/status/{request_id}`, `GET /leave/employees/{employee_id}` (see below)

---

## ðŸ“‹ Leave Request Approval Workflow

**Default flow:** `POST /leave/request` creates the request and returns `PENDING_MANAGER` immediately. Manager decision is processed later by Gmail reply intake or by `POST /leave/manager_reply`.

The workflow runs in two steps: (1) employee submits a request â†’ system checks balance and emails the manager; (2) manager replies via API â†’ system updates balance and notifies the employee.

**Base URL:** Use `http://localhost:9999` if running with Docker (port 9999), or `http://localhost:8000` if running uvicorn locally.

### How manager approval works (emails vs API)

- Employee request methods:
  - Primary: send leave-request email to the configured inbox (`GMAIL_FROM`) with required fields.
  - Override: call `POST /leave/request`.

- Manager decision methods:
  - Primary: reply by email with explicit `Request ID` and `Decision`.
  - Override: call `POST /leave/manager_reply`.

- Waiting behavior:
  - Leave requests stay `PENDING_MANAGER` until a valid manager decision is processed.
  - There is no automatic timeout rejection.
  - `POST /leave/request` is non-blocking by default (`wait=false` by default).

- Gmail processing:
  - Background poller processes inbox continuously when `ENABLE_GMAIL_LEAVE_INTAKE=1`.
  - Start loop + process now: `POST /leave/gmail/process`.
  - One-shot only: `POST /leave/gmail/process?start_loop=false`.

### Test endpoints

```bash
# Process Gmail inbox once (request emails + manager reply emails)
curl -X POST "http://localhost:9999/leave/gmail/process?start_loop=false"

# Start continuous Gmail loop and process immediately
curl -X POST "http://localhost:9999/leave/gmail/process"

# Check loop status
curl "http://localhost:9999/leave/gmail/poller/status"

# Start loop manually if needed
curl -X POST "http://localhost:9999/leave/gmail/poller/start"

# Stop loop
curl -X POST "http://localhost:9999/leave/gmail/poller/stop"

# Health
curl "http://localhost:9999/health"
```

### Create a leave request

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

**Sample response (success):**
```json
{
  "request_id": "LR-0001",
  "status": "PENDING_MANAGER",
  "message": "Request created; manager has been emailed. Awaiting manager reply via email or POST /leave/manager_reply."
}
```

### Create multiple leave requests (parallel workflow style)

```bash
# Request 1: Zoen
curl -X POST "http://localhost:9999/leave/request" \
  -H "Content-Type: application/json" \
  -d '{"employee_id":"E001","leave_type":"annual","start_date":"2026-03-10","end_date":"2026-03-12","reason":"Family trip"}'

# Request 2: Carlos
curl -X POST "http://localhost:9999/leave/request" \
  -H "Content-Type: application/json" \
  -d '{"employee_id":"E002","leave_type":"sick","start_date":"2026-03-11","end_date":"2026-03-11","reason":"Flu"}'
```

Each returns a different `request_id` and can be processed independently.

### Gmail employee request samples (Method A - primary)

Structured sample:

```text
Subject: Leave request for March 10 to March 12
Employee ID: E001
Leave Type: annual
Start Date: 2026-03-10
End Date: 2026-03-12
Reason: Family trip
```

Sentence-style sample (AI parser supported):

```text
Subject: Need leave next week
Hi, this is Zoen Aldueza (E001). I want to file annual leave from 2026-03-10 to 2026-03-12 for a family trip. Thank you.
```

### Manager reply (approve or reject)

```bash
# Approve
curl -X POST "http://localhost:9999/leave/manager_reply" \
  -H "Content-Type: application/json" \
  -d '{"request_id": "LR-0001", "decision": "APPROVE", "comment": "Approved"}'

# Reject
curl -X POST "http://localhost:9999/leave/manager_reply" \
  -H "Content-Type: application/json" \
  -d '{"request_id": "LR-0001", "decision": "REJECT", "comment": "Peak period"}'
```

### Manager reply for multiple pending requests (Method B - override)

```bash
# Approve only LR-0001, leave LR-0002 pending
curl -X POST "http://localhost:9999/leave/manager_reply" \
  -H "Content-Type: application/json" \
  -d '{"request_id":"LR-0001","decision":"APPROVE","comment":"Approved"}'

# Later, decide LR-0002
curl -X POST "http://localhost:9999/leave/manager_reply" \
  -H "Content-Type: application/json" \
  -d '{"request_id":"LR-0002","decision":"REJECT","comment":"Team capacity"}'
```

### Gmail manager reply samples (Method A - primary)

Structured sample:

```text
Subject: Re: Leave Request Approval
Request ID: LR-0001
Decision: APPROVE
Comment: Approved
```

Sentence-style sample (AI parser supported):

```text
Subject: Re: Leave Request Approval for Zoen
Please approve request LR-0001. Looks good from my side.
```

Another sentence-style reject sample:

```text
Subject: Re: Leave Request Approval
For LR-0002, please reject this one due to peak period staffing.
```

### Check request status

```bash
curl "http://localhost:9999/leave/status/LR-0001"
```

### View employee balances and recent history

```bash
curl "http://localhost:9999/leave/employees/E001"
```

---

## ðŸ“§ Gmail setup (optional)

By default, leave emails are **logged to the console** only. To send real emails via Gmail:

1. **Use an App Password (not your normal Gmail password)**  
   - Go to [Google Account â†’ Security](https://myaccount.google.com/security).  
   - Enable **2-Step Verification** if it is not already on.  
   - Open **2-Step Verification** â†’ at the bottom, **App passwords**.  
   - Select app: **Mail**, device: **Other** (e.g. "Leave Workflow"), then **Generate**.  
   - Copy the 16-character password (no spaces).

2. **Set environment variables**  
   - `GMAIL_FROM` â€“ Gmail address that sends (e.g. `you@gmail.com`).  
   - `GMAIL_APP_PASSWORD` â€“ the 16-character app password.  
   - `SEND_LEAVE_EMAILS_VIA_GMAIL=1` â€“ enable sending (otherwise emails are only logged).  
   - Optional: `LEAVE_BASE_URL` â€“ base URL for the manager reply links in the email (default `http://localhost:9999`).

   See `.env.example` for a template. Example `.env`:
   ```bash
   GMAIL_FROM=you@gmail.com
   GMAIL_APP_PASSWORD=abcdabcdabcdabcd
   SEND_LEAVE_EMAILS_VIA_GMAIL=1
   ```

   For Docker, pass these in `docker-compose.yml` under `environment` or use an env file.

3. **Security**  
   - Do not commit the app password to git.  
   - Prefer a dedicated Gmail account or alias for automation.

---

## ðŸ’¡ Behind the Scenes

This endpoint uses the LangGraph workflow defined in:
```
workflow/
â”œâ”€â”€ basic_workflow.py      # Workflow orchestration
â””â”€â”€ nodes/basic/
    â”œâ”€â”€ input_node.py      # Input validation
    â”œâ”€â”€ calculate_node.py  # Math operations
    â””â”€â”€ output_node.py     # Result formatting
```

The workflow executes as: `START â†’ input â†’ calculate â†’ output â†’ END`

---

## ðŸ’¡ Leave workflow structure

Leave request nodes live under `workflow/nodes/leave_request/`:
- `input_validate_node` â†’ `check_balance_node` â†’ `create_request_node` â†’ `send_manager_email_node` (then workflow waits for manager).
- When manager replies: `apply_decision_node` â†’ `notify_employee_node`.
- Data: `data/employees.json`, `data/leave_requests.json` (mock DB).

---

## ðŸ“Œ Academic vs industry: mock DB vs separate DB service

- **Academic / prototype:** A JSON mock DB in the same project is **acceptable and often better**: simple, no extra services, easy to demo and grade. Use it when the goal is to show workflow logic, APIs, and human-in-the-loop behaviour.
- **When to split:** Use a separate DB (or DB API service) when you need real concurrency, audit trails, backups, or multiple apps sharing the same data. In industry, the â€œleaveâ€ service would often call an HR/identity API and a proper database; the workflow you built can stay the same, with only the data layer (e.g. `app/leave_request_db.py`) swapped to use that API/DB.


---

## Email -> Task Extractor Workflow (NEW)

### Endpoints

- `POST /email-task/extract`
  - Simulated Gmail mode (manual email forwarding into API).
  - Input: `subject`, `from`, `body`, optional `received_at`.
  - Output: extracted tasks + created task count.
- `GET /email-task/tasks`
  - List all tasks. Optional query param: `status=PENDING` or `status=DONE`.
- `POST /email-task/mark_done`
  - Mark one task as done using `task_id`.
- `POST /email-task/gmail/poll`
  - Polls Gmail inbox for new messages and runs extraction workflow.
  - Supports `mode=imap` (app password, leave-style) or `mode=oauth` (Google Cloud OAuth).
- `GET /email-task/gmail/poller/status`
  - Shows background poller status for this workflow.
- `POST /email-task/gmail/poller/start`
  - Starts background Gmail polling loop for this workflow.
- `POST /email-task/gmail/poller/stop`
  - Stops background Gmail polling loop for this workflow.

### Node Flow

`input_validate -> extract_tasks_agent -> normalize_and_dedupe -> persist_tasks -> optional_create_calendar_event -> send_summary_email`

### Mock Storage Files

- `data/tasks.json`
- `data/email_state.json`

### Curl tests

1. Simulated email extraction:

```bash
curl -X POST "http://localhost:9999/email-task/extract" \\
  -H "Content-Type: application/json" \\
  -d '{
    "from": "manager@company.com",
    "subject": "Sprint follow-ups for Friday",
    "body": "Hi team, please submit the sprint report by Friday. Also schedule client demo tomorrow 3pm and renew SSL cert before Mar 10."
  }'
```

2. List tasks:

```bash
curl "http://localhost:9999/email-task/tasks"
```

3. Mark task done:

```bash
curl -X POST "http://localhost:9999/email-task/mark_done" \\
  -H "Content-Type: application/json" \\
  -d '{"task_id":"task-REPLACE_ME"}'
```

4. Optional Gmail poll:

```bash
curl -X POST "http://localhost:9999/email-task/gmail/poll" \\
  -H "Content-Type: application/json" \\
  -d '{"mode":"imap","max_results":10,"query":"task,action","skip_existing_on_first_run":true}'
```

5. Optional Gmail background poller start (continuous mode):

```bash
curl -X POST "http://localhost:9999/email-task/gmail/poller/start?interval_seconds=5&mode=imap"
```

6. Check poller status:

```bash
curl "http://localhost:9999/email-task/gmail/poller/status"
```

7. Stop poller:

```bash
curl -X POST "http://localhost:9999/email-task/gmail/poller/stop"
```

### Calendar integration status

- Current build includes `optional_create_calendar_event_node.py` as a stub.
- Future plug-in: Google Calendar API `events.insert` using due date/time from each task.
- No calendar event is auto-created yet in Google Calendar until that stub is implemented.
