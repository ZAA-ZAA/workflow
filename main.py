import json
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI

from agents import execute_tool_by_name, get_tool_specs
from app.agents.zoey_agent import create_zoey_agent
from workflow.basic_workflow import run_workflow

app = FastAPI()


class ChatRequest(BaseModel):
    prompt: str


class ZoeyChatRequest(BaseModel):
    prompt: str
    model: str | None = None


class MathWorkflowRequest(BaseModel):
    num1: float
    num2: float


def _get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # Fail fast with a helpful error when the key is missing.
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)


@app.get("/health")
def health_check():
    """Return a simple health status response."""
    return {"status": "ok"}


@app.post("/agent/chat")
def chat(request: ChatRequest):
    """Minimal chat endpoint that forwards the prompt to OpenAI."""
    client = _get_openai_client()
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Swap to another model if preferred.
            messages=[{"role": "user", "content": request.prompt}],
        )
        # Return the first choice text content.
        return {"reply": response.choices[0].message.content}
    except Exception as exc:  # Broad catch to relay useful error info.
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/agent/zoey/chat")
def zoey_chat(request: ZoeyChatRequest):
    """Chat with the Zoey agent, which can call math tools."""
    agent = create_zoey_agent(model_override=request.model)
    client = _get_openai_client()

    messages = [
        {"role": "system", "content": agent.instructions},
        {"role": "user", "content": request.prompt},
    ]
    tools = get_tool_specs(agent.tools)
    model = agent.model or "gpt-4o-mini"

    try:
        first = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        first_message = first.choices[0].message

        # If the model decides to invoke a tool, execute and follow up.
        if first_message.tool_calls:
            messages.append(
                {
                    "role": "assistant",
                    "content": first_message.content or "",
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": call.function.name,
                                "arguments": call.function.arguments,
                            },
                        }
                        for call in first_message.tool_calls
                    ],
                }
            )

            for call in first_message.tool_calls:
                args = json.loads(call.function.arguments or "{}")
                result = execute_tool_by_name(agent.tools, call.function.name, args)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": str(result),
                    }
                )

            follow_up = client.chat.completions.create(
                model=model,
                messages=messages,
            )
            return {"reply": follow_up.choices[0].message.content}

        # No tool use; return the first reply.
        return {"reply": first_message.content}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/workflow/math")
def math_workflow(request: MathWorkflowRequest):
    """
    Execute the basic math workflow with two numbers.
    
    This workflow performs all 4 basic math operations:
    - Addition
    - Subtraction
    - Multiplication
    - Division (with zero handling)
    """
    try:
        # Run the workflow
        result = run_workflow(request.num1, request.num2)
        
        # Return the results
        return {
            "num1": result["num1"],
            "num2": result["num2"],
            "results": {
                "addition": result["add_result"],
                "subtraction": result["subtract_result"],
                "multiplication": result["multiply_result"],
                "division": result["divide_result"],
            },
            "status": result["step"]
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

