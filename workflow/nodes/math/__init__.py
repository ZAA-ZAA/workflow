"""Math nodes alias package.

The project's original math workflow nodes are implemented in
`workflow/nodes/basic/`. This alias keeps a clear `nodes/math/` path.
"""

from workflow.nodes.basic import WorkflowState, calculate_node, check_node, input_node, output_node

__all__ = [
    "WorkflowState",
    "input_node",
    "calculate_node",
    "check_node",
    "output_node",
]
