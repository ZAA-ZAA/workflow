"""Math Checker agent — validates calculation results in the workflow."""

from agents import Agent


def create_math_checker_agent(model_override: str | None = None) -> Agent:
    """
    Return an agent that checks if math results are correct.

    Used by the workflow check node to validate add/subtract/multiply/divide
    results. No tools; agent replies with CORRECT or INCORRECT.
    """
    instructions = (
        "You are a Math Checker agent. Your job is to verify if the given calculation results are correct. "
        "You will receive two numbers and the results of addition, subtraction, multiplication, and division. "
        "Treat 15.0 as correct for 15, and 2.0 as correct for 2 (decimals are fine). "
        "Reply with exactly one word: CORRECT if all results are right, or INCORRECT if any result is wrong. "
        "Your entire response must be only that one word: CORRECT or INCORRECT, nothing else."
    )
    return Agent(
        name="math-checker-agent",
        instructions=instructions,
        tools=[],  # No tools; simple yes/no validation
        model=model_override,
    )
