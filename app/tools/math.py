"""Math-related tools."""

from agents import function_tool


@function_tool
def add_numbers(a: int, b: int) -> str:
    """Add two integers and describe the steps plus final answer."""
    total = a + b
    return f"The sum of {a} and {b} is {total}."
