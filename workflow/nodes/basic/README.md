# Basic Math Workflow Nodes

This directory contains super simple node implementations for a basic math calculator workflow.

## 🎯 What This Workflow Does

**Accepts 2 numbers → Performs all 4 basic math operations → Shows results**

It's designed to be the easiest possible example to understand how LangGraph workflows work!

## 📁 File Structure

```
workflow/nodes/basic/
├── __init__.py          # Package initialization with exports
├── state.py             # WorkflowState definition (holds 2 numbers + results)
├── input_node.py        # Receives and validates 2 numbers
├── calculate_node.py    # Performs all math operations
└── output_node.py       # Displays all results
```

## 📝 Node Descriptions

### `state.py`
Defines the `WorkflowState` TypedDict:
- `num1`: First number (float)
- `num2`: Second number (float)
- `add_result`: Result of num1 + num2
- `subtract_result`: Result of num1 - num2
- `multiply_result`: Result of num1 × num2
- `divide_result`: Result of num1 ÷ num2 (handles division by zero)
- `step`: Current workflow step name

### `input_node.py`
**Entry point** - receives the two numbers.
- Validates the input
- Initializes all result fields to None
- Moves to "input_validated" step

### `calculate_node.py`
**Main processor** - does all the math!
- ➕ Addition: `num1 + num2`
- ➖ Subtraction: `num1 - num2`
- ✖️ Multiplication: `num1 × num2`
- ➗ Division: `num1 ÷ num2` (with zero check)
- Prints each result as it calculates

### `output_node.py`
**Exit point** - displays all results in a nice format.
- Shows a summary of all calculations
- Sets final step to "completed"

## 🔄 Workflow Flow (Linear!)

```
START → input_node → calculate_node → output_node → END
```

No conditional routing, no branching - just a simple straight line!

## 🎯 Example Usage

```python
from workflow.nodes.basic import (
    WorkflowState,
    input_node,
    calculate_node,
    output_node,
)

# Create initial state
state: WorkflowState = {
    "num1": 10,
    "num2": 5,
    "add_result": None,
    "subtract_result": None,
    "multiply_result": None,
    "divide_result": None,
    "step": "started"
}

# Run through nodes
state = input_node(state)
state = calculate_node(state)
state = output_node(state)

# Results are now in state
print(state["add_result"])      # 15.0
print(state["subtract_result"]) # 5.0
print(state["multiply_result"]) # 50.0
print(state["divide_result"])   # "2.0"
```

Or use the workflow orchestrator:

```python
from workflow.basic_workflow import run_workflow

result = run_workflow(10, 5)
```

## ✨ Why This Structure?

- **Simple**: Only 3 nodes in a straight line
- **Clear**: Each node has exactly one job
- **Beginner-friendly**: Easy to understand what happens at each step
- **Modular**: Each node can be tested independently
- **Extensible**: Easy to add more operations by editing calculate_node.py

## 🔧 Adding More Operations

Want to add more math operations? Just edit `calculate_node.py`:

```python
# Add in calculate_node function
power_result = num1 ** num2
print(f"  🔢 Power: {num1} ^ {num2} = {power_result}")

return {
    **state,
    "power_result": power_result,  # Don't forget to add to state!
    # ... other results
}
```

And update `state.py` to include the new field:

```python
class WorkflowState(TypedDict):
    # ... existing fields
    power_result: Optional[float]
```
