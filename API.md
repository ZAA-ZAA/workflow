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
