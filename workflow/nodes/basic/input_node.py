"""Input node for basic math workflow."""

from .state import WorkflowState


def input_node(state: WorkflowState) -> WorkflowState:
    """
    Initial node that receives and validates two numbers.
    
    Args:
        state: Current workflow state with num1 and num2
        
    Returns:
        Updated workflow state
    """
    num1 = state['num1']
    num2 = state['num2']
    
    print(f"📥 Input Node: Received numbers: {num1} and {num2}")
    
    return {
        **state,
        "step": "input_validated",
        "add_result": None,
        "subtract_result": None,
        "multiply_result": None,
        "divide_result": None,
    }
