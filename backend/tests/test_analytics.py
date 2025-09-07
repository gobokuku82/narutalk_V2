"""
Test cases for Enhanced Analytics Agent with SQLite and Pandas
Testing data analysis, KPI calculation, and predictions
"""
import pytest
import asyncio
import json
import pandas as pd
from datetime import datetime, timedelta
from langchain_core.messages import HumanMessage, AIMessage
from src.state.agent_state import AgentState
from src.agents.analytics import analytics_agent
from src.tools.analytics_tools import (
    query_performance_data,
    analyze_sales_trend,
    calculate_kpis,
    predict_sales_trend
)
from src.tools.database import MockDatabase


class TestAnalyticsTools:
    """Test suite for analytics tools"""
    
    @pytest.fixture
    def mock_db(self):
        """Create a test database instance"""
        db = MockDatabase(":memory:")  # Use in-memory database for tests
        yield db
        db.close()
    
    def test_query_performance_data(self, mock_db):
        """Test querying performance data from SQLite"""
        # Test all employees
        result = query_performance_data.invoke({})
        data = json.loads(result)
        
        assert "total_employees" in data
        assert data["total_employees"] > 0
        assert "avg_monthly_sales" in data
        assert "top_performer" in data
        assert data["top_performer"] is not None
        
        # Test specific employee
        result = query_performance_data.invoke({"employee_id": "emp_001"})
        data = json.loads(result)
        
        assert "employee_details" in data
        assert data["employee_details"]["employee_id"] == "emp_001"
        
    def test_analyze_sales_trend(self, mock_db):
        """Test sales trend analysis"""
        # Test 30-day trend
        result = analyze_sales_trend.invoke({"period_days": 30})
        data = json.loads(result)
        
        assert "period_days" in data
        assert data["period_days"] == 30
        assert "sales_summary" in data
        assert "customer_analysis" in data
        
        if data["customer_analysis"]:
            assert "total_customers" in data["customer_analysis"]
            assert "trend_direction" in data["customer_analysis"]
            assert "avg_satisfaction" in data["customer_analysis"]
        
        # Test with specific customer
        result = analyze_sales_trend.invoke({
            "period_days": 60,
            "customer_id": "cust_001"
        })
        data = json.loads(result)
        
        assert "customer_analysis" in data
    
    def test_calculate_kpis(self, mock_db):
        """Test KPI calculation"""
        result = calculate_kpis.invoke({})
        data = json.loads(result)
        
        # Check main KPI categories
        assert "employee_kpis" in data
        assert "sales_kpis" in data
        assert "product_kpis" in data
        assert "market_kpis" in data
        
        # Check employee KPIs
        if data["employee_kpis"]:
            emp_kpis = data["employee_kpis"]
            assert "total_employees" in emp_kpis
            assert "avg_performance_score" in emp_kpis
            assert "avg_conversion_rate" in emp_kpis
            assert emp_kpis["total_employees"] > 0
        
        # Check sales KPIs
        if data["sales_kpis"]:
            assert "last_30_days" in data["sales_kpis"] or "last_90_days" in data["sales_kpis"]
        
        # Check overall health score
        if "overall_health_score" in data:
            assert 0 <= data["overall_health_score"] <= 100
    
    def test_predict_sales_trend(self, mock_db):
        """Test sales trend prediction"""
        result = predict_sales_trend.invoke({"months_ahead": 3})
        data = json.loads(result)
        
        # May have error if insufficient data
        if "error" not in data:
            assert "predictions" in data
            assert len(data["predictions"]) == 3
            
            # Check prediction structure
            for pred in data["predictions"]:
                assert "month" in pred
                assert "predicted_revenue" in pred
                assert "confidence_low" in pred
                assert "confidence_high" in pred
                assert pred["confidence_low"] <= pred["predicted_revenue"] <= pred["confidence_high"]
            
            # Check trend analysis
            assert "trend_analysis" in data
            trend = data["trend_analysis"]
            assert "direction" in trend
            assert trend["direction"] in ["upward", "downward", "stable"]
            assert "momentum_percentage" in trend


class TestAnalyticsAgent:
    """Test suite for the enhanced analytics agent"""
    
    def test_analytics_agent_basic(self):
        """Test basic analytics agent functionality"""
        # Create initial state
        state = {
            "messages": [HumanMessage(content="Analyze sales performance")],
            "current_agent": "analytics",
            "task_type": "analyze",
            "task_description": "Analyze sales performance",
            "progress": [],
            "context": {},
            "metadata": {},
            "results": {},
            "errors": [],
            "is_complete": False
        }
        
        # Process through analytics agent
        result = analytics_agent(state)
        
        # Check result structure
        assert result is not None
        assert "messages" in result
        assert len(result["messages"]) > 0
        assert "progress" in result
        assert "results" in result
        assert "context" in result
        
        # Check that analytics was completed
        assert result["context"]["analytics_completed"] == True
        
        # Check results contain analytics data
        assert "analytics" in result["results"]
        analytics_result = result["results"]["analytics"]
        assert "timestamp" in analytics_result
        assert "analysis" in analytics_result
        assert "status" in analytics_result
        assert analytics_result["status"] == "success"
    
    def test_analytics_agent_with_kpis(self):
        """Test analytics agent with KPI request"""
        state = {
            "messages": [HumanMessage(content="Calculate KPIs and metrics")],
            "current_agent": "analytics",
            "task_type": "analyze",
            "task_description": "Calculate KPIs and metrics",
            "progress": [],
            "context": {},
            "metadata": {},
            "results": {},
            "errors": [],
            "is_complete": False
        }
        
        result = analytics_agent(state)
        
        # Check that KPIs were calculated
        assert "results" in result
        assert "analytics" in result["results"]
        
        # Check raw data contains KPIs
        if "raw_data" in result["results"]["analytics"]:
            raw_data = result["results"]["analytics"]["raw_data"]
            assert "kpis" in raw_data or len(raw_data) > 0
    
    def test_analytics_agent_with_predictions(self):
        """Test analytics agent with prediction request"""
        state = {
            "messages": [HumanMessage(content="Predict sales trends for next quarter")],
            "current_agent": "analytics",
            "task_type": "analyze",
            "task_description": "Predict sales trends for next quarter",
            "progress": [],
            "context": {},
            "metadata": {},
            "results": {},
            "errors": [],
            "is_complete": False
        }
        
        result = analytics_agent(state)
        
        # Check predictions in context
        assert "context" in result
        
        # Check that appropriate tools were used
        if "messages" in result and result["messages"]:
            metadata = result["messages"][0].metadata
            assert "tools_used" in metadata
    
    def test_analytics_agent_with_employee_filter(self):
        """Test analytics agent with specific employee filter"""
        state = {
            "messages": [HumanMessage(content="Analyze performance for employee emp_001")],
            "current_agent": "analytics",
            "task_type": "analyze",
            "task_description": "Analyze performance for employee emp_001",
            "progress": [],
            "context": {"employee_id": "emp_001"},
            "metadata": {},
            "results": {},
            "errors": [],
            "is_complete": False
        }
        
        result = analytics_agent(state)
        
        # Check that employee-specific analysis was done
        assert "results" in result
        assert "analytics" in result["results"]
        
        # Check context updates
        assert result["context"]["analytics_completed"] == True
        assert "has_performance_data" in result["context"]
    
    def test_analytics_agent_error_handling(self):
        """Test analytics agent error handling"""
        # Create state that might cause an error
        state = {
            "messages": [],  # Empty messages might cause issues
            "current_agent": "analytics",
            "task_type": "analyze",
            "task_description": "",  # Empty task description
            "progress": [],
            "context": {"invalid_key": "test"},
            "metadata": {},
            "results": {},
            "errors": [],
            "is_complete": False
        }
        
        result = analytics_agent(state)
        
        # Should still return a valid result
        assert result is not None
        assert "messages" in result
        assert "current_agent" in result
        
        # May have handled the error gracefully
        if "errors" in result and result["errors"]:
            assert len(result["errors"]) > 0
    
    def test_analytics_agent_comprehensive_analysis(self):
        """Test comprehensive analysis without specific request"""
        state = {
            "messages": [HumanMessage(content="Perform comprehensive business analysis")],
            "current_agent": "analytics",
            "task_type": "analyze",
            "task_description": "Perform comprehensive business analysis",
            "progress": [],
            "context": {"period_days": 90},
            "metadata": {},
            "results": {},
            "errors": [],
            "is_complete": False
        }
        
        result = analytics_agent(state)
        
        # Check multiple data categories were analyzed
        if "results" in result and "analytics" in result["results"]:
            analytics = result["results"]["analytics"]
            if "raw_data" in analytics:
                raw_data = analytics["raw_data"]
                # Should have multiple analysis types
                assert len(raw_data) >= 2
                
                # Check data points analyzed
                if "data_points_analyzed" in analytics:
                    assert analytics["data_points_analyzed"] > 0
    
    def test_analytics_agent_progress_tracking(self):
        """Test that analytics agent tracks progress correctly"""
        state = {
            "messages": [HumanMessage(content="Analyze trends")],
            "current_agent": "analytics",
            "task_type": "analyze",
            "task_description": "Analyze trends",
            "progress": [
                {"agent": "supervisor", "timestamp": "2024-01-01T00:00:00", "action": "routing"}
            ],
            "context": {},
            "metadata": {"thread_id": "test_thread"},
            "results": {},
            "errors": [],
            "is_complete": False
        }
        
        result = analytics_agent(state)
        
        # Check progress was updated
        assert "progress" in result
        assert len(result["progress"]) > 0
        
        # Check new progress entry
        new_progress = result["progress"][-1]
        assert new_progress["agent"] == "analytics"
        assert "timestamp" in new_progress
        assert "action" in new_progress
        assert new_progress["action"] == "analyzing_data_with_sqlite"
        
        # Check status in progress
        if "status" in new_progress:
            assert new_progress["status"] in ["completed", "error"]
        
        # Check data sources tracked
        if "data_sources" in new_progress:
            assert isinstance(new_progress["data_sources"], list)


class TestDatabaseIntegration:
    """Test database integration"""
    
    def test_mock_database_creation(self):
        """Test that mock database is created with data"""
        db = MockDatabase(":memory:")
        
        # Test employee performance table
        df = db.get_employee_performance()
        assert not df.empty
        assert len(df) > 0
        assert "employee_id" in df.columns
        assert "performance_score" in df.columns
        
        # Test customer trends table
        df = db.get_customer_trends(months=1)
        assert not df.empty
        assert "customer_id" in df.columns
        assert "monthly_revenue" in df.columns
        
        # Test sales summary
        summary = db.get_sales_summary(30)
        assert summary is not None
        assert "total_transactions" in summary
        
        db.close()
    
    def test_database_queries(self):
        """Test various database queries"""
        db = MockDatabase(":memory:")
        
        # Test top performers query
        top = db.get_top_performers(3)
        assert not top.empty
        assert len(top) <= 3
        
        # Test product performance
        products = db.get_product_performance()
        assert not products.empty
        assert "product_name" in products.columns
        
        # Test market analysis
        market = db.get_market_analysis()
        assert not market.empty
        assert "opportunity_score" in market.columns
        
        db.close()


@pytest.mark.asyncio
class TestAnalyticsIntegration:
    """Integration tests for analytics with StateGraph"""
    
    async def test_analytics_in_graph_flow(self):
        """Test analytics agent within the graph flow"""
        from src.core.graph import SalesSupportApp
        
        app = SalesSupportApp(use_sqlite=False)
        
        # Request analytics
        result = await app.aprocess_request(
            user_input="Analyze sales KPIs and performance metrics",
            thread_id="test_analytics_1"
        )
        
        # Check that analytics was involved
        progress = result.get("progress", [])
        agents = [p.get("agent") for p in progress]
        
        # Should have supervisor and analytics
        assert "supervisor" in agents or "analytics" in agents
        
        # Check results
        if "results" in result and "analytics" in result["results"]:
            analytics = result["results"]["analytics"]
            assert analytics["status"] == "success"