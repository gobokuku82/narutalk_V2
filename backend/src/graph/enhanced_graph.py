"""
Enhanced Graph Structure with Advanced Query Analysis
Integrates Query Analyzer, Execution Planner, and Dynamic Router
"""
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition

# Import enhanced state
from ..state.enhanced_state import EnhancedAgentState, create_initial_state

# Import new intelligent agents
from ..agents.query_analyzer import query_analyzer_agent
from ..agents.execution_planner import execution_planner_agent
from ..agents.dynamic_router import dynamic_router_agent, route_from_dynamic_router

# Import existing agents
from ..agents.supervisor import supervisor_agent
from ..agents.analytics import analytics_agent
from ..agents.search import search_agent
from ..agents.document import document_agent
from ..agents.compliance import compliance_agent

# Import tools
from ..tools.search_tools import search_internal_db, search_vector_db
from ..tools.analytics_tools import analyze_sales_trend, calculate_kpis


def create_enhanced_graph():
    """
    Create the enhanced LangGraph with advanced query analysis
    
    Architecture:
    1. User Query → Query Analyzer (Intent & Entity extraction)
    2. Query Analyzer → Execution Planner (Create optimized plan)
    3. Execution Planner → Dynamic Router (Execute plan)
    4. Dynamic Router → Agents (Based on plan)
    5. Agents → Dynamic Router (For next routing)
    6. Complete → Supervisor (Final review)
    """
    
    # Initialize StateGraph with EnhancedAgentState
    graph = StateGraph(EnhancedAgentState)
    
    # ===== Add Intelligent Control Nodes =====
    graph.add_node("query_analyzer", query_analyzer_agent)
    graph.add_node("execution_planner", execution_planner_agent)
    graph.add_node("dynamic_router", dynamic_router_agent)
    
    # ===== Add Supervisor Node =====
    graph.add_node("supervisor", supervisor_agent)
    
    # ===== Add Agent Nodes =====
    graph.add_node("analytics", analytics_agent)
    graph.add_node("search", search_agent)
    graph.add_node("document", document_agent)
    graph.add_node("compliance", compliance_agent)
    
    # ===== Add Tool Nodes =====
    # Search tools
    search_tools = [search_internal_db, search_vector_db]
    search_tool_node = ToolNode(search_tools)
    graph.add_node("search_tools", search_tool_node)
    
    # Analytics tools
    analytics_tools = [analyze_sales_trend, calculate_kpis]
    analytics_tool_node = ToolNode(analytics_tools)
    graph.add_node("analytics_tools", analytics_tool_node)
    
    # ===== Define Entry Point =====
    # Start → Query Analyzer (for new queries)
    graph.add_edge(START, "query_analyzer")
    
    # ===== Define Core Flow =====
    # Query Analyzer → Execution Planner
    graph.add_edge("query_analyzer", "execution_planner")
    
    # Execution Planner → Dynamic Router
    graph.add_edge("execution_planner", "dynamic_router")
    
    # ===== Dynamic Router Conditional Edges =====
    graph.add_conditional_edges(
        "dynamic_router",
        route_from_dynamic_router,
        {
            "analytics": "analytics",
            "search": "search",
            "document": "document",
            "compliance": "compliance",
            "supervisor": "supervisor",
            "query_analyzer": "query_analyzer",
            "execution_planner": "execution_planner",
            "end": END
        }
    )
    
    # ===== Agent Return Paths =====
    # All agents return to dynamic router for next routing decision
    graph.add_edge("analytics", "dynamic_router")
    graph.add_edge("search", "dynamic_router")
    graph.add_edge("document", "dynamic_router")
    graph.add_edge("compliance", "dynamic_router")
    
    # ===== Supervisor Routing =====
    # Supervisor can route to any agent or back to query analyzer
    def route_from_supervisor(state: EnhancedAgentState) -> str:
        """Route from supervisor based on state"""
        # Check if complete
        if state.get("is_complete", False):
            return "end"
        
        # Check if needs re-analysis
        if state.get("requires_reanalysis", False):
            return "query_analyzer"
        
        # Check next agent from state
        next_agent = state.get("next_agent", "")
        if next_agent in ["analytics", "search", "document", "compliance"]:
            return next_agent
        
        # Default to dynamic router
        return "dynamic_router"
    
    graph.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "analytics": "analytics",
            "search": "search",
            "document": "document",
            "compliance": "compliance",
            "query_analyzer": "query_analyzer",
            "dynamic_router": "dynamic_router",
            "end": END
        }
    )
    
    # ===== Tool Integration =====
    # Search agent can use tools
    graph.add_conditional_edges(
        "search",
        tools_condition,
        {
            "tools": "search_tools",
            END: "dynamic_router"  # Return to router after search
        }
    )
    graph.add_edge("search_tools", "search")
    
    # Analytics agent can use tools
    graph.add_conditional_edges(
        "analytics",
        tools_condition,
        {
            "tools": "analytics_tools",
            END: "dynamic_router"  # Return to router after analytics
        }
    )
    graph.add_edge("analytics_tools", "analytics")
    
    # ===== Compile with Persistence =====
    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


def create_simple_enhanced_graph():
    """
    Create a simplified version for testing
    User → Query Analyzer → Execution Planner → Agents
    """
    graph = StateGraph(EnhancedAgentState)
    
    # Add nodes
    graph.add_node("query_analyzer", query_analyzer_agent)
    graph.add_node("execution_planner", execution_planner_agent)
    graph.add_node("analytics", analytics_agent)
    graph.add_node("search", search_agent)
    graph.add_node("document", document_agent)
    
    # Define flow
    graph.add_edge(START, "query_analyzer")
    graph.add_edge("query_analyzer", "execution_planner")
    
    # Simple routing from planner
    def route_from_planner(state: EnhancedAgentState) -> str:
        # Get first agent from execution plan
        plan = state.get("execution_plan", {})
        sequential = plan.get("sequential_tasks", [])
        if sequential:
            return sequential[0]
        return "analytics"  # Default
    
    graph.add_conditional_edges(
        "execution_planner",
        route_from_planner,
        {
            "analytics": "analytics",
            "search": "search",
            "document": "document"
        }
    )
    
    # All agents go to END
    graph.add_edge("analytics", END)
    graph.add_edge("search", END)
    graph.add_edge("document", END)
    
    return graph.compile()


# Utility functions for graph management
def get_graph_visualization(graph):
    """
    Get graph structure for visualization
    Returns nodes and edges in a format suitable for frontend display
    """
    # This would integrate with LangGraph's visualization capabilities
    nodes = [
        {"id": "start", "label": "Start", "type": "entry"},
        {"id": "query_analyzer", "label": "Query Analyzer", "type": "intelligent"},
        {"id": "execution_planner", "label": "Execution Planner", "type": "intelligent"},
        {"id": "dynamic_router", "label": "Dynamic Router", "type": "intelligent"},
        {"id": "supervisor", "label": "Supervisor", "type": "control"},
        {"id": "analytics", "label": "Analytics Agent", "type": "agent"},
        {"id": "search", "label": "Search Agent", "type": "agent"},
        {"id": "document", "label": "Document Agent", "type": "agent"},
        {"id": "compliance", "label": "Compliance Agent", "type": "agent"},
        {"id": "end", "label": "End", "type": "exit"}
    ]
    
    edges = [
        {"from": "start", "to": "query_analyzer", "type": "fixed"},
        {"from": "query_analyzer", "to": "execution_planner", "type": "fixed"},
        {"from": "execution_planner", "to": "dynamic_router", "type": "fixed"},
        {"from": "dynamic_router", "to": "analytics", "type": "conditional"},
        {"from": "dynamic_router", "to": "search", "type": "conditional"},
        {"from": "dynamic_router", "to": "document", "type": "conditional"},
        {"from": "dynamic_router", "to": "compliance", "type": "conditional"},
        {"from": "analytics", "to": "dynamic_router", "type": "fixed"},
        {"from": "search", "to": "dynamic_router", "type": "fixed"},
        {"from": "document", "to": "dynamic_router", "type": "fixed"},
        {"from": "compliance", "to": "dynamic_router", "type": "fixed"},
        {"from": "dynamic_router", "to": "end", "type": "conditional"}
    ]
    
    return {"nodes": nodes, "edges": edges}


async def execute_enhanced_query(graph, query: str, config: Dict[str, Any] = None):
    """
    Execute a query through the enhanced graph
    
    Args:
        graph: Compiled LangGraph
        query: User query string
        config: Optional configuration including thread_id
    
    Returns:
        Final state after execution
    """
    from langchain_core.messages import HumanMessage
    
    # Prepare initial state
    initial_state = create_initial_state()
    initial_state["messages"] = [HumanMessage(content=query)]
    initial_state["raw_query"] = query
    
    # Default config if not provided
    if config is None:
        config = {"configurable": {"thread_id": "default"}}
    
    # Execute the graph
    try:
        result = await graph.ainvoke(initial_state, config)
        return result
    except Exception as e:
        print(f"Error executing query: {e}")
        return {
            "errors": [str(e)],
            "is_complete": False
        }


from typing import List
def get_execution_trace(state: EnhancedAgentState) -> List[Dict[str, Any]]:
    """
    Extract execution trace from state for debugging
    """
    trace = []
    
    # Add routing history
    for routing in state.get("routing_history", []):
        trace.append({
            "type": "routing",
            "timestamp": routing["timestamp"],
            "from": routing["from_agent"],
            "to": routing["to_agent"],
            "reason": routing["reason"]
        })
    
    # Add progress entries
    for progress in state.get("progress", []):
        trace.append({
            "type": "progress",
            "timestamp": progress["timestamp"],
            "agent": progress["agent"],
            "action": progress["action"],
            "details": progress.get("details", {})
        })
    
    # Sort by timestamp
    trace.sort(key=lambda x: x.get("timestamp", ""))
    
    return trace