@echo off
REM Test script for the math workflow API (Windows CMD)
REM Make sure the server is running first: set OPENAI_API_KEY=... && uvicorn main:app --host 0.0.0.0 --port 8000

echo Testing Math Workflow API
echo ==========================
echo.

echo Example 1: Calculate 10 and 5
curl -X POST "http://localhost:8000/workflow/math" -H "Content-Type: application/json" -d "{\"num1\": 10, \"num2\": 5}"
echo.

@REM echo Example 2: Calculate 7.5 and 2.5
@REM curl -X POST "http://localhost:8000/workflow/math" -H "Content-Type: application/json" -d "{\"num1\": 7.5, \"num2\": 2.5}"
@REM echo.

@REM echo Example 3: Division by zero (15 and 0)
@REM curl -X POST "http://localhost:8000/workflow/math" -H "Content-Type: application/json" -d "{\"num1\": 15, \"num2\": 0}"
@REM echo.

@REM echo Example 4: Negative numbers (-8 and 4)
@REM curl -X POST "http://localhost:8000/workflow/math" -H "Content-Type: application/json" -d "{\"num1\": -8, \"num2\": 4}"
@REM echo.

pause
