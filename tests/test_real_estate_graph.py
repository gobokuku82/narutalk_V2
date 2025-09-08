"""
Test file for Real Estate AI Agent System
Testing LangGraph 0.6.6 implementation
"""
import os
import sys
import asyncio
from typing import Dict, Any

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test imports for LangGraph 0.6.6
def test_langgraph_imports():
    """Test that all required LangGraph 0.6.6 imports work"""
    try:
        from langgraph.graph import StateGraph, START, END
        from langgraph.graph.message import add_messages, MessagesState
        from langgraph.checkpoint.memory import MemorySaver
        from langgraph.prebuilt import ToolNode, tools_condition
        print("✅ All LangGraph 0.6.6 imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

# Test State Definition
def test_state_definition():
    """Test Real Estate State definition"""
    try:
        from langgraph.graph.message import MessagesState
        from typing import TypedDict, Annotated, List, Dict, Any, Optional
        from enum import Enum
        
        class PropertyType(Enum):
            APARTMENT = "apartment"
            HOUSE = "house"
            VILLA = "villa"
            COMMERCIAL = "commercial"
        
        class RealEstateState(MessagesState):
            """Test state for real estate system"""
            current_agent: str
            property_type: Optional[PropertyType]
            location: Optional[str]
            search_results: List[Dict[str, Any]]
            progress: Annotated[List[Dict], lambda x, y: x + y]
        
        print("✅ Real Estate State defined successfully")
        return True
    except Exception as e:
        print(f"❌ State definition error: {e}")
        return False

# Test Graph Construction
def test_graph_construction():
    """Test basic graph construction with real estate agents"""
    try:
        from langgraph.graph import StateGraph, START, END
        from langgraph.graph.message import MessagesState
        from langgraph.checkpoint.memory import MemorySaver
        from typing import Dict
        
        # Define simple test state
        class TestState(MessagesState):
            current_agent: str
            results: Dict[str, Any]
        
        # Create test agents
        def supervisor_agent(state: TestState) -> dict:
            return {
                "current_agent": "property_search",
                "results": {"supervisor": "planning_complete"}
            }
        
        def property_search_agent(state: TestState) -> dict:
            return {
                "current_agent": "valuation",
                "results": {"search": "10 properties found"}
            }
        
        def valuation_agent(state: TestState) -> dict:
            return {
                "current_agent": "end",
                "results": {"valuation": "analysis complete"}
            }
        
        # Routing function
        def route_agent(state: TestState) -> str:
            agent = state.get("current_agent", "end")
            return agent if agent != "end" else END
        
        # Build graph
        graph = StateGraph(TestState)
        
        # Add nodes
        graph.add_node("supervisor", supervisor_agent)
        graph.add_node("property_search", property_search_agent)
        graph.add_node("valuation", valuation_agent)
        
        # Add edges
        graph.add_edge(START, "supervisor")
        
        # Add conditional routing
        graph.add_conditional_edges(
            "supervisor",
            route_agent,
            {
                "property_search": "property_search",
                "valuation": "valuation",
                END: END
            }
        )
        
        graph.add_edge("property_search", "valuation")
        graph.add_edge("valuation", END)
        
        # Compile with checkpointer
        checkpointer = MemorySaver()
        app = graph.compile(checkpointer=checkpointer)
        
        print("✅ Graph construction successful")
        return app
    except Exception as e:
        print(f"❌ Graph construction error: {e}")
        return None

# Test Tool Definition
def test_tool_definition():
    """Test real estate tool definition"""
    try:
        from langchain_core.tools import tool
        import json
        
        @tool
        def search_properties(location: str, property_type: str = "apartment") -> str:
            """
            Search for properties in a specific location
            
            Args:
                location: The area to search in
                property_type: Type of property
                
            Returns:
                JSON string with search results
            """
            results = {
                "location": location,
                "property_type": property_type,
                "found": 5,
                "properties": [
                    {"id": "1", "price": 500000000, "area": 84},
                    {"id": "2", "price": 600000000, "area": 99}
                ]
            }
            return json.dumps(results, ensure_ascii=False)
        
        @tool
        def calculate_mortgage(price: float, down_payment: float, years: int = 30) -> str:
            """Calculate monthly mortgage payment"""
            loan_amount = price - down_payment
            monthly_rate = 0.035 / 12  # 3.5% annual rate
            months = years * 12
            
            if monthly_rate > 0:
                payment = loan_amount * (monthly_rate * (1 + monthly_rate)**months) / ((1 + monthly_rate)**months - 1)
            else:
                payment = loan_amount / months
            
            return json.dumps({
                "loan_amount": loan_amount,
                "monthly_payment": round(payment),
                "total_payment": round(payment * months)
            })
        
        # Test tool execution
        result1 = search_properties.invoke({"location": "강남구", "property_type": "아파트"})
        result2 = calculate_mortgage.invoke({"price": 1000000000, "down_payment": 400000000, "years": 30})
        
        print("✅ Tool definition and execution successful")
        print(f"   Search result: {result1[:50]}...")
        print(f"   Mortgage calc: {result2}")
        return True
    except Exception as e:
        print(f"❌ Tool definition error: {e}")
        return False

# Test Async Execution
async def test_async_execution():
    """Test async graph execution"""
    try:
        from langgraph.graph import StateGraph, START, END
        from langgraph.graph.message import MessagesState
        from langgraph.checkpoint.memory import MemorySaver
        from langchain_core.messages import HumanMessage, AIMessage
        
        class AsyncState(MessagesState):
            result: str
        
        async def async_agent(state: AsyncState) -> dict:
            await asyncio.sleep(0.1)  # Simulate async operation
            return {
                "messages": [AIMessage(content="Async response")],
                "result": "success"
            }
        
        graph = StateGraph(AsyncState)
        graph.add_node("agent", async_agent)
        graph.add_edge(START, "agent")
        graph.add_edge("agent", END)
        
        app = graph.compile(checkpointer=MemorySaver())
        
        # Test async invocation
        result = await app.ainvoke(
            {"messages": [HumanMessage(content="Test")]},
            config={"configurable": {"thread_id": "test_async"}}
        )
        
        print("✅ Async execution successful")
        print(f"   Result: {result.get('result')}")
        return True
    except Exception as e:
        print(f"❌ Async execution error: {e}")
        return False

# Test Progress Tracking
def test_progress_tracking():
    """Test progress tracking mechanism"""
    try:
        from typing import Annotated, List, Dict
        
        # Test reducer function
        def accumulate_progress(x: List[Dict], y: List[Dict]) -> List[Dict]:
            return x + y
        
        # Simulate progress updates
        progress: Annotated[List[Dict], accumulate_progress] = []
        
        # Add progress entries
        progress_1 = [{"agent": "supervisor", "status": "completed"}]
        progress_2 = [{"agent": "search", "status": "completed"}]
        
        combined = accumulate_progress(progress_1, progress_2)
        
        assert len(combined) == 2
        assert combined[0]["agent"] == "supervisor"
        assert combined[1]["agent"] == "search"
        
        print("✅ Progress tracking successful")
        print(f"   Progress entries: {len(combined)}")
        return True
    except Exception as e:
        print(f"❌ Progress tracking error: {e}")
        return False

# Main test runner
def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("🏢 Real Estate AI Agent System - Test Suite")
    print("Testing LangGraph 0.6.6 Implementation")
    print("="*60 + "\n")
    
    tests = [
        ("LangGraph Imports", test_langgraph_imports),
        ("State Definition", test_state_definition),
        ("Graph Construction", test_graph_construction),
        ("Tool Definition", test_tool_definition),
        ("Progress Tracking", test_progress_tracking)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Testing: {test_name}")
        print("-" * 40)
        result = test_func()
        results.append(result)
        print()
    
    # Async test
    print(f"\n📋 Testing: Async Execution")
    print("-" * 40)
    async_result = asyncio.run(test_async_execution())
    results.append(async_result)
    
    # Summary
    print("\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)
    
    passed = sum(1 for r in results if r)
    total = len(results)
    
    print(f"\n✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed! Ready for real estate app development.")
    else:
        print("\n⚠️ Some tests failed. Please check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    # Check Python version
    import sys
    if sys.version_info < (3, 8):
        print("⚠️ Python 3.8+ required for async features")
        sys.exit(1)
    
    # Run tests
    success = run_all_tests()
    sys.exit(0 if success else 1)