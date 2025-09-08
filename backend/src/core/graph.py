"""
Main StateGraph implementation for LangGraph 0.6.6
Following rules.md strictly - ONLY use StateGraph, START, END
"""
from typing import Dict, Any
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
# SqliteSaver import with fallback for langgraph 0.6.6
try:
    from langgraph.checkpoint.sqlite import SqliteSaver
except ImportError:
    SqliteSaver = None
from langchain_core.messages import HumanMessage, AIMessage
import os
from datetime import datetime

# Import state and agents
from ..state.agent_state import AgentState, TaskType
from ..agents.supervisor import supervisor_agent, route_by_task_type
from ..agents.analytics import analytics_agent
from ..agents.search import search_agent
from ..agents.document import document_agent
from ..agents.compliance import compliance_agent


def create_sales_support_graph(use_sqlite: bool = False):
    """
    Create the main sales support AI graph
    Following rules.md pattern exactly
    """
    # Initialize StateGraph with AgentState
    graph = StateGraph(AgentState)
    
    # Add all agent nodes
    graph.add_node("supervisor", supervisor_agent)
    graph.add_node("analytics", analytics_agent)
    graph.add_node("search", search_agent)
    graph.add_node("document", document_agent)
    graph.add_node("compliance", compliance_agent)
    
    # Add entry point from START to supervisor
    graph.add_edge(START, "supervisor")
    
    # Add conditional routing from supervisor
    graph.add_conditional_edges(
        "supervisor",
        route_by_task_type,
        {
            "analytics": "analytics",
            "search": "search",
            "document": "document",
            "compliance": "compliance",
            "end": END
        }
    )
    
    # Add edges from specialized agents back to supervisor for potential re-routing
    # Or directly to END based on task completion
    graph.add_edge("analytics", "supervisor")
    graph.add_edge("search", "supervisor")
    graph.add_edge("document", "supervisor")
    graph.add_edge("compliance", "supervisor")
    
    # Choose checkpointer based on parameter
    if use_sqlite and SqliteSaver:
        # Production: Use SqliteSaver if available
        db_path = os.path.join(os.path.dirname(__file__), "..", "..", "checkpoints.db")
        checkpointer = SqliteSaver.from_conn_string(f"sqlite:///{db_path}")
    else:
        # Development or fallback: Use MemorySaver
        checkpointer = MemorySaver()
    
    # Compile the graph with checkpointer
    app = graph.compile(checkpointer=checkpointer)
    
    return app


class SalesSupportApp:
    """
    Wrapper class for the sales support application
    Provides high-level interface for the graph
    """
    
    def __init__(self, use_sqlite: bool = False):
        """Initialize the sales support application"""
        self.app = create_sales_support_graph(use_sqlite=use_sqlite)
        self.thread_counter = 0
    
    def process_request(self, user_input: str, thread_id: str = None) -> Dict[str, Any]:
        """
        Process a user request through the graph
        
        Args:
            user_input: The user's request
            thread_id: Optional thread ID for conversation continuity
        
        Returns:
            Dictionary containing the final state
        """
        # Generate thread_id if not provided
        if not thread_id:
            self.thread_counter += 1
            thread_id = f"thread_{self.thread_counter}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Prepare initial state
        initial_state = {
            "messages": [HumanMessage(content=user_input)],
            "current_agent": "supervisor",
            "task_type": "",
            "task_description": user_input,
            "progress": [],
            "context": {},
            "metadata": {
                "thread_id": thread_id,
                "timestamp": datetime.now().isoformat(),
                "user_input": user_input
            },
            "results": {},
            "errors": [],
            "is_complete": False
        }
        
        # Configure execution
        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }
        
        # Execute the graph
        final_state = self.app.invoke(initial_state, config)
        
        return final_state
    
    async def aprocess_request(self, user_input: str, thread_id: str = None) -> Dict[str, Any]:
        """
        Async version of process_request
        """
        # Generate thread_id if not provided
        if not thread_id:
            self.thread_counter += 1
            thread_id = f"thread_{self.thread_counter}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Prepare initial state
        initial_state = {
            "messages": [HumanMessage(content=user_input)],
            "current_agent": "supervisor",
            "task_type": "",
            "task_description": user_input,
            "progress": [],
            "context": {},
            "metadata": {
                "thread_id": thread_id,
                "timestamp": datetime.now().isoformat(),
                "user_input": user_input
            },
            "results": {},
            "errors": [],
            "is_complete": False
        }
        
        # Configure execution
        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }
        
        # Execute the graph asynchronously
        final_state = await self.app.ainvoke(initial_state, config)
        
        return final_state
    
    async def stream_request(self, user_input: str, thread_id: str = None):
        """
        Stream the processing of a request
        
        Yields state updates as they happen
        """
        # Generate thread_id if not provided
        if not thread_id:
            self.thread_counter += 1
            thread_id = f"thread_{self.thread_counter}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Prepare initial state
        initial_state = {
            "messages": [HumanMessage(content=user_input)],
            "current_agent": "supervisor",
            "task_type": "",
            "task_description": user_input,
            "progress": [],
            "context": {},
            "metadata": {
                "thread_id": thread_id,
                "timestamp": datetime.now().isoformat(),
                "user_input": user_input
            },
            "results": {},
            "errors": [],
            "is_complete": False
        }
        
        # Configure execution
        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }
        
        # Stream the graph execution
        async for output in self.app.astream(initial_state, config):
            yield output
    
    async def stream_events(self, user_input: str, thread_id: str = None):
        """
        Stream events from the graph execution (0.6.6 feature)
        
        Provides detailed event stream for monitoring
        """
        # Generate thread_id if not provided
        if not thread_id:
            self.thread_counter += 1
            thread_id = f"thread_{self.thread_counter}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Prepare initial state
        initial_state = {
            "messages": [HumanMessage(content=user_input)],
            "current_agent": "supervisor",
            "task_type": "",
            "task_description": user_input,
            "progress": [],
            "context": {},
            "metadata": {
                "thread_id": thread_id,
                "timestamp": datetime.now().isoformat(),
                "user_input": user_input
            },
            "results": {},
            "errors": [],
            "is_complete": False
        }
        
        # Stream events with version="v2" (0.6.6 pattern)
        async for event in self.app.astream_events(initial_state, version="v2"):
            yield event
    
    def get_graph_visualization(self):
        """
        Get the graph structure for visualization
        """
        try:
            # Try to get the graph structure
            return self.app.get_graph()
        except:
            # Return a simple representation if visualization not available
            return {
                "nodes": [
                    "START",
                    "supervisor",
                    "analytics",
                    "search",
                    "document",
                    "compliance",
                    "END"
                ],
                "edges": [
                    ("START", "supervisor"),
                    ("supervisor", "analytics"),
                    ("supervisor", "search"),
                    ("supervisor", "document"),
                    ("supervisor", "compliance"),
                    ("supervisor", "END"),
                    ("analytics", "supervisor"),
                    ("search", "supervisor"),
                    ("document", "supervisor"),
                    ("compliance", "supervisor")
                ]
            }