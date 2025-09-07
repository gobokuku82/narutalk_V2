"""
Agent State definition for LangGraph 0.6.6
Following rules.md strictly
"""
from typing import Annotated, Literal, TypedDict, Any
from langgraph.graph.message import MessagesState, add_messages
from langchain_core.messages import BaseMessage
from enum import Enum


class TaskType(str, Enum):
    """Task types for agent routing"""
    ANALYZE = "analyze"
    SEARCH = "search"
    DOCUMENT = "document"
    VALIDATE = "validate"
    COMPLIANCE = "compliance"
    END = "end"


def add_progress(existing: list[dict], new: list[dict]) -> list[dict]:
    """Reducer function to accumulate progress logs"""
    if not existing:
        existing = []
    if not new:
        return existing
    return existing + new


class AgentState(MessagesState):
    """
    State for 영업 지원 AI system
    Extends MessagesState for message handling
    """
    # Current active agent
    current_agent: str
    
    # Task type for routing
    task_type: TaskType | str
    
    # Progress tracking with accumulator reducer
    progress: Annotated[list[dict], add_progress]
    
    # Context for sharing data between agents
    context: dict[str, Any]
    
    # Metadata for tracking
    metadata: dict[str, Any]
    
    # Current task description
    task_description: str
    
    # Results from each agent
    results: dict[str, Any]
    
    # Error tracking
    errors: list[str]
    
    # Completion status
    is_complete: bool