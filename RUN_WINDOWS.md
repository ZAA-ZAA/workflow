# Running and testing on Windows

This file is **documentation only** (read it in your editor or browser). To run the app, use the commands below in CMD or PowerShell; do not try to "run" this .md file.

## What you need

1. **OpenAI API key**  
   The check node uses the Math Checker AI agent (OpenAI). Set your key before running:
   - **CMD:**  
     `set OPENAI_API_KEY=sk-your-key-here`
   - **PowerShell:**  
     `$env:OPENAI_API_KEY="sk-your-key-here"`

2. **Python** with dependencies installed:
   ```cmd
   pip install -r requirements.txt
   ```

---

## Start the server

## Running with Docker

When you use Docker, the API key and anything else the app needs must be passed into the container.

### 1. Where to put the API key

**Option A – `.env` file (recommended)**  
In the **same folder as `docker-compose.yml`** (project root), create a file named `.env`:

```env
OPENAI_API_KEY=sk-your-actual-key-here
```

Docker Compose reads this file automatically and sets `OPENAI_API_KEY` inside the container.  
Do not commit `.env` (it’s in `.gitignore`).

**Option B – Set in the shell before running**  
- **CMD:**  
  `set OPENAI_API_KEY=sk-your-key-here`  
  then run `docker-compose up`  
- **PowerShell:**  
  `$env:OPENAI_API_KEY="sk-your-key-here"`  
  then run `docker-compose up`

### 2. Start the app

```cmd
docker-compose up
```

### 3. Port when using Docker

In `docker-compose.yml` the app is mapped to **port 9999** on your machine (`9999:8000`). So:

- Base URL when using Docker: **`http://localhost:9999`**
- Health check: `http://localhost:9999/health`
- Workflow: `http://localhost:9999/workflow/math`

You don’t need to set anything else for the math workflow + check node; the container only needs `OPENAI_API_KEY`.

If you see `status: "incorrect"` and logs show **401** or **invalid_api_key** or **"Inccorrect API key provided"**: the math is fine; your **OpenAI API key** is invalid or expired. Update `OPENAI_API_KEY` in `.env` (no extra spaces), get a key at https://platform.openai.com/account/api-keys, then run `docker-compose up --build` again.

---

## Test the endpoint (copy-paste)

**If you’re using Docker, use port 9999. If you ran uvicorn locally, use port 8000.**

### CMD – single curl (one line)

**Docker (port 9999):**
```cmd
curl -X POST "http://localhost:9999/workflow/math" -H "Content-Type: application/json" -d "{\"num1\": 10, \"num2\": 5}"
```

**Local uvicorn (port 8000):**
```cmd
curl -X POST "http://localhost:8000/workflow/math" -H "Content-Type: application/json" -d "{\"num1\": 10, \"num2\": 5}"
```

### PowerShell (copy-paste)

In PowerShell, **`curl` is an alias** for `Invoke-WebRequest` and uses different parameters, so the command fails. Use one of these instead:

**Option 1 – Invoke-RestMethod (recommended in PowerShell)**  
Docker (port 9999):
```powershell
Invoke-RestMethod -Uri "http://localhost:9999/workflow/math" -Method Post -ContentType "application/json" -Body '{"num1": 10, "num2": 5}'
```
Local (port 8000):
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/workflow/math" -Method Post -ContentType "application/json" -Body '{"num1": 10, "num2": 5}'
```

**Option 2 – Real curl**  
Call `curl.exe` (not `curl`) so you get the actual curl program:
```powershell
curl.exe -X POST "http://localhost:9999/workflow/math" -H "Content-Type: application/json" -d '{"num1": 10, "num2": 5}'
```

### Run all tests (Windows batch)

The batch file uses port 8000. **If you use Docker**, either change `BASE_URL` in `test_workflow_api.py` to `http://localhost:9999` or run curl manually with port 9999.

### Run Python test script

```cmd
python test_workflow_api.py
```

---

## Leave workflow Gmail mode (new)

If you want Gmail to be the primary method:

1. Set env vars (in `.env` or shell):
   - `GMAIL_FROM`
   - `GMAIL_APP_PASSWORD`
   - `SEND_LEAVE_EMAILS_VIA_GMAIL=1`
   - optional: `ENABLE_GMAIL_LEAVE_INTAKE=1` (default enabled)
2. Start the app. It will poll inbox in background.
3. Optional manual trigger:
   - `POST /leave/gmail/process`
4. API override paths still work:
   - `POST /leave/request`
   - `POST /leave/manager_reply`

---

## Workflow status

- **`status: "correct"`** – Math Checker agent said all results are correct.
- **`status: "incorrect"`** – At least one result is wrong (e.g. if you change the formula in `calculate_node.py` on purpose).

To test the checker, change the formula in `workflow/nodes/basic/calculate_node.py` (e.g. line 28: use `num1 - num2` instead of `num1 + num2` for addition), run the workflow again, and you should get `status: "incorrect"`.
