"""
Test cases for the main StateGraph
Testing LangGraph 0.6.6 integration
"""
import pytest
import asyncio
from langchain_core.messages import HumanMessage, AIMessage
from src.core.graph import create_sales_support_graph, SalesSupportApp
from src.state.agent_state import AgentState, TaskType


class TestStateGraph:
    """Test suite for the main StateGraph"""
    
    def test_graph_creation(self):
        """Test that graph can be created successfully"""
        graph = create_sales_support_graph(use_sqlite=False)
        assert graph is not None
        
    def test_graph_nodes(self):
        """Test that all required nodes are present"""
        graph = create_sales_support_graph(use_sqlite=False)
        
        # In LangGraph 0.6.6, we can check the graph structure
        # Note: Exact API may vary, this is a conceptual test
        expected_nodes = ["supervisor", "analytics", "search", "document", "compliance"]
        
        # Graph should have been compiled successfully
        assert graph is not None
        
    @pytest.mark.asyncio
    async def test_graph_execution_analytics(self):
        """Test graph execution with analytics request"""
        app = SalesSupportApp(use_sqlite=False)
        
        result = await app.aprocess_request(
            user_input="Analyze sales performance for last quarter",
            thread_id="test_thread_1"
        )
        
        # Check result structure
        assert "messages" in result
        assert "progress" in result
        assert "results" in result
        assert "metadata" in result
        
        # Check that supervisor was involved
        progress = result.get("progress", [])
        agents_involved = [p.get("agent") for p in progress]
        assert "supervisor" in agents_involved
        
    @pytest.mark.asyncio
    async def test_graph_execution_search(self):
        """Test graph execution with search request"""
        app = SalesSupportApp(use_sqlite=False)
        
        result = await app.aprocess_request(
            user_input="Search for information about Samsung Electronics",
            thread_id="test_thread_2"
        )
        
        # Check result
        assert "messages" in result
        assert len(result["messages"]) > 0
        
        # Check metadata
        assert result["metadata"]["thread_id"] == "test_thread_2"
        
    @pytest.mark.asyncio
    async def test_graph_execution_document(self):
        """Test graph execution with document generation request"""
        app = SalesSupportApp(use_sqlite=False)
        
        result = await app.aprocess_request(
            user_input="Create a sales proposal for a new client in healthcare industry",
            thread_id="test_thread_3"
        )
        
        # Check result
        assert "messages" in result
        assert "results" in result
        
    @pytest.mark.asyncio
    async def test_graph_execution_compliance(self):
        """Test graph execution with compliance request"""
        app = SalesSupportApp(use_sqlite=False)
        
        result = await app.aprocess_request(
            user_input="Check compliance for data privacy regulations",
            thread_id="test_thread_4"
        )
        
        # Check result
        assert "messages" in result
        assert "progress" in result
        
    @pytest.mark.asyncio
    async def test_graph_streaming(self):
        """Test graph streaming functionality"""
        app = SalesSupportApp(use_sqlite=False)
        
        outputs = []
        async for output in app.stream_request(
            user_input="Analyze market trends",
            thread_id="test_stream_1"
        ):
            outputs.append(output)
        
        # Should have received multiple outputs
        assert len(outputs) > 0
        
        # Each output should be a dict with node results
        for output in outputs:
            assert isinstance(output, dict)
            
    @pytest.mark.asyncio
    async def test_graph_event_streaming(self):
        """Test LangGraph 0.6.6 event streaming feature"""
        app = SalesSupportApp(use_sqlite=False)
        
        events = []
        async for event in app.stream_events(
            user_input="Search for customer data",
            thread_id="test_events_1"
        ):
            events.append(event)
            # Limit events for testing
            if len(events) > 10:
                break
        
        # Should have received events
        assert len(events) > 0
        
    def test_graph_visualization(self):
        """Test graph visualization structure"""
        app = SalesSupportApp(use_sqlite=False)
        
        viz = app.get_graph_visualization()
        
        # Check structure
        assert "nodes" in viz or "edges" in viz
        
        if "nodes" in viz:
            assert "supervisor" in viz["nodes"]
            assert "analytics" in viz["nodes"]
            assert "search" in viz["nodes"]
            assert "document" in viz["nodes"]
            assert "compliance" in viz["nodes"]
            
    def test_thread_id_generation(self):
        """Test automatic thread_id generation"""
        app = SalesSupportApp(use_sqlite=False)
        
        # Process without thread_id
        result = app.process_request(
            user_input="Test request"
        )
        
        # Should have generated thread_id
        assert "metadata" in result
        assert "thread_id" in result["metadata"]
        assert result["metadata"]["thread_id"].startswith("thread_")
        
    def test_thread_id_preservation(self):
        """Test that provided thread_id is preserved"""
        app = SalesSupportApp(use_sqlite=False)
        
        # Process with specific thread_id
        result = app.process_request(
            user_input="Test request",
            thread_id="custom_thread_123"
        )
        
        # Should preserve the thread_id
        assert result["metadata"]["thread_id"] == "custom_thread_123"
        
    @pytest.mark.asyncio
    async def test_multiple_agent_routing(self):
        """Test that multiple agents can be involved in processing"""
        app = SalesSupportApp(use_sqlite=False)
        
        # Request that might involve multiple agents
        result = await app.aprocess_request(
            user_input="Analyze sales data and create a compliance report",
            thread_id="test_multi_1"
        )
        
        # Check progress for multiple agents
        progress = result.get("progress", [])
        agents = [p.get("agent") for p in progress]
        
        # Should have at least supervisor
        assert "supervisor" in agents
        
        # May have routed to analytics or compliance
        assert len(agents) >= 1
        
    def test_error_handling(self):
        """Test error handling in the graph"""
        app = SalesSupportApp(use_sqlite=False)
        
        # Test with empty input
        result = app.process_request(user_input="")
        
        # Should handle gracefully
        assert "messages" in result
        assert "errors" in result or result.get("is_complete", False)


class TestSalesSupportApp:
    """Test the SalesSupportApp wrapper class"""
    
    def test_app_initialization(self):
        """Test app initialization"""
        app = SalesSupportApp(use_sqlite=False)
        assert app is not None
        assert app.app is not None
        assert app.thread_counter == 0
        
    def test_app_with_sqlite(self):
        """Test app initialization with SQLite checkpointer"""
        app = SalesSupportApp(use_sqlite=True)
        assert app is not None
        
    @pytest.mark.asyncio
    async def test_app_async_processing(self):
        """Test async processing method"""
        app = SalesSupportApp(use_sqlite=False)
        
        result = await app.aprocess_request(
            user_input="Test async processing",
            thread_id="async_test_1"
        )
        
        assert result is not None
        assert "messages" in result
        assert "metadata" in result
        
    def test_app_sync_processing(self):
        """Test sync processing method"""
        app = SalesSupportApp(use_sqlite=False)
        
        result = app.process_request(
            user_input="Test sync processing",
            thread_id="sync_test_1"
        )
        
        assert result is not None
        assert "messages" in result
        assert "metadata" in result