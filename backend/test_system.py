"""
Simple test script for Sales Support AI Backend
Tests each agent independently
"""
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from src.state.agent_state import AgentState
from src.agents.supervisor import supervisor_agent
from src.agents.analytics import analytics_agent
from src.agents.search import search_agent
from src.agents.document import document_agent
from src.agents.compliance import compliance_agent

# Load environment variables from .env file
load_dotenv()


def test_supervisor():
    """Test Supervisor Agent routing"""
    print("\n=== Testing Supervisor Agent ===")
    state = {
        "messages": [HumanMessage(content="분석 작업을 수행해줘")],
        "current_agent": "supervisor",
        "task_type": None,
        "task_description": "",
        "progress": [],
        "context": {},
        "metadata": {},
        "results": {},
        "errors": [],
        "is_complete": False
    }
    
    result = supervisor_agent(state)
    print(f"Task Type: {result.get('task_type')}")
    print(f"Current Agent: {result.get('current_agent')}")
    print(f"Task Description: {result.get('task_description')[:50]}...")
    return result


def test_analytics():
    """Test Analytics Agent"""
    print("\n=== Testing Analytics Agent ===")
    state = {
        "messages": [HumanMessage(content="이번 분기 성과 분석해줘")],
        "current_agent": "analytics",
        "task_type": "analyze",
        "task_description": "이번 분기 성과 분석해줘",
        "progress": [],
        "context": {},
        "metadata": {},
        "results": {},
        "errors": [],
        "is_complete": False
    }
    
    result = analytics_agent(state)
    print(f"Status: {result['progress'][0].get('status', 'unknown')}")
    try:
        print(f"Message Preview: {result['messages'][0].content[:100]}...")
    except UnicodeEncodeError:
        print("Message Preview: [Contains unicode characters]")
    return result


def test_search():
    """Test Search Agent"""
    print("\n=== Testing Search Agent ===")
    state = {
        "messages": [HumanMessage(content="Samsung 고객 정보 검색")],
        "current_agent": "search",
        "task_type": "search",
        "task_description": "Samsung 고객 정보 검색",
        "progress": [],
        "context": {},
        "metadata": {},
        "results": {},
        "errors": [],
        "is_complete": False
    }
    
    result = search_agent(state)
    print(f"Status: {result['progress'][0].get('status', 'unknown')}")
    print(f"Search completed: {result['context'].get('search_completed', False)}")
    return result


def test_document():
    """Test Document Agent"""
    print("\n=== Testing Document Agent ===")
    state = {
        "messages": [HumanMessage(content="방문 보고서 작성해줘")],
        "current_agent": "document",
        "task_type": "document",
        "task_description": "방문 보고서 작성해줘",
        "progress": [],
        "context": {
            "client_name": "Test Corp",
            "visit_date": datetime.now().strftime("%Y-%m-%d")
        },
        "metadata": {},
        "results": {},
        "errors": [],
        "is_complete": False
    }
    
    result = document_agent(state)
    print(f"Status: {result['progress'][0].get('status', 'unknown')}")
    print(f"Document Type: {result['results']['document'].get('type', 'unknown')}")
    print(f"Document ID: {result['results']['document'].get('document_id', 'N/A')}")
    return result


def test_compliance():
    """Test Compliance Agent"""
    print("\n=== Testing Compliance Agent ===")
    state = {
        "messages": [HumanMessage(content="규정 검토해줘")],
        "current_agent": "compliance",
        "task_type": "compliance",
        "task_description": "의사에게 리베이트 10% 제공하는 제안서 검토",
        "progress": [],
        "context": {
            "document_type": "proposal",
            "document_id": "TEST-001"
        },
        "metadata": {},
        "results": {
            "document": {
                "data": {
                    "content": "의사에게 리베이트 10% 제공 및 골프 접대"
                }
            }
        },
        "errors": [],
        "is_complete": False
    }
    
    result = compliance_agent(state)
    print(f"Status: {result['progress'][0].get('status', 'unknown')}")
    print(f"Compliance Status: {result['results']['compliance'].get('compliance_status', 'unknown')}")
    print(f"Violations Found: {result['progress'][0].get('violations_found', 0)}")
    return result


def main():
    """Run all tests"""
    print("=" * 50)
    print("Sales Support AI Backend Test")
    print("=" * 50)
    
    try:
        # Test each agent
        test_supervisor()
        test_analytics()
        test_search()
        test_document()
        test_compliance()
        
        print("\n" + "=" * 50)
        print("All tests completed successfully!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\nTest failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()