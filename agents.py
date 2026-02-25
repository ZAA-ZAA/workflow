"""Lightweight agent helpers for tool-enabled chats."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass
class Agent:
    """Simple container describing an agent."""

    name: str
    instructions: str
    tools: List[Callable]
    model: Optional[str] = None


def function_tool(func: Callable) -> Callable:
    """Mark a function as a tool; metadata is derived at runtime."""
    func._is_function_tool = True  # marker only
    return func


def _annotation_to_json_type(annotation: Any) -> str:
    """Map Python type annotations to JSON schema type names."""
    if annotation in (int, "int"):
        return "integer"
    if annotation in (float, "float"):
        return "number"
    if annotation in (bool, "bool"):
        return "boolean"
    return "string"


def build_tool_spec(func: Callable) -> Dict[str, Any]:
    """Create an OpenAI tool spec from a Python function signature."""
    signature = inspect.signature(func)
    properties: Dict[str, Any] = {}
    required: List[str] = []

    for name, param in signature.parameters.items():
        properties[name] = {
            "type": _annotation_to_json_type(param.annotation),
        }
        if param.default is inspect._empty:
            required.append(name)

    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": (func.__doc__ or "").strip(),
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


def get_tool_specs(tools: List[Callable]) -> List[Dict[str, Any]]:
    """Build tool specs for all registered tools."""
    return [build_tool_spec(tool) for tool in tools]


def execute_tool_by_name(tools: List[Callable], name: str, arguments: Dict[str, Any]) -> Any:
    """Run a tool by name with provided arguments."""
    for tool in tools:
        if tool.__name__ == name:
            return tool(**arguments)
    raise ValueError(f"Tool '{name}' not found")
