#!/bin/bash

# Test script for the math workflow API endpoint

echo "Testing Math Workflow API"
echo "=========================="
echo ""

# Example 1: Basic calculation
echo "Example 1: Calculate 10 and 5"
curl -X POST "http://localhost:8000/workflow/math" \
  -H "Content-Type: application/json" \
  -d '{"num1": 10, "num2": 5}'
echo -e "\n"

# Example 2: Decimal numbers
echo "Example 2: Calculate 7.5 and 2.5"
curl -X POST "http://localhost:8000/workflow/math" \
  -H "Content-Type: application/json" \
  -d '{"num1": 7.5, "num2": 2.5}'
echo -e "\n"

# Example 3: Division by zero
echo "Example 3: Division by zero (15 and 0)"
curl -X POST "http://localhost:8000/workflow/math" \
  -H "Content-Type: application/json" \
  -d '{"num1": 15, "num2": 0}'
echo -e "\n"

# Example 4: Negative numbers
echo "Example 4: Negative numbers (-8 and 4)"
curl -X POST "http://localhost:8000/workflow/math" \
  -H "Content-Type: application/json" \
  -d '{"num1": -8, "num2": 4}'
echo -e "\n"
