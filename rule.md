# 🏢 Real Estate AI Agent System - Development Rules
**Built with LangGraph 0.6.6 | Last Updated: 2025-09-08**

## 🎯 Project Overview
AI-powered real estate platform using LangGraph 0.6.6 with supervisor pattern, multiple specialized agents, and real-time progress visualization.

## 🏗️ Core Architecture Rules

### 1. LangGraph 0.6.6 Essentials
```python
# ✅ CORRECT IMPORTS (ALWAYS USE THESE)
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages, MessagesState
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import ToolNode, tools_condition
from typing import TypedDict, Annotated, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

# ❌ NEVER USE (Deprecated patterns)
# from langgraph.graph import Graph, Chain, MessageGraph
# graph.set_entry_point()  # OLD
# from langgraph.checkpoint.aiosqlite import AsyncSqliteSaver  # OLD
```

### 2. State Definition for Real Estate
```python
from enum import Enum

class PropertyType(Enum):
    APARTMENT = "apartment"
    HOUSE = "house"
    VILLA = "villa"
    COMMERCIAL = "commercial"
    LAND = "land"

class TaskType(Enum):
    SEARCH = "search"
    VALUATION = "valuation"
    DOCUMENT = "document"
    COMPLIANCE = "compliance"
    MARKET_ANALYSIS = "market"
    RECOMMENDATION = "recommendation"

class RealEstateState(MessagesState):
    """State for Real Estate AI System"""
    # Agent Management
    current_agent: str
    task_type: TaskType
    execution_plan: List[str]
    
    # Property Context
    property_type: Optional[PropertyType]
    location: Optional[str]
    price_range: Optional[Dict[str, float]]
    area_sqm: Optional[float]
    
    # Results Storage
    search_results: List[Dict[str, Any]]
    valuation_data: Dict[str, Any]
    market_analysis: Dict[str, Any]
    documents: List[Dict[str, Any]]
    compliance_checks: List[Dict[str, Any]]
    
    # Progress Tracking
    progress: Annotated[List[Dict], lambda x, y: x + y]  # Accumulate
    completion_percentage: float
    
    # Error Handling
    errors: List[str]
    retry_count: int
```

### 3. Graph Construction Pattern
```python
def create_real_estate_graph():
    """Create the main real estate AI graph"""
    # Initialize StateGraph
    graph = StateGraph(RealEstateState)
    
    # Add Agent Nodes
    graph.add_node("supervisor", supervisor_agent)
    graph.add_node("property_search", property_search_agent)
    graph.add_node("valuation", valuation_agent)
    graph.add_node("document", document_agent)
    graph.add_node("compliance", compliance_agent)
    graph.add_node("market_analysis", market_analysis_agent)
    graph.add_node("recommendation", recommendation_agent)
    
    # Tool Nodes
    graph.add_node("search_tools", search_tool_node)
    graph.add_node("valuation_tools", valuation_tool_node)
    
    # Entry Point
    graph.add_edge(START, "supervisor")
    
    # Conditional Routing from Supervisor
    graph.add_conditional_edges(
        "supervisor",
        route_by_task_type,
        {
            "search": "property_search",
            "valuation": "valuation",
            "document": "document",
            "compliance": "compliance",
            "market": "market_analysis",
            "recommendation": "recommendation",
            "end": END
        }
    )
    
    # Direct Agent-to-Agent Routing (Optimization)
    graph.add_edge("property_search", "valuation")  # Auto valuation after search
    graph.add_edge("document", "compliance")  # Auto compliance check
    graph.add_edge("valuation", "market_analysis")  # Market context
    
    # Tool Integration
    graph.add_conditional_edges(
        "property_search",
        tools_condition,
        {"tools": "search_tools", END: END}
    )
    
    # Compile with Checkpointer
    checkpointer = SqliteSaver.from_conn_string("real_estate.db")
    return graph.compile(checkpointer=checkpointer)
```

## 🤖 Real Estate Agent Specifications

### 1. Supervisor Agent
```python
def supervisor_agent(state: RealEstateState) -> dict:
    """
    Orchestrates real estate workflow
    - Analyzes user intent
    - Creates execution plan
    - Routes to appropriate agents
    - Monitors progress
    """
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    # Analyze request type
    request_analysis = analyze_real_estate_request(state)
    
    # Create execution plan based on request
    if "매물 검색" in request_analysis:
        execution_plan = ["search", "valuation", "market", "recommendation"]
    elif "시세 조회" in request_analysis:
        execution_plan = ["valuation", "market"]
    elif "계약서" in request_analysis:
        execution_plan = ["document", "compliance"]
    else:
        execution_plan = ["search"]
    
    return {
        "execution_plan": execution_plan,
        "current_agent": execution_plan[0],
        "task_type": execution_plan[0],
        "progress": [{"agent": "supervisor", "status": "planning_complete"}]
    }
```

### 2. Property Search Agent
```python
@tool
def search_properties(
    location: str,
    property_type: PropertyType,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    area_min: Optional[float] = None,
    area_max: Optional[float] = None
) -> str:
    """
    Search for properties based on criteria
    
    Returns:
        JSON string with property listings
    """
    # Implementation with real estate API
    results = call_property_api(location, property_type, price_range)
    return json.dumps(results, ensure_ascii=False)

def property_search_agent(state: RealEstateState) -> dict:
    """Search and filter properties"""
    tools = [search_properties, filter_by_amenities, calculate_distance]
    tool_node = ToolNode(tools)
    
    # Execute search based on criteria
    search_criteria = extract_search_criteria(state)
    results = execute_property_search(search_criteria)
    
    return {
        "search_results": results,
        "current_agent": "valuation",  # Next in pipeline
        "progress": [{"agent": "property_search", "found": len(results)}]
    }
```

### 3. Valuation Agent
```python
def valuation_agent(state: RealEstateState) -> dict:
    """
    Analyzes property values
    - Current market price
    - Historical trends
    - Comparative analysis
    - Investment potential
    """
    properties = state.get("search_results", [])
    
    valuation_results = []
    for property in properties:
        valuation = {
            "property_id": property["id"],
            "current_price": property["price"],
            "estimated_value": calculate_market_value(property),
            "price_per_sqm": property["price"] / property["area"],
            "market_trend": analyze_price_trend(property["location"]),
            "investment_score": calculate_investment_score(property)
        }
        valuation_results.append(valuation)
    
    return {
        "valuation_data": {"properties": valuation_results},
        "current_agent": "market_analysis",
        "progress": [{"agent": "valuation", "analyzed": len(valuation_results)}]
    }
```

### 4. Document Agent
```python
def document_agent(state: RealEstateState) -> dict:
    """
    Generates real estate documents
    - Purchase agreements
    - Lease contracts
    - Property reports
    - Investment analysis
    """
    doc_type = state.get("document_type", "report")
    property_data = state.get("selected_property")
    
    document = generate_document(doc_type, property_data)
    
    return {
        "documents": [document],
        "current_agent": "compliance",  # Auto compliance check
        "progress": [{"agent": "document", "generated": doc_type}]
    }
```

### 5. Compliance Agent
```python
def compliance_agent(state: RealEstateState) -> dict:
    """
    Checks legal and regulatory compliance
    - Building codes
    - Zoning laws
    - Tax obligations
    - Contract validity
    """
    checks = []
    
    # Perform various compliance checks
    checks.append(check_building_permits(state))
    checks.append(check_zoning_compliance(state))
    checks.append(verify_ownership(state))
    checks.append(check_tax_status(state))
    
    return {
        "compliance_checks": checks,
        "current_agent": "supervisor",
        "progress": [{"agent": "compliance", "checks_passed": sum(c["passed"] for c in checks)}]
    }
```

## 🛠️ Tool Implementation Rules

### 1. Real Estate Specific Tools
```python
# Property Search Tools
@tool
def search_by_location(location: str, radius_km: float = 5) -> str:
    """Search properties within radius of location"""
    pass

@tool
def filter_by_school_district(district: str) -> str:
    """Filter properties by school district"""
    pass

@tool
def calculate_mortgage(price: float, down_payment: float, years: int) -> str:
    """Calculate monthly mortgage payment"""
    pass

# Valuation Tools
@tool
def get_comparable_sales(property_id: str) -> str:
    """Get recent comparable property sales"""
    pass

@tool
def estimate_rental_income(property_id: str) -> str:
    """Estimate potential rental income"""
    pass

# Market Analysis Tools
@tool
def get_market_trends(location: str, period: str = "1y") -> str:
    """Get market trend data for location"""
    pass

@tool
def analyze_neighborhood(location: str) -> str:
    """Analyze neighborhood amenities and quality"""
    pass
```

### 2. Tool Node Pattern
```python
# Create specialized tool nodes
search_tools = [
    search_by_location,
    filter_by_school_district,
    search_by_amenities
]
search_tool_node = ToolNode(search_tools)

valuation_tools = [
    get_comparable_sales,
    estimate_rental_income,
    calculate_roi
]
valuation_tool_node = ToolNode(valuation_tools)
```

## 📊 Progress Tracking & Visualization

### 1. Progress State Management
```python
def update_progress(state: RealEstateState, agent: str, status: str) -> dict:
    """Update progress with detailed tracking"""
    progress_entry = {
        "agent": agent,
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "percentage": calculate_completion_percentage(state)
    }
    
    return {
        "progress": [progress_entry],
        "completion_percentage": progress_entry["percentage"]
    }
```

### 2. WebSocket Message Format
```python
# Progress update message
{
    "type": "progress_update",
    "data": {
        "current_agent": "property_search",
        "agents_completed": ["supervisor"],
        "agents_pending": ["valuation", "market_analysis"],
        "percentage": 25,
        "message": "검색 중: 강남구 아파트 매물",
        "results_preview": {
            "found": 15,
            "filtered": 8
        }
    }
}

# Agent result message
{
    "type": "agent_result",
    "data": {
        "agent": "valuation",
        "result_type": "valuation_complete",
        "summary": "8개 매물 시세 분석 완료",
        "details": {
            "average_price_per_sqm": 15000000,
            "best_value_property_id": "prop_123"
        }
    }
}
```

## 🎨 Frontend Integration Rules

### 1. Component Structure
```
frontend/src/
├── components/
│   ├── RealEstate/
│   │   ├── PropertyCard.jsx       # Property display card
│   │   ├── PropertyMap.jsx        # Map integration
│   │   ├── ValuationChart.jsx     # Price charts
│   │   ├── DocumentViewer.jsx     # Document preview
│   │   └── ComplianceChecklist.jsx # Compliance status
│   ├── Progress/
│   │   ├── AgentProgress.jsx      # Agent-specific progress
│   │   ├── OverallProgress.jsx    # Overall workflow progress
│   │   └── StepIndicator.jsx      # Visual step indicator
│   └── Chat/
│       ├── ChatInterface.jsx      # Main chat UI
│       └── MessageRenderer.jsx    # Message with visuals
```

### 2. Visual Registry Pattern
```javascript
// Real Estate Visual Components Registry
const realEstateVisuals = {
    property_search: PropertySearchResults,
    valuation: ValuationDisplay,
    market_analysis: MarketChart,
    document: DocumentPreview,
    compliance: ComplianceStatus,
    recommendation: RecommendationCard
};

export const getRealEstateVisual = (agentType) => {
    return realEstateVisuals[agentType] || DefaultDisplay;
};
```

## 🔒 Error Handling & Recovery

### 1. Agent-Level Error Handling
```python
def safe_agent_execution(agent_func):
    """Decorator for safe agent execution"""
    async def wrapper(state: RealEstateState) -> dict:
        try:
            return await agent_func(state)
        except Exception as e:
            logger.error(f"Agent {agent_func.__name__} failed: {e}")
            return {
                "errors": [str(e)],
                "current_agent": "supervisor",  # Return to supervisor
                "retry_count": state.get("retry_count", 0) + 1
            }
    return wrapper
```

### 2. Retry Strategy
```python
MAX_RETRIES = 3
RETRY_DELAY = [1, 2, 5]  # Exponential backoff

async def retry_with_backoff(func, state, max_retries=MAX_RETRIES):
    """Retry with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return await func(state)
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(RETRY_DELAY[attempt])
            else:
                return create_fallback_response(state, str(e))
```

## 🗄️ Database Schema

### 1. Property Data Model
```sql
-- Properties table
CREATE TABLE properties (
    id VARCHAR(50) PRIMARY KEY,
    property_type VARCHAR(20),
    location VARCHAR(200),
    address TEXT,
    price DECIMAL(15, 2),
    area_sqm DECIMAL(10, 2),
    rooms INTEGER,
    bathrooms INTEGER,
    year_built INTEGER,
    features JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Search History
CREATE TABLE search_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id VARCHAR(50),
    search_criteria JSON,
    results_count INTEGER,
    timestamp TIMESTAMP
);

-- Valuations
CREATE TABLE valuations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id VARCHAR(50),
    estimated_value DECIMAL(15, 2),
    valuation_date DATE,
    method VARCHAR(50),
    confidence_score DECIMAL(3, 2)
);
```

## 🧪 Testing Strategy

### 1. Unit Tests
```python
# tests/test_real_estate_agents.py
import pytest
from backend.src.agents import property_search_agent

@pytest.mark.asyncio
async def test_property_search_agent():
    """Test property search agent"""
    state = RealEstateState(
        location="강남구",
        property_type=PropertyType.APARTMENT,
        price_range={"min": 1000000000, "max": 2000000000}
    )
    
    result = await property_search_agent(state)
    
    assert "search_results" in result
    assert len(result["search_results"]) > 0
    assert "progress" in result
```

### 2. Integration Tests
```python
@pytest.mark.asyncio
async def test_full_workflow():
    """Test complete real estate workflow"""
    graph = create_real_estate_graph()
    
    initial_state = {
        "messages": [HumanMessage(content="강남구 10억대 아파트 추천해줘")],
        "location": "강남구",
        "property_type": PropertyType.APARTMENT
    }
    
    result = await graph.ainvoke(
        initial_state,
        config={"configurable": {"thread_id": "test_001"}}
    )
    
    assert result["search_results"] is not None
    assert result["valuation_data"] is not None
    assert result["completion_percentage"] == 100
```

## 📋 Implementation Checklist

### Phase 1: Core Setup ✅
- [ ] Create RealEstateState class
- [ ] Set up StateGraph structure
- [ ] Configure SqliteSaver for persistence
- [ ] Initialize supervisor agent

### Phase 2: Agent Development 🚧
- [ ] Property Search Agent
- [ ] Valuation Agent
- [ ] Document Agent
- [ ] Compliance Agent
- [ ] Market Analysis Agent
- [ ] Recommendation Agent

### Phase 3: Tool Integration 🔧
- [ ] Property search tools
- [ ] Valuation calculation tools
- [ ] Market data tools
- [ ] Document generation tools

### Phase 4: Frontend Components 🎨
- [ ] PropertyCard component
- [ ] PropertyMap integration
- [ ] ValuationChart component
- [ ] Progress indicators
- [ ] WebSocket integration

### Phase 5: Testing & Optimization 🧪
- [ ] Unit tests for each agent
- [ ] Integration test suite
- [ ] Performance profiling
- [ ] Error recovery testing

## 🚀 Quick Start Commands

```bash
# Backend setup
cd backend
pip install langgraph==0.6.6 langchain-openai
python -m pytest tests/

# Frontend setup
cd frontend
npm install
npm start

# Run full system
python backend/main.py  # Start backend
npm start              # Start frontend (separate terminal)
```

## ⚡ Performance Guidelines

1. **Parallel Execution**: Use asyncio for concurrent agent operations
2. **Caching**: Cache property data and valuations for 24 hours
3. **Batch Processing**: Process multiple properties in batches
4. **Connection Pooling**: Use database connection pools
5. **Message Queuing**: Implement message queue for WebSocket

## 🔐 Security Requirements

1. **API Keys**: Store in environment variables
2. **Data Validation**: Validate all user inputs
3. **Rate Limiting**: Implement per-user rate limits
4. **Session Management**: Secure session tokens
5. **Data Encryption**: Encrypt sensitive property data

## 📝 Documentation Requirements

1. **API Documentation**: OpenAPI/Swagger spec
2. **Agent Specifications**: Detailed agent behavior docs
3. **Tool Documentation**: Tool usage examples
4. **Deployment Guide**: Production deployment steps
5. **User Guide**: End-user documentation

---

**Version**: 1.0.0  
**LangGraph Version**: 0.6.6  
**Last Updated**: 2025-09-08  
**Author**: Real Estate AI Development Team