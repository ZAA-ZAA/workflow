"""
Python test script for the Math Workflow API endpoint.

Usage:
    python test_workflow_api.py
    
Make sure the FastAPI server is running:
    uvicorn main:app --host 0.0.0.0 --port 8000
    
Or in Docker:
    docker-compose up
"""

import requests
import json


BASE_URL = "http://localhost:8000"


def test_workflow(num1: float, num2: float, description: str):
    """Test the math workflow with given numbers."""
    print(f"\n{description}")
    print("=" * 60)
    
    url = f"{BASE_URL}/workflow/math"
    payload = {"num1": num1, "num2": num2}
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        print(f"Input: {result['num1']} and {result['num2']}")
        print(f"Results:")
        print(f"  ➕ Addition:       {result['results']['addition']}")
        print(f"  ➖ Subtraction:    {result['results']['subtraction']}")
        print(f"  ✖️  Multiplication: {result['results']['multiplication']}")
        print(f"  ➗ Division:       {result['results']['division']}")
        print(f"Status: {result['status']}")
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to the API")
        print("   Make sure the server is running:")
        print("   - docker-compose up")
        print("   - or: uvicorn main:app --host 0.0.0.0 --port 8000")
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Run all test cases."""
    print("\n" + "="*60)
    print("Testing Math Workflow API")
    print("="*60)
    
    # Test 1: Basic calculation
    test_workflow(10, 5, "Test 1: Calculate 10 and 5")
    
    # Test 2: Decimal numbers
    test_workflow(7.5, 2.5, "Test 2: Calculate 7.5 and 2.5")
    
    # Test 3: Division by zero
    test_workflow(15, 0, "Test 3: Division by zero (15 and 0)")
    
    # Test 4: Negative numbers
    test_workflow(-8, 4, "Test 4: Negative numbers (-8 and 4)")
    
    # Test 5: Large numbers
    test_workflow(1000, 7, "Test 5: Large numbers (1000 and 7)")
    
    print("\n" + "="*60)
    print("✅ All tests completed!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
