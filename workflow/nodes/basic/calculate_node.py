"""Calculate node for basic math workflow."""

from .state import WorkflowState


def calculate_node(state: WorkflowState) -> WorkflowState:
    """
    Performs all math operations on the two numbers.
    
    Operations performed:
    - Addition: num1 + num2
    - Subtraction: num1 - num2
    - Multiplication: num1 * num2
    - Division: num1 / num2 (handles division by zero)
    
    Args:
        state: Current workflow state with num1 and num2
        
    Returns:
        Updated workflow state with all calculation results
    """
    num1 = state['num1']
    num2 = state['num2']
    
    print(f"🧮 Calculate Node: Performing operations on {num1} and {num2}")
    
    # Perform all operations
    add_result = num1 + num2
    subtract_result = num1 - num2
    multiply_result = num1 - num2
    
    # Handle division by zero
    if num2 == 0:
        divide_result = "Cannot divide by zero"
        print("⚠️  Warning: Division by zero detected")
    else:
        divide_result = str(num1 / num2)
    
    print(f"  ➕ Addition: {num1} + {num2} = {add_result}")
    print(f"  ➖ Subtraction: {num1} - {num2} = {subtract_result}")
    print(f"  ✖️  Multiplication: {num1} × {num2} = {multiply_result}")
    print(f"  ➗ Division: {num1} ÷ {num2} = {divide_result}")
    
    return {
        **state,
        "step": "calculated",
        "add_result": add_result,
        "subtract_result": subtract_result,
        "multiply_result": multiply_result,
        "divide_result": divide_result,
    }
