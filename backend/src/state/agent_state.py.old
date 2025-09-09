"""
Agent State definition for LangGraph 0.6.6
Following rules.md strictly
"""
from typing import Annotated, Literal, TypedDict, Any, Optional
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


class AgentResults(TypedDict, total=False):
    """State의 results 필드 구조 정의 - 에이전트 간 정보 공유용"""
    analytics: dict  # Analytics 에이전트 결과 (KPIs, insights, metrics)
    search: dict     # Search 에이전트 결과 (company info, products)
    document: dict   # Document 에이전트 결과 (generated docs)
    compliance: dict # Compliance 에이전트 결과 (validation results)


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
    
    # Results from each agent - 타입 힌트 강화
    results: AgentResults
    
    # Error tracking
    errors: list[str]
    
    # Completion status
    is_complete: bool
    
    # Execution plan for multi-agent coordination
    execution_plan: list[str]
    
    # Next agent to route to
    next_agent: str | None
    
    # Current step in execution plan
    current_step: int
    
    # Parallel execution support
    parallel_tasks: list[str]
    
    # Agent dependencies
    dependencies: dict[str, list[str]]