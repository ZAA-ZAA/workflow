# LangGraph Workflows

This directory contains sample LangGraph workflow implementations demonstrating various patterns and use cases.

## 📁 Directory Structure

```
workflow/
├── __init__.py
├── basic_workflow.py       # Simple math calculator workflow
├── llm_workflow.py         # LLM-integrated workflow
├── README.md              # This file
└── nodes/                 # Modular node implementations
    ├── __init__.py
    └── basic/             # Nodes for basic math workflow
        ├── __init__.py
        ├── state.py       # State definition
        ├── input_node.py  # Input validation
        ├── calculate_node.py  # Math operations
        ├── output_node.py # Result display
        └── README.md      # Detailed node docs
```

## 📝 Workflows

### `basic_workflow.py` - Math Calculator 🧮

**Super simple workflow for beginners!** Takes 2 numbers and performs all 4 basic math operations.

**What it does:**
1. Accepts 2 numbers as input
2. Performs: addition, subtraction, multiplication, division
3. Displays all results

**Example Usage:**
```python
from workflow.basic_workflow import run_workflow

# Calculate with 10 and 5
result = run_workflow(10, 5)
# Output:
#   Addition: 15.0
#   Subtraction: 5.0
#   Multiplication: 50.0
#   Division: 2.0

# Works with decimals too!
result = run_workflow(7.5, 2.5)

# Handles division by zero
result = run_workflow(15, 0)
# Output: Division: "Cannot divide by zero"
```

**Workflow Structure (Linear - No Branching!):**
```
START → input → calculate → output → END
```

**Node Organization:**
Each node is in a separate file under `workflow/nodes/basic/`:
- `input_node.py` - Receives and validates 2 numbers
- `calculate_node.py` - Performs all 4 math operations
- `output_node.py` - Displays results in nice format
- `state.py` - Defines WorkflowState with num1, num2, and results

**Why this workflow is great for learning:**
- ✅ Only 3 nodes in a straight line
- ✅ No complex conditional logic
- ✅ Clear input and output
- ✅ Easy to understand what each node does
- ✅ Modular structure shows best practices

### `llm_workflow.py` - AI Agent Workflow 🤖

An LLM-integrated workflow showing how to:
- **Integrate OpenAI** with LangGraph
- **Manage message history** with state
- **Create agent-based workflows**
- **Handle LLM responses** in a graph structure

**Example Usage:**
```python
from workflow.llm_workflow import run_llm_workflow

result = run_llm_workflow(
    user_input="What is LangGraph?",
    system_prompt="You are a helpful AI assistant."
)
```

## 🚀 Quick Start

### 1. Install Dependencies

Make sure you have the required packages installed:

```bash
pip install -r requirements.txt
```

Or with Docker:

```bash
docker-compose build
```

### 2. Set Environment Variables

Create a `.env` file with your OpenAI API key:

```bash
OPENAI_API_KEY=your_api_key_here
```

### 3. Run Examples

#### Run Basic Workflow:
```bash
# From the project root
python -m workflow.basic_workflow
```

Or in Docker:
```bash
docker-compose exec app python -m workflow.basic_workflow
```

#### Run LLM Workflow:
```bash
# From the project root
python -m workflow.llm_workflow
```

Or in Docker:
```bash
docker-compose exec app python -m workflow.llm_workflow
```

## 🏗️ Workflow Patterns

### Basic State Graph Pattern

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

class State(TypedDict):
    data: str
    
workflow = StateGraph(State)
workflow.add_node("process", process_function)
workflow.set_entry_point("process")
workflow.add_edge("process", END)

app = workflow.compile()
result = app.invoke({"data": "input"})
```

### Conditional Routing Pattern

```python
def router(state: State) -> str:
    if condition:
        return "path_a"
    return "path_b"

workflow.add_conditional_edges(
    "node_name",
    router,
    {
        "path_a": "node_a",
        "path_b": "node_b"
    }
)
```

### LLM Integration Pattern

```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

llm = ChatOpenAI(model="gpt-4o-mini")

def llm_node(state: State):
    response = llm.invoke(state["messages"])
    return {"messages": [response]}
```

## 🔧 Extending the Workflows

### Adding New Nodes

1. Define a function that takes state and returns updated state:
```python
def my_node(state: WorkflowState) -> WorkflowState:
    # Process the state
    return {**state, "new_field": "value"}
```

2. Add it to the workflow:
```python
workflow.add_node("my_node", my_node)
workflow.add_edge("previous_node", "my_node")
```

### Adding Tools

For tool calling with LLMs:

```python
from langchain_core.tools import tool

@tool
def my_tool(query: str) -> str:
    """Tool description."""
    return f"Result for {query}"

tools = [my_tool]
llm_with_tools = llm.bind_tools(tools)
```

## 📚 Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangChain Documentation](https://python.langchain.com/)
- [LangGraph Tutorials](https://langchain-ai.github.io/langgraph/tutorials/)

## 🐳 Docker Usage

The workflows are designed to run in the Docker environment:

```bash
# Build the container
docker-compose build

# Run a workflow
docker-compose exec app python -m workflow.basic_workflow

# Or start an interactive shell
docker-compose exec app bash
```

## 💡 Tips

1. **State Design**: Keep your state structure simple and focused on what you need
2. **Node Functions**: Each node should have a single responsibility
3. **Conditional Logic**: Use conditional edges for complex routing logic
4. **Testing**: Test individual nodes before integrating into the full workflow
5. **Debugging**: Add print statements or logging to track workflow execution

## 🔍 Common Use Cases

- **Multi-step agents**: Break complex tasks into discrete steps
- **Human-in-the-loop**: Add approval nodes for human review
- **Tool calling**: Integrate external APIs and tools
- **Parallel processing**: Execute multiple nodes concurrently
- **Error handling**: Add retry logic and fallback paths
