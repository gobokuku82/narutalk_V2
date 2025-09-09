"""
Dynamic Router Agent - Intelligent Routing with Parallel Execution Support
Handles dynamic routing based on execution plans and real-time conditions
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from ..state.enhanced_state import EnhancedAgentState


class DynamicRouter:
    """
    Intelligent router that handles:
    - Sequential execution
    - Parallel execution
    - Conditional routing
    - Error recovery and re-routing
    - Plan modification based on results
    """
    
    def __init__(self, llm_model: str = "gpt-4o-mini", temperature: float = 0):
        self.llm = ChatOpenAI(model=llm_model, temperature=temperature)
        
        # Routing rules and conditions
        self.routing_rules = {
            "success_routing": {
                "analytics": ["document"],  # After analytics, can go to document
                "search": ["analytics", "document"],  # After search, can analyze or document
                "document": ["compliance"],  # After document, check compliance
                "compliance": []  # Compliance is usually final
            },
            "failure_routing": {
                "analytics": ["search"],  # If analytics fails, try search first
                "search": ["analytics"],  # If search fails, try analytics with available data
                "document": ["analytics"],  # If document fails, go back to analytics
                "compliance": ["document"]  # If compliance fails, revise document
            }
        }
        
        # Conditional routing patterns
        self.conditional_patterns = {
            "low_confidence": {
                "condition": lambda state: state.get("intent_confidence", 1.0) < 0.5,
                "action": "request_clarification"
            },
            "missing_data": {
                "condition": lambda state: not state.get("results", {}).get("search"),
                "action": "route_to_search"
            },
            "compliance_required": {
                "condition": lambda state: state.get("context", {}).get("compliance_ready"),
                "action": "route_to_compliance"
            },
            "error_threshold": {
                "condition": lambda state: len(state.get("errors", [])) > 3,
                "action": "fallback_mode"
            }
        }
    
    def evaluate_conditions(self, state: EnhancedAgentState) -> Optional[str]:
        """
        Evaluate conditional routing patterns
        Returns action to take if condition is met
        """
        for pattern_name, pattern in self.conditional_patterns.items():
            if pattern["condition"](state):
                return pattern["action"]
        return None
    
    def determine_next_route(self, 
                            state: EnhancedAgentState,
                            current_agent: str,
                            execution_plan: Dict[str, Any]) -> Tuple[str, str]:
        """
        Determine the next routing decision
        Returns (next_agent, routing_reason)
        """
        # Check for conditional routing first
        conditional_action = self.evaluate_conditions(state)
        if conditional_action:
            if conditional_action == "request_clarification":
                return ("supervisor", "Low confidence - requesting clarification")
            elif conditional_action == "route_to_search":
                return ("search", "Missing data - routing to search")
            elif conditional_action == "route_to_compliance":
                return ("compliance", "Compliance check required")
            elif conditional_action == "fallback_mode":
                return ("supervisor", "Error threshold exceeded - fallback to supervisor")
        
        # Check execution plan
        sequential_tasks = execution_plan.get("sequential_tasks", [])
        parallel_tasks = execution_plan.get("parallel_tasks", [])
        
        # Get completed agents
        results = state.get("results", {})
        completed_agents = list(results.keys())
        
        # Find next sequential task
        for task in sequential_tasks:
            if task not in completed_agents:
                return (task, f"Next in sequential plan")
        
        # Check parallel tasks
        for group in parallel_tasks:
            pending_in_group = [a for a in group if a not in completed_agents]
            if pending_in_group:
                # Return first pending agent from parallel group
                # In real implementation, these would run in parallel
                return (pending_in_group[0], f"Part of parallel group: {group}")
        
        # Check if there are conditional tasks
        conditional_tasks = execution_plan.get("conditional_tasks", {})
        if conditional_tasks:
            condition_desc = conditional_tasks.get("condition", "")
            # Evaluate condition based on state
            # This is simplified - in real implementation, would evaluate actual condition
            if results.get("analytics", {}).get("score", 0) > 0.7:
                next_agents = conditional_tasks.get("if_true", [])
            else:
                next_agents = conditional_tasks.get("if_false", [])
            
            if next_agents and next_agents[0] not in completed_agents:
                return (next_agents[0], f"Conditional routing: {condition_desc}")
        
        # All tasks completed
        return ("END", "All tasks completed")
    
    def handle_agent_failure(self, 
                           state: EnhancedAgentState,
                           failed_agent: str) -> Tuple[str, str]:
        """
        Handle agent failure and determine recovery route
        """
        execution_plan = state.get("execution_plan", {})
        fallback_plans = execution_plan.get("fallback_plans", {})
        
        # Check if there's a specific fallback for this agent
        if failed_agent in fallback_plans and fallback_plans[failed_agent]:
            fallback_agent = fallback_plans[failed_agent][0]
            return (fallback_agent, f"Fallback from {failed_agent} failure")
        
        # Use general failure routing rules
        failure_routes = self.routing_rules["failure_routing"]
        if failed_agent in failure_routes and failure_routes[failed_agent]:
            recovery_agent = failure_routes[failed_agent][0]
            return (recovery_agent, f"Recovery route from {failed_agent}")
        
        # Default to supervisor for manual intervention
        return ("supervisor", f"No recovery route for {failed_agent} failure")
    
    def optimize_remaining_plan(self, 
                               state: EnhancedAgentState,
                               completed_agents: List[str]) -> Dict[str, Any]:
        """
        Optimize the remaining execution plan based on completed work
        """
        original_plan = state.get("execution_plan", {})
        
        # Filter out completed agents
        remaining_sequential = [
            task for task in original_plan.get("sequential_tasks", [])
            if task not in completed_agents
        ]
        
        remaining_parallel = []
        for group in original_plan.get("parallel_tasks", []):
            remaining_group = [a for a in group if a not in completed_agents]
            if remaining_group:
                remaining_parallel.append(remaining_group)
        
        # Check if we can parallelize some sequential tasks
        if len(remaining_sequential) > 1:
            # Check dependencies
            dependencies = original_plan.get("dependencies", {})
            
            # Find tasks with no dependencies on each other
            can_parallel = []
            cannot_parallel = []
            
            for task in remaining_sequential:
                task_deps = dependencies.get(task, [])
                # Check if dependencies are satisfied
                if all(dep in completed_agents for dep in task_deps):
                    can_parallel.append(task)
                else:
                    cannot_parallel.append(task)
            
            # Reorganize plan
            if len(can_parallel) > 1:
                remaining_parallel.insert(0, can_parallel)
                remaining_sequential = cannot_parallel
        
        optimized_plan = {
            **original_plan,
            "sequential_tasks": remaining_sequential,
            "parallel_tasks": remaining_parallel
        }
        
        return optimized_plan
    
    def calculate_progress(self, state: EnhancedAgentState) -> float:
        """
        Calculate overall progress percentage
        """
        execution_plan = state.get("execution_plan", {})
        
        # Count total tasks
        total_tasks = len(execution_plan.get("sequential_tasks", []))
        for group in execution_plan.get("parallel_tasks", []):
            total_tasks += len(group)
        
        if total_tasks == 0:
            return 100.0
        
        # Count completed tasks
        completed_tasks = len(state.get("results", {}))
        
        return (completed_tasks / total_tasks) * 100.0
    
    def create_routing_decision(self, 
                               state: EnhancedAgentState,
                               next_agent: str,
                               reason: str) -> Dict[str, Any]:
        """
        Create a routing decision with all necessary state updates
        """
        # Calculate progress
        progress = self.calculate_progress(state)
        
        # Estimate remaining time
        execution_plan = state.get("execution_plan", {})
        remaining_time = execution_plan.get("estimated_time", 10.0) * (1 - progress / 100.0)
        
        # Create routing history entry
        routing_entry = {
            "timestamp": datetime.now().isoformat(),
            "from_agent": state.get("current_agent", "unknown"),
            "to_agent": next_agent,
            "reason": reason,
            "progress": progress
        }
        
        # Update routing history
        routing_history = state.get("routing_history", [])
        routing_history.append(routing_entry)
        
        return {
            "next_agent": next_agent,
            "routing_reason": reason,
            "completion_percentage": progress,
            "estimated_remaining_time": remaining_time,
            "routing_history": routing_history
        }


def dynamic_router_agent(state: EnhancedAgentState) -> Dict[str, Any]:
    """
    Main dynamic router agent function for LangGraph
    Handles intelligent routing based on execution plans and conditions
    """
    # Initialize router
    router = DynamicRouter()
    
    # Get current state information
    current_agent = state.get("current_agent", "supervisor")
    execution_plan = state.get("execution_plan", {})
    results = state.get("results", {})
    errors = state.get("errors", [])
    
    # Check if we're recovering from an error
    if errors and state.get("error_recovery_attempts", 0) < state.get("max_recovery_attempts", 3):
        # Get the last error
        last_error = errors[-1] if errors else "Unknown error"
        
        # Determine recovery route
        failed_agent = current_agent
        next_agent, reason = router.handle_agent_failure(state, failed_agent)
        
        # Create recovery message
        recovery_message = AIMessage(
            content=f"Recovering from error in {failed_agent}. Routing to {next_agent}: {reason}",
            metadata={
                "agent": "dynamic_router",
                "action": "error_recovery",
                "failed_agent": failed_agent,
                "recovery_agent": next_agent
            }
        )
        
        # Update state
        return {
            "messages": [recovery_message],
            "current_agent": next_agent,
            "error_recovery_attempts": state.get("error_recovery_attempts", 0) + 1,
            "progress": [{
                "agent": "dynamic_router",
                "timestamp": datetime.now().isoformat(),
                "action": "error_recovery",
                "details": {"failed_agent": failed_agent, "recovery_agent": next_agent}
            }],
            **router.create_routing_decision(state, next_agent, reason)
        }
    
    # Normal routing based on execution plan
    if not execution_plan:
        # No execution plan - route to execution planner
        return {
            "current_agent": "execution_planner",
            "progress": [{
                "agent": "dynamic_router",
                "timestamp": datetime.now().isoformat(),
                "action": "no_plan",
                "details": {"routing_to": "execution_planner"}
            }]
        }
    
    # Determine next route
    next_agent, reason = router.determine_next_route(state, current_agent, execution_plan)
    
    # Check if we need to optimize the remaining plan
    completed_agents = list(results.keys())
    if len(completed_agents) > 0 and state.get("plan_version", 0) < 2:
        # Optimize remaining plan
        optimized_plan = router.optimize_remaining_plan(state, completed_agents)
        
        # Check if optimization changed the plan
        if optimized_plan != execution_plan:
            optimization_message = AIMessage(
                content=f"Optimized execution plan. Next: {next_agent}",
                metadata={
                    "agent": "dynamic_router",
                    "action": "plan_optimized",
                    "optimization_applied": True
                }
            )
            
            return {
                "messages": [optimization_message],
                "execution_plan": optimized_plan,
                "plan_version": state.get("plan_version", 0) + 1,
                "current_agent": next_agent,
                "progress": [{
                    "agent": "dynamic_router",
                    "timestamp": datetime.now().isoformat(),
                    "action": "plan_optimized",
                    "details": {"next_agent": next_agent}
                }],
                **router.create_routing_decision(state, next_agent, reason)
            }
    
    # Handle parallel execution
    parallel_agents = state.get("parallel_agents", [])
    if parallel_agents and next_agent in parallel_agents:
        # This is part of a parallel group
        parallel_message = AIMessage(
            content=f"Executing parallel group: {parallel_agents}. Starting with {next_agent}",
            metadata={
                "agent": "dynamic_router",
                "action": "parallel_execution",
                "parallel_group": parallel_agents,
                "current_execution": next_agent
            }
        )
        
        # In a real implementation, we would spawn parallel tasks here
        # For now, we execute them sequentially but track as parallel
        return {
            "messages": [parallel_message],
            "current_agent": next_agent,
            "parallel_execution_active": True,
            "progress": [{
                "agent": "dynamic_router",
                "timestamp": datetime.now().isoformat(),
                "action": "parallel_routing",
                "details": {
                    "parallel_group": parallel_agents,
                    "executing": next_agent
                }
            }],
            **router.create_routing_decision(state, next_agent, reason)
        }
    
    # Check if all tasks are completed
    if next_agent == "END":
        completion_message = AIMessage(
            content="All tasks completed successfully. Execution plan finished.",
            metadata={
                "agent": "dynamic_router",
                "action": "execution_complete",
                "final_progress": 100.0
            }
        )
        
        return {
            "messages": [completion_message],
            "current_agent": "supervisor",
            "is_complete": True,
            "completion_percentage": 100.0,
            "progress": [{
                "agent": "dynamic_router",
                "timestamp": datetime.now().isoformat(),
                "action": "execution_complete",
                "details": {"completed_agents": completed_agents}
            }]
        }
    
    # Normal routing
    routing_message = AIMessage(
        content=f"Routing to {next_agent}: {reason}",
        metadata={
            "agent": "dynamic_router",
            "action": "routing",
            "target_agent": next_agent,
            "reason": reason
        }
    )
    
    return {
        "messages": [routing_message],
        "current_agent": next_agent,
        "progress": [{
            "agent": "dynamic_router",
            "timestamp": datetime.now().isoformat(),
            "action": "routing",
            "details": {"to_agent": next_agent, "reason": reason}
        }],
        **router.create_routing_decision(state, next_agent, reason)
    }


def route_from_dynamic_router(state: EnhancedAgentState) -> str:
    """
    Routing function for conditional edges from dynamic router
    Returns the next node based on routing decision
    """
    next_agent = state.get("next_agent", "supervisor")
    
    # Map to actual node names
    if next_agent == "END":
        return "end"
    elif next_agent in ["analytics", "search", "document", "compliance"]:
        return next_agent
    elif next_agent in ["query_analyzer", "execution_planner"]:
        return next_agent
    else:
        return "supervisor"