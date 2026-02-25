"""Check node — uses AI agent to validate calculation results."""

import os
import re

from openai import OpenAI

from app.agents.math_checker_agent import create_math_checker_agent
from .state import WorkflowState


def check_node(state: WorkflowState) -> WorkflowState:
    """
    Validates math results using the Math Checker AI agent.

    Sends num1, num2, and all results to the agent. If the agent says
    CORRECT, step is set to "correct"; otherwise "incorrect".
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {
            **state,
            "step": "incorrect",
        }
    client = OpenAI(api_key=api_key)
    agent = create_math_checker_agent()

    num1 = state["num1"]
    num2 = state["num2"]
    add_result = state.get("add_result")
    subtract_result = state.get("subtract_result")
    multiply_result = state.get("multiply_result")
    divide_result = state.get("divide_result")

    prompt = (
        f"Numbers: {num1} and {num2}. "
        f"Addition result: {add_result}. "
        f"Subtraction result: {subtract_result}. "
        f"Multiplication result: {multiply_result}. "
        f"Division result: {divide_result}. "
        "Are these results correct? Reply with only CORRECT or INCORRECT."
    )

    print(f"🔍 Check Node: Asking Math Checker agent to validate results...")

    try:
        response = client.chat.completions.create(
            model=agent.model or "gpt-4o-mini",
            messages=[
                {"role": "system", "content": agent.instructions},
                {"role": "user", "content": prompt},
            ],
        )
        raw = (response.choices[0].message.content or "").strip()
        content = raw.upper().replace("```", "").strip()
        words = content.split()
        last_word = (words[-1] if words else "").rstrip(".,!?")
        # Word-boundary match so "INCORRECT" doesn't match "CORRECT"
        has_correct = bool(re.search(r"\bCORRECT\b", content)) or "ACCURATE" in content
        has_incorrect = bool(re.search(r"\bINCORRECT\b", content))
        is_correct = (
            last_word in ("CORRECT", "ACCURATE")
            or (has_correct and not has_incorrect)
        )
        step = "correct" if is_correct else "incorrect"
        print(f"  Agent raw reply: {raw!r}")
    except Exception as e:
        err = str(e)
        if "401" in err or "invalid_api_key" in err or "Inccorrect API key" in err:
            print("⚠️  Check Node: OpenAI API key invalid or rejected. Check OPENAI_API_KEY in .env (no spaces, valid key from https://platform.openai.com/account/api-keys).")
        else:
            print(f"⚠️  Check Node: Agent call failed: {e}")
        step = "incorrect"

    if step == "correct":
        print("  ✅ Validation: Tama ang results.")
    else:
        print("  ❌ Validation: May mali sa results.")

    return {
        **state,
        "step": step,
    }
