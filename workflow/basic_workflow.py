"""
Basic Math Workflow Example

This is a super simple LangGraph workflow that demonstrates:
- Accepting 2 numbers as input
- Performing 4 basic math operations (add, subtract, multiply, divide)
- Linear workflow with 3 nodes: input → calculate → output

This workflow is designed to be easy to understand for beginners!
Nodes are organized in separate files under workflow/nodes/basic/
"""

from langgraph.graph import StateGraph, END
from workflow.nodes.basic import (
    WorkflowState,
    input_node,
    calculate_node,
    check_node,
    output_node,
)


def create_basic_workflow() -> StateGraph:
    """
    Creates a simple math calculator workflow.
    
    Workflow structure (linear, no branching):
    START → input → calculate → check → output → END
    
    Returns:
        StateGraph: The compiled LangGraph workflow
    """
    # Create the state graph
    workflow = StateGraph(WorkflowState)
    
    # Add nodes to the graph
    workflow.add_node("input", input_node)
    workflow.add_node("calculate", calculate_node)
    workflow.add_node("check", check_node)
    workflow.add_node("output", output_node)
    
    # Define the linear flow (no conditional edges!)
    workflow.set_entry_point("input")
    workflow.add_edge("input", "calculate")
    workflow.add_edge("calculate", "check")
    workflow.add_edge("check", "output")
    workflow.add_edge("output", END)
    
    return workflow


def run_workflow(num1: float, num2: float) -> dict:
    """
    Execute the math workflow with two numbers.
    
    Args:
        num1: First number
        num2: Second number
        
    Returns:
        dict: The final state with all calculation results
    """
    print("\n" + "="*60)
    print("🚀 Starting Basic Math Workflow")
    print("="*60 + "\n")
    
    # Create the workflow
    workflow = create_basic_workflow()
    
    # Compile the workflow
    app = workflow.compile()
    
    # Initial state
    initial_state: WorkflowState = {
        "num1": num1,
        "num2": num2,
        "add_result": None,
        "subtract_result": None,
        "multiply_result": None,
        "divide_result": None,
        "step": "started",
    }
    
    # Run the workflow
    final_state = app.invoke(initial_state)
    
    print("\n" + "="*60)
    print("✅ Workflow Complete!")
    print("="*60)
    print(f"Status: {final_state['step']}\n")
    
    return final_state


if __name__ == "__main__":
    # Example 1: Basic calculation
    print("\n### Example 1: Calculate 10 and 5 ###")
    run_workflow(10, 5)
    
    print("\n\n")
    
    # Example 2: With decimal numbers
    print("\n### Example 2: Calculate 7.5 and 2.5 ###")
    run_workflow(7.5, 2.5)
    
    print("\n\n")
    
    # Example 3: Division by zero handling
    print("\n### Example 3: Division by zero (15 and 0) ###")
    run_workflow(15, 0)
