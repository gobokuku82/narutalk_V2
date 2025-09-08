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
        
        # Create routing prompt for execution plan
        routing_prompt = f"""
        Analyze this user request and create an execution plan:
        "{user_request}"
        
        Available agents:
        - analytics: For data analysis, metrics, KPIs, and insights
        - search: For information retrieval and research
        - document: For report generation and documentation
        - compliance: For regulatory checks and validation
        
        Determine which agents are needed and in what order.
        Consider that:
        1. Simple queries may need only one agent
        2. Complex requests may need multiple agents in sequence
        3. Document creation often requires compliance check afterwards
        
        Respond in JSON format with the execution plan:
        {{"agents": ["agent1", "agent2"], "reason": "brief explanation"}}
        
        Examples:
        - "지난 분기 매출 분석" → {{"agents": ["analytics"], "reason": "Sales data analysis"}}
        - "서울대병원 정보 찾고 보고서 작성" → {{"agents": ["search", "document"], "reason": "Search then document"}}
        - "제안서 작성하고 규정 검토" → {{"agents": ["document", "compliance"], "reason": "Document then compliance"}}
        """
        
        # Get routing decision
        response = llm.invoke([HumanMessage(content=routing_prompt)])
        
        # Parse execution plan
        try:
            import re
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                execution_plan = json.loads(json_match.group())
            else:
                # Fallback to simple analytics if parsing fails
                execution_plan = {"agents": ["analytics"], "reason": "Default fallback"}
        except:
            execution_plan = {"agents": ["analytics"], "reason": "Parsing error fallback"}
        
        # Get the planned agents and validate them
        planned_agents = execution_plan.get("agents", ["analytics"])
        valid_agents = ["analytics", "search", "document", "compliance"]
        planned_agents = [a for a in planned_agents if a in valid_agents]
        
        if not planned_agents:
            planned_agents = ["analytics"]  # Default fallback
        
        # Get the first agent to execute
        first_agent = planned_agents[0]
        
        # Store execution plan in context
        updated_context = state.get("context", {})
        updated_context["execution_plan"] = planned_agents
        updated_context["plan_reason"] = execution_plan.get("reason", "")
        updated_context["current_step"] = 0
        updated_context["total_steps"] = len(planned_agents)
        
        # Update progress
        progress_update["decision"] = first_agent
        progress_update["execution_plan"] = planned_agents
        progress_update["request"] = user_request[:100]  # First 100 chars
        
        # Prepare response message with execution plan
        routing_message = AIMessage(
            content=f"Execution plan: {' → '.join(planned_agents)}. Starting with {first_agent} agent.",
            metadata={
                "agent": "supervisor", 
                "task_type": first_agent,
                "execution_plan": planned_agents,
                "total_steps": len(planned_agents)
            }
        )
        
        return {
            "messages": [routing_message],
            "current_agent": first_agent,
            "task_type": first_agent,
            "task_description": user_request,
            "progress": [progress_update],
            "context": updated_context,
            "execution_plan": planned_agents
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