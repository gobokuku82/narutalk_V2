"""
Test cases for Supervisor Agent
Testing routing logic and progress tracking
"""
import pytest
import asyncio
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage
from src.state.agent_state import AgentState, TaskType
from src.agents.supervisor import supervisor_agent, route_by_task_type


class TestSupervisorAgent:
    """Test suite for supervisor agent"""
    
    def test_supervisor_routing_analytics(self):
        """Test routing to analytics agent"""
        # Create initial state with analytics request
        state = {
            "messages": [HumanMessage(content="Analyze sales data for Q1 2024")],
            "current_agent": "supervisor",
            "task_type": "",
            "progress": [],
            "context": {},
            "metadata": {},
            "results": {},
            "errors": [],
            "is_complete": False
        }
        
        # Process through supervisor
        result = supervisor_agent(state)
        
        # Assertions
        assert result is not None
        assert "task_type" in result
        assert result["task_type"] in ["analyze", "analytics"]
        assert "current_agent" in result
        assert "progress" in result
        assert len(result["progress"]) > 0
        assert result["progress"][0]["agent"] == "supervisor"
        
    def test_supervisor_routing_search(self):
        """Test routing to search agent"""
        # Create initial state with search request
        state = {
            "messages": [HumanMessage(content="Search for customer information about Samsung")],
            "current_agent": "supervisor",
            "task_type": "",
            "progress": [],
            "context": {},
            "metadata": {},
            "results": {},
            "errors": [],
            "is_complete": False
        }
        
        # Process through supervisor
        result = supervisor_agent(state)
        
        # Assertions
        assert result is not None
        assert result["task_type"] == "search"
        assert "task_description" in result
        assert "Samsung" in result["task_description"]
        
    def test_supervisor_routing_document(self):
        """Test routing to document agent"""
        # Create initial state with document request
        state = {
            "messages": [HumanMessage(content="Create a sales proposal for new client")],
            "current_agent": "supervisor",
            "task_type": "",
            "progress": [],
            "context": {},
            "metadata": {},
            "results": {},
            "errors": [],
            "is_complete": False
        }
        
        # Process through supervisor
        result = supervisor_agent(state)
        
        # Assertions
        assert result is not None
        assert result["task_type"] in ["document", "analyze"]  # Could route either way
        assert "messages" in result
        assert len(result["messages"]) > 0
        
    def test_supervisor_routing_compliance(self):
        """Test routing to compliance agent"""
        # Create initial state with compliance request
        state = {
            "messages": [HumanMessage(content="Check compliance for data privacy regulations")],
            "current_agent": "supervisor",
            "task_type": "",
            "progress": [],
            "context": {},
            "metadata": {},
            "results": {},
            "errors": [],
            "is_complete": False
        }
        
        # Process through supervisor
        result = supervisor_agent(state)
        
        # Assertions
        assert result is not None
        assert result["task_type"] in ["compliance", "validate", "analyze"]
        assert "progress" in result
        assert result["progress"][0]["action"] == "routing_decision"
        
    def test_supervisor_empty_message(self):
        """Test supervisor with no messages"""
        # Create state with no messages
        state = {
            "messages": [],
            "current_agent": "supervisor",
            "task_type": "",
            "progress": [],
            "context": {},
            "metadata": {},
            "results": {},
            "errors": [],
            "is_complete": False
        }
        
        # Process through supervisor
        result = supervisor_agent(state)
        
        # Assertions
        assert result is not None
        assert result["task_type"] == "end"
        assert result["is_complete"] == True
        
    def test_route_by_task_type_function(self):
        """Test the routing function"""
        # Test analyze routing
        state = {"task_type": "analyze"}
        assert route_by_task_type(state) == "analytics"
        
        # Test search routing
        state = {"task_type": "search"}
        assert route_by_task_type(state) == "search"
        
        # Test document routing
        state = {"task_type": "document"}
        assert route_by_task_type(state) == "document"
        
        # Test compliance routing
        state = {"task_type": "compliance"}
        assert route_by_task_type(state) == "compliance"
        
        # Test validate routing (maps to compliance)
        state = {"task_type": "validate"}
        assert route_by_task_type(state) == "compliance"
        
        # Test end routing
        state = {"task_type": "end"}
        assert route_by_task_type(state) == "end"
        
        # Test unknown routing (defaults to end)
        state = {"task_type": "unknown"}
        assert route_by_task_type(state) == "end"
        
    def test_supervisor_progress_tracking(self):
        """Test progress tracking functionality"""
        # Create initial state
        state = {
            "messages": [HumanMessage(content="Analyze customer data and create report")],
            "current_agent": "supervisor",
            "task_type": "",
            "progress": [
                {"agent": "previous", "timestamp": "2024-01-01T00:00:00", "action": "test"}
            ],
            "context": {"test_key": "test_value"},
            "metadata": {},
            "results": {},
            "errors": [],
            "is_complete": False
        }
        
        # Process through supervisor
        result = supervisor_agent(state)
        
        # Assertions
        assert "progress" in result
        assert len(result["progress"]) > 0
        
        # Check new progress entry
        new_progress = result["progress"][-1]
        assert new_progress["agent"] == "supervisor"
        assert "timestamp" in new_progress
        assert "action" in new_progress
        assert new_progress["action"] == "routing_decision"
        assert "decision" in new_progress
        
        # Check context preservation
        assert "context" in result
        assert result["context"] == state["context"]
        
    def test_supervisor_context_preservation(self):
        """Test that supervisor preserves context"""
        # Create state with existing context
        state = {
            "messages": [HumanMessage(content="Search for information")],
            "current_agent": "supervisor",
            "task_type": "",
            "progress": [],
            "context": {
                "client_name": "Test Corp",
                "priority": "high",
                "session_id": "12345"
            },
            "metadata": {"thread_id": "test_thread"},
            "results": {"previous_analysis": {"data": "test"}},
            "errors": [],
            "is_complete": False
        }
        
        # Process through supervisor
        result = supervisor_agent(state)
        
        # Assertions - context should be preserved
        assert "context" in result
        assert result["context"]["client_name"] == "Test Corp"
        assert result["context"]["priority"] == "high"
        assert result["context"]["session_id"] == "12345"


@pytest.mark.asyncio
class TestSupervisorIntegration:
    """Integration tests for supervisor with other components"""
    
    async def test_supervisor_with_multiple_messages(self):
        """Test supervisor with conversation history"""
        state = {
            "messages": [
                HumanMessage(content="I need help with sales"),
                AIMessage(content="I can help you with sales. What specific aspect?"),
                HumanMessage(content="Analyze our Q1 performance")
            ],
            "current_agent": "supervisor",
            "task_type": "",
            "progress": [],
            "context": {},
            "metadata": {},
            "results": {},
            "errors": [],
            "is_complete": False
        }
        
        # Process through supervisor
        result = supervisor_agent(state)
        
        # Should route based on last human message
        assert result["task_type"] in ["analyze", "analytics"]
        assert "Q1 performance" in result["task_description"]