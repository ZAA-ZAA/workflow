"""Output node for basic math workflow."""

from .state import WorkflowState


def output_node(state: WorkflowState) -> WorkflowState:
    """
    Final node that displays all calculation results.
    
    Args:
        state: Current workflow state with all calculation results
        
    Returns:
        Final workflow state
    """
    print(f"\n📤 Output Node: Finalizing results")
    print("="*50)
    print(f"  Input: {state['num1']} and {state['num2']}")
    print(f"  Addition: {state['add_result']}")
    print(f"  Subtraction: {state['subtract_result']}")
    print(f"  Multiplication: {state['multiply_result']}")
    print(f"  Division: {state['divide_result']}")
    print("="*50)
    
    # Keep step from check node: "completed" (tama) or "mali" (may error)
    return {
        **state,
    }
