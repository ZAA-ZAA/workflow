# Email -> Task Extractor Nodes

Node order used by `workflow/email_task_workflow.py`:

1. `input_validate_node.py`
2. `extract_tasks_agent_node.py`
3. `normalize_and_dedupe_node.py`
4. `persist_tasks_node.py`
5. `optional_create_calendar_event_node.py`
6. `send_summary_email_node.py`

This workflow stores tasks in `data/tasks.json` and duplicate-tracking state in `data/email_state.json`.
