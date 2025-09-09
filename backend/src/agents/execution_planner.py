"""
Execution Planner Agent - Dynamic Execution Plan Optimization
Receives analysis from Query Analyzer and creates optimized execution plans
"""
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime
import json
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from ..state.enhanced_state import EnhancedAgentState


class ExecutionPlanner:
    """
    Creates and optimizes execution plans based on query analysis
    Handles dependencies, parallel execution, and conditional routing
    """
    
    def __init__(self, llm_model: str = "gpt-4o-mini", temperature: float = 0):
        self.llm = ChatOpenAI(model=llm_model, temperature=temperature)
        
        # Agent execution characteristics
        self.agent_characteristics = {
            "analytics": {
                "avg_time": 3.0,
                "can_parallel": True,
                "requires_data": True,
                "produces": ["insights", "metrics", "charts"],
                "dependencies": []
            },
            "search": {
                "avg_time": 2.0,
                "can_parallel": True,
                "requires_data": False,
                "produces": ["search_results", "raw_data"],
                "dependencies": []
            },
            "document": {
                "avg_time": 4.0,
                "can_parallel": False,
                "requires_data": True,
                "produces": ["documents", "reports"],
                "dependencies": ["analytics", "search"]  # Usually needs other results
            },
            "compliance": {
                "avg_time": 2.5,
                "can_parallel": False,
                "requires_data": True,
                "produces": ["validation_results", "compliance_report"],
                "dependencies": ["document"]  # Often validates documents
            }
        }
    
    def analyze_dependencies(self, required_agents: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
        """
        Analyze dependencies between agents
        Returns a dependency graph
        """
        dependencies = {}
        
        for agent_info in required_agents:
            agent_name = agent_info["agent"]
            agent_deps = set(agent_info.get("dependencies", []))
            
            # Add characteristic-based dependencies
            char_deps = self.agent_characteristics.get(agent_name, {}).get("dependencies", [])
            for dep in char_deps:
                # Only add if the dependency agent is also required
                if any(a["agent"] == dep for a in required_agents):
                    agent_deps.add(dep)
            
            dependencies[agent_name] = agent_deps
        
        return dependencies
    
    def identify_parallel_groups(self, required_agents: List[str], dependencies: Dict[str, Set[str]]) -> List[List[str]]:
        """
        Identify groups of agents that can run in parallel
        Uses topological sorting with level identification
        """
        # Create reverse dependency map (who depends on me)
        reverse_deps = {agent: set() for agent in required_agents}
        for agent, deps in dependencies.items():
            for dep in deps:
                if dep in reverse_deps:
                    reverse_deps[dep].add(agent)
        
        # Topological sort with levels
        levels = []
        processed = set()
        remaining = set(required_agents)
        
        while remaining:
            # Find agents with no unprocessed dependencies
            current_level = []
            for agent in remaining:
                agent_deps = dependencies.get(agent, set())
                if agent_deps.issubset(processed):
                    current_level.append(agent)
            
            if not current_level:
                # Circular dependency or error - fall back to sequential
                return [[agent] for agent in remaining]
            
            levels.append(current_level)
            processed.update(current_level)
            remaining.difference_update(current_level)
        
        return levels
    
    def optimize_execution_order(self, parallel_groups: List[List[str]]) -> List[List[str]]:
        """
        Optimize execution order within parallel groups
        Prioritize faster agents and critical path
        """
        optimized_groups = []
        
        for group in parallel_groups:
            if len(group) <= 1:
                optimized_groups.append(group)
                continue
            
            # Sort by estimated execution time (faster first)
            sorted_group = sorted(group, 
                key=lambda a: self.agent_characteristics.get(a, {}).get("avg_time", 5.0))
            
            # Check if any agent in the group cannot be parallelized
            non_parallel = [a for a in sorted_group 
                           if not self.agent_characteristics.get(a, {}).get("can_parallel", True)]
            
            if non_parallel:
                # Split into sequential execution
                for agent in non_parallel:
                    optimized_groups.append([agent])
                parallel_agents = [a for a in sorted_group if a not in non_parallel]
                if parallel_agents:
                    optimized_groups.append(parallel_agents)
            else:
                optimized_groups.append(sorted_group)
        
        return optimized_groups
    
    def calculate_estimated_time(self, execution_plan: Dict[str, Any]) -> float:
        """
        Calculate estimated execution time for the plan
        Considers parallel execution
        """
        total_time = 0.0
        
        # Sequential tasks
        for task in execution_plan.get("sequential_tasks", []):
            total_time += self.agent_characteristics.get(task, {}).get("avg_time", 3.0)
        
        # Parallel groups (take max time in each group)
        for group in execution_plan.get("parallel_tasks", []):
            if group:
                group_time = max(
                    self.agent_characteristics.get(agent, {}).get("avg_time", 3.0)
                    for agent in group
                )
                total_time += group_time
        
        return total_time
    
    def create_fallback_plans(self, required_agents: List[str]) -> Dict[str, List[str]]:
        """
        Create fallback plans for each agent in case of failure
        """
        fallback_plans = {}
        
        for agent in required_agents:
            if agent == "search":
                # If search fails, try analytics with available data
                fallback_plans[agent] = ["analytics"]
            elif agent == "document":
                # If document generation fails, create summary
                fallback_plans[agent] = ["analytics"]  # Analytics can provide summary
            elif agent == "compliance":
                # If compliance fails, flag for manual review
                fallback_plans[agent] = []  # No automated fallback
            else:
                fallback_plans[agent] = []
        
        return fallback_plans
    
    def identify_optimization_opportunities(self, 
                                          execution_plan: Dict[str, Any],
                                          query_analysis: Dict[str, Any]) -> List[str]:
        """
        Identify opportunities for optimization
        """
        optimizations = []
        
        # Check for caching opportunities
        if "temporal" in query_analysis.get("entities", {}):
            temporal_values = query_analysis["entities"]["temporal"]
            if any("지난" in t or "작년" in t or "Q" in t for t in temporal_values):
                optimizations.append("Cache historical data for faster retrieval")
        
        # Check for parallel execution
        parallel_groups = execution_plan.get("parallel_tasks", [])
        if len(parallel_groups) > 0:
            total_parallel = sum(len(g) for g in parallel_groups)
            if total_parallel > 2:
                optimizations.append(f"Parallel execution of {total_parallel} agents will reduce total time")
        
        # Check for redundant operations
        sequential = execution_plan.get("sequential_tasks", [])
        if "search" in sequential and "analytics" in sequential:
            optimizations.append("Consider combining search and analytics operations")
        
        # Check for batch processing
        if len(execution_plan.get("required_agents", [])) > 3:
            optimizations.append("Consider batch processing for multiple similar operations")
        
        return optimizations
    
    def build_execution_plan_with_llm(self, 
                                      query_analysis: Dict[str, Any],
                                      state_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use LLM to refine and validate the execution plan
        """
        required_agents = [a["agent"] for a in query_analysis.get("required_agents", [])]
        
        # Analyze dependencies
        dependencies = self.analyze_dependencies(query_analysis.get("required_agents", []))
        
        # Identify parallel execution groups
        parallel_groups = self.identify_parallel_groups(required_agents, dependencies)
        
        # Optimize execution order
        optimized_groups = self.optimize_execution_order(parallel_groups)
        
        # Build execution plan structure
        execution_plan = {
            "sequential_tasks": [],
            "parallel_tasks": [],
            "conditional_tasks": {},
            "dependencies": {k: list(v) for k, v in dependencies.items()},
            "fallback_plans": self.create_fallback_plans(required_agents),
            "optimization_hints": []
        }
        
        # Convert optimized groups to plan format
        for group in optimized_groups:
            if len(group) == 1:
                execution_plan["sequential_tasks"].append(group[0])
            else:
                execution_plan["parallel_tasks"].append(group)
        
        # Calculate estimated time
        execution_plan["estimated_time"] = self.calculate_estimated_time(execution_plan)
        
        # Identify optimizations
        execution_plan["optimization_hints"] = self.identify_optimization_opportunities(
            execution_plan, query_analysis
        )
        
        # Determine priority based on confidence and complexity
        confidence = query_analysis.get("confidence", 0.7)
        complexity = query_analysis.get("query_complexity", "moderate")
        
        if confidence > 0.8 and complexity in ["simple", "moderate"]:
            execution_plan["priority_level"] = "medium"
        elif confidence > 0.8 and complexity in ["complex", "advanced"]:
            execution_plan["priority_level"] = "high"
        elif confidence < 0.5:
            execution_plan["priority_level"] = "low"
        else:
            execution_plan["priority_level"] = "medium"
        
        return execution_plan


def execution_planner_agent(state: EnhancedAgentState) -> Dict[str, Any]:
    """
    Main execution planner agent function for LangGraph
    Creates optimized execution plans based on query analysis
    """
    # Check if query analysis exists
    query_analysis = state.get("query_analysis")
    if not query_analysis:
        return {
            "errors": ["No query analysis found. Query Analyzer must run first."],
            "current_agent": "query_analyzer"
        }
    
    # Initialize planner
    planner = ExecutionPlanner()
    start_time = datetime.now()
    
    # Build state context
    state_context = {
        "previous_results": state.get("results", {}),
        "errors": state.get("errors", []),
        "context": state.get("context", {}),
        "user_preferences": state.get("user_preferences", {})
    }
    
    # Create execution plan
    execution_plan = planner.build_execution_plan_with_llm(query_analysis, state_context)
    
    # Validate the plan
    if not execution_plan.get("sequential_tasks") and not execution_plan.get("parallel_tasks"):
        # No tasks to execute - fallback to simple analytics
        execution_plan["sequential_tasks"] = ["analytics"]
    
    # Calculate total steps
    total_steps = len(execution_plan.get("sequential_tasks", []))
    total_steps += sum(len(group) for group in execution_plan.get("parallel_tasks", []))
    
    # Prepare detailed execution schedule
    execution_schedule = []
    step_number = 1
    
    # Add sequential tasks to schedule
    for task in execution_plan.get("sequential_tasks", []):
        execution_schedule.append({
            "step": step_number,
            "type": "sequential",
            "agents": [task],
            "estimated_time": planner.agent_characteristics.get(task, {}).get("avg_time", 3.0)
        })
        step_number += 1
    
    # Add parallel groups to schedule
    for group in execution_plan.get("parallel_tasks", []):
        execution_schedule.append({
            "step": step_number,
            "type": "parallel",
            "agents": group,
            "estimated_time": max(
                planner.agent_characteristics.get(a, {}).get("avg_time", 3.0)
                for a in group
            )
        })
        step_number += 1
    
    # Calculate processing time
    processing_time = (datetime.now() - start_time).total_seconds()
    
    # Update progress
    progress_entry = {
        "agent": "execution_planner",
        "timestamp": datetime.now().isoformat(),
        "action": "plan_created",
        "details": {
            "total_steps": total_steps,
            "sequential_count": len(execution_plan.get("sequential_tasks", [])),
            "parallel_groups": len(execution_plan.get("parallel_tasks", [])),
            "estimated_time": execution_plan["estimated_time"],
            "priority": execution_plan.get("priority_level", "medium")
        }
    }
    
    # Prepare response message
    plan_summary = f"Execution plan created:\n"
    plan_summary += f"• Total agents: {total_steps}\n"
    plan_summary += f"• Estimated time: {execution_plan['estimated_time']:.1f} seconds\n"
    plan_summary += f"• Priority: {execution_plan.get('priority_level', 'medium')}\n"
    
    if execution_plan.get("parallel_tasks"):
        plan_summary += f"• Parallel execution enabled for {sum(len(g) for g in execution_plan['parallel_tasks'])} agents\n"
    
    planning_message = AIMessage(
        content=plan_summary,
        metadata={
            "agent": "execution_planner",
            "plan_created": True,
            "total_steps": total_steps,
            "execution_schedule": execution_schedule
        }
    )
    
    # Determine next agent (first in execution plan)
    next_agent = "dynamic_router"  # Router will handle actual execution
    
    # If we have a simple sequential plan, we can go directly to the first agent
    if execution_plan.get("sequential_tasks") and not execution_plan.get("parallel_tasks"):
        next_agent = execution_plan["sequential_tasks"][0]
    
    # Return state updates
    return {
        "messages": [planning_message],
        "execution_plan": execution_plan,
        "plan_version": state.get("plan_version", 0) + 1,
        "plan_status": "ready",
        "original_plan": execution_plan if not state.get("original_plan") else state.get("original_plan"),
        "progress": [progress_entry],
        "estimated_remaining_time": execution_plan["estimated_time"],
        "current_agent": next_agent,
        "next_agents": execution_plan.get("sequential_tasks", []) + 
                      [a for group in execution_plan.get("parallel_tasks", []) for a in group],
        "parallel_agents": execution_plan.get("parallel_tasks", [[]])[0] if execution_plan.get("parallel_tasks") else [],
        "suggested_optimizations": execution_plan.get("optimization_hints", []),
        "context": {
            **state.get("context", {}),
            "execution_plan_ready": True,
            "execution_schedule": execution_schedule
        }
    }