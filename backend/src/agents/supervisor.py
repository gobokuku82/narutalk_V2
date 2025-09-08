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
    
    # Analyze State to understand current progress
    results = state.get("results", {})
    errors = state.get("errors", [])
    
    # Check what agents have already run
    completed_agents = []
    if results.get("analytics"):
        completed_agents.append("analytics")
    if results.get("search"):
        completed_agents.append("search")
    if results.get("document"):
        completed_agents.append("document")
    if results.get("compliance"):
        completed_agents.append("compliance")
    
    # Default values for state updates
    progress_update = {
        "agent": "supervisor",
        "timestamp": datetime.now().isoformat(),
        "action": "routing_decision"
    }
    
    # Check if we're continuing an execution plan (agent returning to supervisor)
    execution_plan = state.get("execution_plan", [])
    current_step = state.get("current_step", 0)
    
    # If an agent just completed and we have more agents in the plan
    if execution_plan and current_step < len(execution_plan) and state.get("current_agent") != "supervisor":
        # Move to next step in execution plan
        next_step = current_step + 1
        
        if next_step < len(execution_plan):
            next_agent = execution_plan[next_step]
            progress_update["decision"] = next_agent
            progress_update["reason"] = f"Continuing execution plan: step {next_step + 1}/{len(execution_plan)}"
            
            routing_message = AIMessage(
                content=f"Proceeding to next agent in plan: {next_agent}",
                metadata={
                    "agent": "supervisor",
                    "task_type": next_agent,
                    "execution_step": next_step
                }
            )
            
            return {
                "messages": [routing_message],
                "current_agent": next_agent,
                "task_type": next_agent,
                "task_description": state.get("task_description", ""),
                "progress": [progress_update],
                "context": context,
                "execution_plan": execution_plan,
                "current_step": next_step,
                "next_agent": None
            }
        else:
            # All agents completed
            progress_update["decision"] = "end"
            progress_update["reason"] = "All agents in execution plan completed"
            
            completion_message = AIMessage(
                content="All planned agents have completed their tasks.",
                metadata={
                    "agent": "supervisor",
                    "task_type": "end",
                    "completed_agents": execution_plan
                }
            )
            
            return {
                "messages": [completion_message],
                "current_agent": "supervisor",
                "task_type": "end",
                "progress": [progress_update],
                "context": context,
                "is_complete": True,
                "execution_plan": execution_plan,
                "current_step": current_step,
                "next_agent": None
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
    
    # Check if there's a next_agent signal from previous agent (like compliance re-routing)
    next_agent = state.get("next_agent")
    if next_agent:
        # Analyze why re-routing is needed
        re_route_reason = ""
        if next_agent == "document" and context.get("document_revision_needed"):
            re_route_reason = "Document needs revision based on compliance violations"
        elif next_agent == "search" and context.get("search_refinement_needed"):
            re_route_reason = "Search refinement needed for compliance requirements"
        else:
            re_route_reason = f"Previous agent requested routing to {next_agent}"
        
        progress_update["decision"] = next_agent
        progress_update["auto_routed"] = True
        progress_update["reason"] = re_route_reason
        progress_update["state_based_routing"] = True
        
        routing_message = AIMessage(
            content=f"State-based routing to {next_agent}: {re_route_reason}",
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
        
        # Create routing prompt for execution plan with State awareness
        state_context = ""
        if completed_agents:
            state_context = f"\n\nAgents already executed: {', '.join(completed_agents)}"
        if errors:
            state_context += f"\nPrevious errors: {errors[:2]}"  # Show first 2 errors
        
        # Include insights from previous agent results
        if results.get("analytics", {}).get("key_insights"):
            insights = results["analytics"]["key_insights"]
            state_context += f"\nAnalytics insights: Health score={insights.get('performance_metrics', {}).get('health_score', 'N/A')}"
        if results.get("search", {}).get("raw_data"):
            search_data = results["search"]["raw_data"]
            state_context += f"\nSearch found: {len(search_data.get('companies_found', []))} companies, {len(search_data.get('products_found', []))} products"
        
        routing_prompt = f"""
        Analyze this user request and create an execution plan:
        "{user_request}"
        {state_context}
        
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
        4. Use State information to avoid redundant agent calls
        5. If agents have already run, don't include them again unless necessary
        
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
        
        # Update progress with State analysis
        progress_update["decision"] = first_agent
        progress_update["execution_plan"] = planned_agents
        progress_update["request"] = user_request[:100]  # First 100 chars
        progress_update["state_aware"] = True
        progress_update["agents_already_run"] = completed_agents
        
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
            "execution_plan": planned_agents,
            "current_step": 0,
            "next_agent": None
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
    
    # Direct mapping for agent names (used in execution plan)
    if task_type in ["analytics", "search", "document", "compliance"]:
        return task_type
    
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