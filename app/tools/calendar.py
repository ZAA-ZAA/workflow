"""Dummy calendar tool returning hard-coded events."""

from datetime import date as _date
from typing import List, Dict

from agents import function_tool


_DUMMY_EVENTS: List[Dict[str, str]] = [
    {"date": "2026-02-11", "title": "Product sync", "time": "10:00", "location": "Zoom"},
    {"date": "2026-02-11", "title": "Lunch with Sam", "time": "12:30", "location": "Cafe Rio"},
    {"date": "2026-02-12", "title": "Sprint planning", "time": "09:00", "location": "Room 3A"},
    {"date": "2026-02-13", "title": "Dentist appointment", "time": "15:00", "location": "Downtown Clinic"},
]


@function_tool
def list_events(for_date: str | None = None) -> str:
    """List calendar events for a date (YYYY-MM-DD). Defaults to today."""
    target = for_date or _date.today().isoformat()
    matches = [e for e in _DUMMY_EVENTS if e["date"] == target]
    if not matches:
        return f"No events found for {target}."
    lines = [f"{e['time']} - {e['title']} @ {e['location']}" for e in matches]
    return f"Events for {target}:\n" + "\n".join(lines)