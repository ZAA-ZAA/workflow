"""State definition for basic math workflow."""

from typing import TypedDict, Optional


class WorkflowState(TypedDict):
    """State object that gets passed between nodes."""
    num1: float
    num2: float
    add_result: Optional[float]
    subtract_result: Optional[float]
    multiply_result: Optional[float]
    divide_result: Optional[str]  # str to handle division by zero message
    step: str
