"""
Test script to verify State-based information sharing between agents
"""
import asyncio
import json
import sys
sys.path.append('.')
from backend.src.core.graph import create_sales_support_graph
from loguru import logger

async def test_state_sharing():
    """Test that agents share information through State"""
    
    print("\n" + "="*50)
    print("Testing State-based Information Sharing")
    print("="*50 + "\n")
    
    # Test 1: Multi-agent query that should share data
    test_query = "서울대병원 고객 정보를 검색하고 매출 분석 후 보고서 작성"
    print(f"Test Query: {test_query}")
    print("-" * 50)
    
    thread_id = "test_state_sharing_001"
    
    # Create the graph
    sales_app = create_sales_support_graph(use_sqlite=False)
    
    try:
        # Process the query
        print("\nProcessing query through multi-agent system...")
        from langchain_core.messages import HumanMessage
        
        initial_state = {
            "messages": [HumanMessage(content=test_query)],
            "current_agent": "supervisor",
            "task_type": "analyze",
            "progress": [],
            "context": {},
            "metadata": {},
            "task_description": test_query,
            "results": {},
            "errors": [],
            "is_complete": False
        }
        
        async for output in sales_app.astream(initial_state, {"configurable": {"thread_id": thread_id}}):
            for node_name, node_output in output.items():
                print(f"\n[{node_name}] Agent executing...")
                
                # Check if results are being accumulated in State
                if "results" in node_output:
                    results = node_output["results"]
                    print(f"  State.results keys: {list(results.keys())}")
                    
                    # Check for data from previous agents
                    if "search" in results and "analytics" in results:
                        print("  ✅ Analytics has access to Search results!")
                        search_data = results["search"].get("raw_data", {})
                        if search_data:
                            print(f"    - Companies found by Search: {search_data.get('companies_found', [])[:3]}")
                    
                    if "document" in results:
                        doc_data = results["document"]
                        if doc_data.get("integrated_sources", {}).get("search_data_used"):
                            print("  ✅ Document integrated Search data!")
                        if doc_data.get("integrated_sources", {}).get("analytics_data_used"):
                            print("  ✅ Document integrated Analytics data!")
                        integrated = doc_data.get("integrated_sources", {})
                        if integrated.get("companies_included"):
                            print(f"    - Companies included in document: {integrated['companies_included']}")
                        if integrated.get("recommendations_included"):
                            print(f"    - Recommendations included: {integrated['recommendations_included']}")
                
                # Check context updates
                if "context" in node_output:
                    context = node_output["context"]
                    if context.get("search_completed"):
                        print(f"  Context: Search completed")
                    if context.get("analytics_completed"):
                        print(f"  Context: Analytics completed")
                    if context.get("document_generated"):
                        print(f"  Context: Document generated")
        
        print("\n" + "="*50)
        print("State Sharing Test Complete!")
        print("="*50)
        
    except Exception as e:
        print(f"\nError during test: {str(e)}")
        logger.error(f"Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_state_sharing())