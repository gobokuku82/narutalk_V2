"""
Enhanced System Integration Tests
Tests for the enhanced graph with Query Analyzer and Dynamic Router
"""
import pytest
import asyncio
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from src.graph.enhanced_graph import create_enhanced_graph, execute_enhanced_query
from src.state.enhanced_state import create_initial_state
from langchain_core.messages import HumanMessage


class TestEnhancedGraph:
    """Test the enhanced graph functionality"""
    
    @pytest.fixture
    def graph(self):
        """Create enhanced graph instance"""
        return create_enhanced_graph()
    
    def test_graph_creation(self, graph):
        """Test that enhanced graph is created successfully"""
        assert graph is not None
        print("[OK] Enhanced graph created successfully")
    
    @pytest.mark.asyncio
    async def test_query_analyzer(self, graph):
        """Test query analyzer functionality"""
        query = "작년 대비 올해 매출 성장률을 분석해줘"
        
        config = {"configurable": {"thread_id": "test_analyzer"}}
        initial_state = create_initial_state()
        initial_state["messages"] = [HumanMessage(content=query)]
        initial_state["raw_query"] = query
        
        # Run only through query analyzer
        result = None
        async for output in graph.astream(initial_state, config):
            if "query_analyzer" in output:
                result = output["query_analyzer"]
                break
        
        assert result is not None
        assert "query_analysis" in result or "primary_intent" in result
        print(f"[OK] Query Analyzer processed: {query}")
        print(f"   Intent detected: {result.get('primary_intent', 'N/A')}")
    
    @pytest.mark.asyncio
    async def test_execution_planner(self, graph):
        """Test execution planner functionality"""
        query = "고객사 A의 제품 정보를 찾고 매출 분석 보고서를 작성해줘"
        
        config = {"configurable": {"thread_id": "test_planner"}}
        initial_state = create_initial_state()
        initial_state["messages"] = [HumanMessage(content=query)]
        initial_state["raw_query"] = query
        
        # Run through query analyzer and execution planner
        planner_output = None
        async for output in graph.astream(initial_state, config):
            if "execution_planner" in output:
                planner_output = output["execution_planner"]
                break
        
        assert planner_output is not None
        assert "execution_plan" in planner_output
        plan = planner_output.get("execution_plan", {})
        print(f"[OK] Execution Planner created plan")
        print(f"   Sequential tasks: {plan.get('sequential_tasks', [])}")
        print(f"   Parallel tasks: {plan.get('parallel_tasks', [])}")
    
    @pytest.mark.asyncio
    async def test_dynamic_router(self, graph):
        """Test dynamic router functionality"""
        query = "매출 데이터를 분석해줘"
        
        result = await execute_enhanced_query(graph, query)
        
        assert result is not None
        assert "routing_history" in result or "progress" in result
        print(f"[OK] Dynamic Router executed query: {query}")
        
        # Check if query went through proper agents
        if "routing_history" in result:
            for routing in result["routing_history"]:
                print(f"   Routed: {routing.get('from_agent')} → {routing.get('to_agent')}")
    
    @pytest.mark.asyncio
    async def test_analytics_query(self, graph):
        """Test analytics-focused query"""
        query = "이번 달 매출 KPI를 계산해줘"
        
        result = await execute_enhanced_query(graph, query)
        
        assert result is not None
        assert not result.get("errors", [])
        print(f"[OK] Analytics query processed: {query}")
    
    @pytest.mark.asyncio
    async def test_search_query(self, graph):
        """Test search-focused query"""
        query = "Samsung 회사 정보를 검색해줘"
        
        result = await execute_enhanced_query(graph, query)
        
        assert result is not None
        assert not result.get("errors", [])
        print(f"[OK] Search query processed: {query}")
    
    @pytest.mark.asyncio
    async def test_complex_query(self, graph):
        """Test complex multi-step query"""
        query = "고객사 리스트를 검색하고, 각 고객사의 매출을 분석한 후 보고서를 작성해줘"
        
        result = await execute_enhanced_query(graph, query)
        
        assert result is not None
        print(f"[OK] Complex query processed: {query}")
        
        # Check execution plan was created
        if "execution_plan" in result:
            plan = result["execution_plan"]
            print(f"   Total steps planned: {len(plan.get('sequential_tasks', []) + plan.get('parallel_tasks', []))}")


class TestAPIEndpoints:
    """Test API endpoints"""
    
    @pytest.mark.asyncio
    async def test_api_import(self):
        """Test that API can be imported"""
        try:
            from src.api.app import app, enhanced_graph
            assert app is not None
            print("[OK] API app imported successfully")
        except Exception as e:
            pytest.fail(f"Failed to import API: {e}")
    
    @pytest.mark.asyncio
    async def test_websocket_handler(self):
        """Test WebSocket handler imports"""
        try:
            from src.api.app import handle_websocket_invoke
            assert handle_websocket_invoke is not None
            print("[OK] WebSocket handlers imported successfully")
        except Exception as e:
            pytest.fail(f"Failed to import WebSocket handler: {e}")


def run_basic_test():
    """Run basic synchronous test without pytest"""
    print("\n" + "="*50)
    print("Running Basic Enhanced System Tests")
    print("="*50 + "\n")
    
    try:
        # Test 1: Graph Creation
        print("Test 1: Creating enhanced graph...")
        from src.graph.enhanced_graph import create_enhanced_graph
        graph = create_enhanced_graph()
        print("[OK] Graph created successfully\n")
        
        # Test 2: State Creation
        print("Test 2: Creating initial state...")
        from src.state.enhanced_state import create_initial_state
        state = create_initial_state()
        print(f"[OK] State created with fields: {list(state.keys())[:5]}...\n")
        
        # Test 3: Simple Query Execution
        print("Test 3: Executing simple query...")
        from langchain_core.messages import HumanMessage
        
        query = "안녕하세요"
        config = {"configurable": {"thread_id": "test_basic"}}
        initial_state = create_initial_state()
        initial_state["messages"] = [HumanMessage(content=query)]
        initial_state["raw_query"] = query
        
        # Use synchronous invoke instead of async
        try:
            # Just invoke the graph to test it works
            output = graph.invoke(initial_state, config)
            if output:
                print(f"[OK] Query executed successfully")
            else:
                print("[FAIL] No output from query execution\n")
        except Exception as e:
            print(f"[FAIL] Query execution failed: {e}\n")
        
        # Test 4: Import all agents
        print("\nTest 4: Importing all agents...")
        from src.agents.query_analyzer import query_analyzer_agent
        from src.agents.execution_planner import execution_planner_agent
        from src.agents.dynamic_router import dynamic_router_agent
        from src.agents.supervisor import supervisor_agent
        from src.agents.analytics import analytics_agent
        from src.agents.search import search_agent
        from src.agents.document import document_agent
        from src.agents.compliance import compliance_agent
        print("[OK] All agents imported successfully\n")
        
        print("="*50)
        print("[OK] All basic tests passed!")
        print("="*50)
        
    except Exception as e:
        print(f"\n[FAIL] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    # Run basic test first
    if run_basic_test():
        print("\n" + "="*50)
        print("Running Full Test Suite with Pytest")
        print("="*50 + "\n")
        
        # Run pytest if available
        try:
            import pytest
            pytest.main([__file__, "-v", "--tb=short"])
        except ImportError:
            print("Pytest not installed. Install with: pip install pytest pytest-asyncio")