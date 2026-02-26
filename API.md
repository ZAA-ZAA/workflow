# Math Workflow API

The math workflow is now available as a REST API endpoint in the FastAPI application!

## 🚀 Quick Start

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

## 📡 API Endpoint

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
  - `multiplication`: Product of num1 × num2
  - `division`: Quotient of num1 ÷ num2 (string to handle division by zero)
- `status`: Workflow completion status

## 📋 Examples

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

## 🐍 Using Python

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

## 🌐 Interactive API Docs

FastAPI provides automatic interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

You can test the endpoint directly from the Swagger UI!

## 🔍 Other Endpoints

The API also includes:
- `GET /health` - Health check endpoint
- `POST /agent/chat` - Basic OpenAI chat
- `POST /agent/zoey/chat` - Zoey agent with tool calling
- Leave Request Workflow: `POST /leave/request`, `POST /leave/manager_reply`, `GET /leave/status/{request_id}`, `GET /leave/employees/{employee_id}` (see below)

---

## 📋 Leave Request Approval Workflow

**Single-curl flow (default):** One **POST /leave/request** runs the workflow start to finish: it sends the email to the manager, then waits for a reply (by polling Gmail or by detecting **POST /leave/manager_reply** from another terminal). When the manager's decision is in, it applies it and notifies the employee, then returns. Use **?wait=false** to return immediately with PENDING_MANAGER.

The workflow runs in two steps: (1) employee submits a request → system checks balance and emails the manager; (2) manager replies via API → system updates balance and notifies the employee.

**Base URL:** Use `http://localhost:9999` if running with Docker (port 9999), or `http://localhost:8000` if running uvicorn locally.

### How manager approval works (emails vs API)

- **Where emails come from**  
  The addresses in `data/employees.json` are used when sending:
  - **Manager:** `manager_email` on each employee is used as the **To** address for the “please approve/reject” email.
  - **Employee:** `email` on each employee is used as the **To** address for the approval or rejection notification.

- **Does the workflow wait for a reply in Gmail?**  
  **No.** The app does not read the manager’s Gmail inbox. When we say the workflow “waits for the manager,” we mean:
  - The request stays in status `PENDING_MANAGER` until someone (usually the manager) calls the API.
  - The **only** way to approve or reject is to call **POST /leave/manager_reply** with `request_id` and `decision` (APPROVE or REJECT). The email we send to the manager contains the curl commands so they can do that.
  - So there is **one** way to respond: use the API. The two “options” are the two **decisions** (APPROVE vs REJECT), not “reply by email” vs “call API.” Replying to the email in Gmail does **not** update the workflow unless you add something like Gmail API polling (not included here).

- **Summary**
  - Emails **to** manager and **to** employee use the addresses from `data/employees.json` (and Gmail if configured).
  - The workflow **waits** for a reply: it polls Gmail (IMAP) for a reply from the manager and uses an AI agent to parse APPROVE/REJECT, or you can submit the decision from another terminal via **POST /leave/manager_reply**.

**Single-curl behavior:** By default, **POST /leave/request** blocks until the manager has replied (via Gmail or API) or the timeout (see `LEAVE_WAIT_TIMEOUT_SECONDS`). So one curl runs the workflow start to finish. Use `?wait=false` to return immediately with PENDING_MANAGER and then use **POST /leave/manager_reply** separately.

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
  "message": "Request created; manager has been emailed. Awaiting manager reply via POST /leave/manager_reply."
}
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

### Check request status

```bash
curl "http://localhost:9999/leave/status/LR-0001"
```

### View employee balances and recent history

```bash
curl "http://localhost:9999/leave/employees/E001"
```

---

## 📧 Gmail setup (optional)

By default, leave emails are **logged to the console** only. To send real emails via Gmail:

1. **Use an App Password (not your normal Gmail password)**  
   - Go to [Google Account → Security](https://myaccount.google.com/security).  
   - Enable **2-Step Verification** if it is not already on.  
   - Open **2-Step Verification** → at the bottom, **App passwords**.  
   - Select app: **Mail**, device: **Other** (e.g. "Leave Workflow"), then **Generate**.  
   - Copy the 16-character password (no spaces).

2. **Set environment variables**  
   - `GMAIL_FROM` – Gmail address that sends (e.g. `you@gmail.com`).  
   - `GMAIL_APP_PASSWORD` – the 16-character app password.  
   - `SEND_LEAVE_EMAILS_VIA_GMAIL=1` – enable sending (otherwise emails are only logged).  
   - Optional: `LEAVE_BASE_URL` – base URL for the manager reply links in the email (default `http://localhost:9999`).

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

## 💡 Behind the Scenes

This endpoint uses the LangGraph workflow defined in:
```
workflow/
├── basic_workflow.py      # Workflow orchestration
└── nodes/basic/
    ├── input_node.py      # Input validation
    ├── calculate_node.py  # Math operations
    └── output_node.py     # Result formatting
```

The workflow executes as: `START → input → calculate → output → END`

---

## 💡 Leave workflow structure

Leave request nodes live under `workflow/nodes/leave_request/`:
- `input_validate_node` → `check_balance_node` → `create_request_node` → `send_manager_email_node` (then workflow waits for manager).
- When manager replies: `apply_decision_node` → `notify_employee_node`.
- Data: `data/employees.json`, `data/leave_requests.json` (mock DB).

---

## 📌 Academic vs industry: mock DB vs separate DB service

- **Academic / prototype:** A JSON mock DB in the same project is **acceptable and often better**: simple, no extra services, easy to demo and grade. Use it when the goal is to show workflow logic, APIs, and human-in-the-loop behaviour.
- **When to split:** Use a separate DB (or DB API service) when you need real concurrency, audit trails, backups, or multiple apps sharing the same data. In industry, the “leave” service would often call an HR/identity API and a proper database; the workflow you built can stay the same, with only the data layer (e.g. `app/leave_request_db.py`) swapped to use that API/DB.
