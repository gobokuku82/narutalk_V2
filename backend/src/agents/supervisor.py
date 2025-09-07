"""
Supervisor Agent for LangGraph 0.6.6
Manages task routing and coordination between agents
"""
from typing import Dict, Any
from datetime import datetime
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from ..state.agent_state import AgentState, TaskType
import json


def supervisor_agent(state: AgentState) -> dict:
    """
    Enhanced Supervisor agent with auto-routing capability
    Following rules.md: Node functions MUST return dict
    Supports document → compliance auto-routing
    """
    # Initialize LLM for decision making
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    # Get the last message to understand the request
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else None
    context = state.get("context", {})
    
    # Default values for state updates
    progress_update = {
        "agent": "supervisor",
        "timestamp": datetime.now().isoformat(),
        "action": "routing_decision"
    }
    
    # Check for auto-routing from document to compliance
    if context.get("compliance_ready", False) and not context.get("compliance_checked", False):
        # Auto-route to compliance after document generation
        progress_update["decision"] = "compliance"
        progress_update["auto_routed"] = True
        progress_update["reason"] = "Document requires compliance validation"
        
        routing_message = AIMessage(
            content=f"Auto-routing to compliance agent for document validation.",
            metadata={
                "agent": "supervisor",
                "task_type": "compliance",
                "auto_routed": True
            }
        )
        
        return {
            "messages": [routing_message],
            "current_agent": "compliance",
            "task_type": "compliance",
            "task_description": f"Validate document {context.get('document_id', 'unknown')}",
            "progress": [progress_update],
            "context": {**context, "compliance_checking": True}
        }
    
    # Check if there's a next_agent signal from previous agent
    next_agent = state.get("next_agent")
    if next_agent:
        progress_update["decision"] = next_agent
        progress_update["auto_routed"] = True
        progress_update["reason"] = f"Previous agent requested routing to {next_agent}"
        
        routing_message = AIMessage(
            content=f"Auto-routing to {next_agent} agent as requested.",
            metadata={
                "agent": "supervisor",
                "task_type": next_agent,
                "auto_routed": True
            }
        )
        
        return {
            "messages": [routing_message],
            "current_agent": next_agent,
            "task_type": next_agent,
            "task_description": state.get("task_description", ""),
            "progress": [progress_update],
            "context": context
        }
    
    # Normal routing based on user request
    if last_message and isinstance(last_message, HumanMessage):
        user_request = last_message.content
        
        # Create routing prompt
        routing_prompt = f"""
        Analyze this user request and determine the appropriate task type:
        "{user_request}"
        
        Available task types:
        - analyze: For data analysis, metrics, and insights
        - search: For information retrieval and research
        - document: For report generation and documentation
        - compliance: For regulatory checks and validation
        - validate: For data validation and verification
        - end: If the task is complete
        
        Respond with ONLY the task type keyword.
        """
        
        # Get routing decision
        response = llm.invoke([HumanMessage(content=routing_prompt)])
        task_type = response.content.strip().lower()
        
        # Validate task type
        valid_types = ["analyze", "search", "document", "compliance", "validate", "end"]
        if task_type not in valid_types:
            task_type = "analyze"  # Default fallback
        
        # Update progress
        progress_update["decision"] = task_type
        progress_update["request"] = user_request[:100]  # First 100 chars
        
        # Prepare response message
        routing_message = AIMessage(
            content=f"Task routed to {task_type} agent for processing.",
            metadata={"agent": "supervisor", "task_type": task_type}
        )
        
        return {
            "messages": [routing_message],
            "current_agent": task_type,
            "task_type": task_type,
            "task_description": user_request,
            "progress": [progress_update],
            "context": state.get("context", {})
        }
    else:
        # No valid message to process
        return {
            "messages": [AIMessage(content="No task to process. Please provide a request.")],
            "current_agent": "supervisor",
            "task_type": "end",
            "progress": [progress_update],
            "is_complete": True
        }


def route_by_task_type(state: AgentState) -> str:
    """
    Routing function for conditional edges
    Returns the next node based on task_type
    """
    task_type = state.get("task_type", "end")
    
    # Map task types to agent nodes
    routing_map = {
        "analyze": "analytics",
        "search": "search",
        "document": "document",
        "compliance": "compliance",
        "validate": "compliance",  # Validation handled by compliance
        "end": "end"
    }
    
    return routing_map.get(task_type, "end")