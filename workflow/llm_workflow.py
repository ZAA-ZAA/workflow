"""
LangGraph Workflow with LLM Integration

This example demonstrates how to integrate OpenAI with LangGraph for
an agent-based workflow with tool calling capabilities.
"""

import os
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages


# Define the agent state
class AgentState(TypedDict):
    """State for the agent workflow with message history."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    next_step: str


def create_llm_node(llm):
    """
    Creates a node that calls the LLM.
    
    Args:
        llm: The language model to use
        
    Returns:
        A function that processes state through the LLM
    """
    def call_llm(state: AgentState) -> AgentState:
        """Call the LLM with the current message history."""
        print("🤖 Calling LLM...")
        messages = state["messages"]
        response = llm.invoke(messages)
        print(f"💬 LLM Response: {response.content[:100]}...")
        
        return {
            "messages": [response],
            "next_step": "complete"
        }
    
    return call_llm


def should_continue(state: AgentState) -> str:
    """
    Determine if we should continue or end the workflow.
    
    This is where you would check for tool calls or other conditions.
    """
    last_message = state["messages"][-1]
    
    # If the last message is from the AI and doesn't require further action
    if isinstance(last_message, AIMessage):
        return "end"
    
    return "continue"


def create_llm_workflow(model_name: str = "gpt-4o-mini") -> StateGraph:
    """
    Creates a simple LangGraph workflow with LLM integration.
    
    Args:
        model_name: OpenAI model to use (default: gpt-4o-mini)
        
    Returns:
        Compiled LangGraph workflow
    """
    # Initialize the LLM
    llm = ChatOpenAI(
        model=model_name,
        temperature=0.7,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Create the state graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    llm_node = create_llm_node(llm)
    workflow.add_node("llm", llm_node)
    
    # Set entry point
    workflow.set_entry_point("llm")
    
    # Add conditional edge
    workflow.add_conditional_edges(
        "llm",
        should_continue,
        {
            "continue": "llm",
            "end": END
        }
    )
    
    return workflow


def run_llm_workflow(user_input: str, system_prompt: str = None) -> dict:
    """
    Execute the LLM workflow with user input.
    
    Args:
        user_input: The user's message/query
        system_prompt: Optional system prompt to set context
        
    Returns:
        dict: The final state with all messages
    """
    print("\n" + "="*60)
    print("🚀 Starting LLM Workflow")
    print("="*60 + "\n")
    
    # Create and compile the workflow
    workflow = create_llm_workflow()
    app = workflow.compile()
    
    # Prepare initial messages
    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=user_input))
    
    # Initial state
    initial_state = {
        "messages": messages,
        "next_step": "start"
    }
    
    # Run the workflow
    final_state = app.invoke(initial_state)
    
    print("\n" + "="*60)
    print("✅ LLM Workflow Complete!")
    print("="*60)
    
    # Extract the assistant's response
    assistant_messages = [
        msg for msg in final_state["messages"] 
        if isinstance(msg, AIMessage)
    ]
    
    if assistant_messages:
        print(f"\n🤖 Assistant: {assistant_messages[-1].content}\n")
    
    return final_state


if __name__ == "__main__":
    # Example usage
    system_prompt = "You are a helpful AI assistant that provides concise and accurate answers."
    user_query = "What is LangGraph and why is it useful?"
    
    result = run_llm_workflow(user_query, system_prompt)
    
    print("\n📊 Message History:")
    for i, msg in enumerate(result["messages"], 1):
        msg_type = type(msg).__name__
        content_preview = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
        print(f"  {i}. [{msg_type}] {content_preview}")
