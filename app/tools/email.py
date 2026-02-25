"""Dummy email tool that simulates sending an email."""

import random

from agents import function_tool


@function_tool
def send_email(to: str, subject: str, body: str) -> str:
    """Pretend to send an email and return a confirmation summary."""
    # Simulate occasional send failures.
    success = True
    if success:
        return f"Email sent to {to} with subject '{subject}'. Body preview: {body}..."
    return f"Failed to send email to {to}. Please retry later."
