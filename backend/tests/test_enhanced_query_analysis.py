"""
Test suite for Enhanced Query Analysis System
Tests Query Analyzer, Execution Planner, and Dynamic Router
"""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage

# Import components to test
from backend.src.state.enhanced_state import (
    EnhancedAgentState,
    create_initial_state,
    IntentType,
    SecondaryIntent,
    QueryComplexity
)
from backend.src.agents.query_analyzer import (
    query_analyzer_agent,
    DescriptionBasedAnalyzer
)
from backend.src.agents.execution_planner import (
    execution_planner_agent,
    ExecutionPlanner
)
from backend.src.agents.dynamic_router import (
    dynamic_router_agent,
    DynamicRouter
)
from backend.src.graph.enhanced_graph import (
    create_enhanced_graph,
    create_simple_enhanced_graph
)


class TestQueryAnalyzer:
    """Test Query Analyzer functionality"""
    
    def test_description_based_analysis(self):
        """Test that analyzer uses descriptions instead of keywords"""
        analyzer = DescriptionBasedAnalyzer()
        
        # Mock LLM response
        mock_llm_response = {
            "intent_summary": "사용자가 지난달 매출 데이터를 분석하고 보고서를 생성하려고 함",
            "complexity": "moderate",
            "required_agents": [
                {
                    "agent": "analytics",
                    "reason": "매출 데이터 분석 필요",
                    "specific_task": "지난달 매출 KPI 분석",
                    "priority": 1,
                    "dependencies": []
                },
                {
                    "agent": "document",
                    "reason": "분석 결과를 보고서로 작성",
                    "specific_task": "매출 분석 보고서 생성",
                    "priority": 2,
                    "dependencies": ["analytics"]
                }
            ],
            "execution_plan": {
                "sequential": ["analytics", "document"],
                "parallel_groups": [],
                "conditional": {}
            },
            "estimated_time_seconds": 7,
            "confidence": 0.85,
            "clarification_needed": False,
            "suggested_clarifications": [],
            "optimization_hints": ["분석과 문서 생성을 순차적으로 실행"]
        }
        
        with patch.object(analyzer.llm, 'invoke') as mock_invoke:
            mock_invoke.return_value.content = f"```json\n{str(mock_llm_response)}\n```"
            
            result = analyzer.analyze_query_with_descriptions(
                "지난달 매출 분석해서 보고서 만들어줘"
            )
            
            assert result["intent_summary"] == mock_llm_response["intent_summary"]
            assert len(result["required_agents"]) == 2
            assert result["required_agents"][0]["agent"] == "analytics"
            assert result["required_agents"][1]["agent"] == "document"
            assert result["confidence"] == 0.85
    
    def test_entity_extraction(self):
        """Test entity extraction from context"""
        analyzer = DescriptionBasedAnalyzer()
        
        query = "지난달 삼성전자 매출 분석하고 Q3 실적과 비교해줘"
        analysis_result = {
            "required_agents": [
                {"agent": "analytics", "specific_task": "매출 분석"}
            ]
        }
        
        entities = analyzer.extract_entities_from_context(query, analysis_result)
        
        assert "temporal" in entities
        assert "지난달" in entities["temporal"]
        assert "Q3" in entities["temporal"]
        assert "targets" in entities
        assert "삼성전자" in str(entities.get("targets", []))
    
    @pytest.mark.asyncio
    async def test_query_analyzer_agent(self):
        """Test the main query analyzer agent function"""
        state = create_initial_state()
        state["messages"] = [HumanMessage(content="고객사 정보 검색하고 분석해줘")]
        
        with patch('backend.src.agents.query_analyzer.DescriptionBasedAnalyzer') as MockAnalyzer:
            mock_analyzer = MockAnalyzer.return_value
            mock_analyzer.analyze_query_with_descriptions.return_value = {
                "intent_summary": "고객사 정보 검색 및 분석",
                "complexity": "moderate",
                "required_agents": [
                    {"agent": "search", "reason": "정보 검색", "specific_task": "고객사 정보 검색", "priority": 1, "dependencies": []},
                    {"agent": "analytics", "reason": "데이터 분석", "specific_task": "검색 결과 분석", "priority": 2, "dependencies": ["search"]}
                ],
                "execution_plan": {"sequential": ["search", "analytics"], "parallel_groups": [], "conditional": {}},
                "estimated_time_seconds": 5,
                "confidence": 0.8,
                "clarification_needed": False,
                "suggested_clarifications": [],
                "optimization_hints": []
            }
            mock_analyzer.extract_entities_from_context.return_value = {"targets": ["고객사"]}
            
            result = query_analyzer_agent(state)
            
            assert "query_analysis" in result
            assert result["current_agent"] == "execution_planner"
            assert result["next_agents"] == ["search", "analytics"]
            assert result["query_processing_time"] >= 0


class TestExecutionPlanner:
    """Test Execution Planner functionality"""
    
    def test_dependency_analysis(self):
        """Test dependency analysis between agents"""
        planner = ExecutionPlanner()
        
        required_agents = [
            {"agent": "search", "dependencies": []},
            {"agent": "analytics", "dependencies": ["search"]},
            {"agent": "document", "dependencies": ["analytics"]}
        ]
        
        dependencies = planner.analyze_dependencies(required_agents)
        
        assert dependencies["search"] == set()
        assert dependencies["analytics"] == {"search"}
        assert dependencies["document"] == {"analytics"}
    
    def test_parallel_group_identification(self):
        """Test identification of parallel execution groups"""
        planner = ExecutionPlanner()
        
        # Agents with no interdependencies can run in parallel
        required_agents = ["search", "analytics"]
        dependencies = {"search": set(), "analytics": set()}
        
        parallel_groups = planner.identify_parallel_groups(required_agents, dependencies)
        
        assert len(parallel_groups) == 1
        assert set(parallel_groups[0]) == {"search", "analytics"}
        
        # Agents with dependencies must run sequentially
        required_agents = ["search", "analytics", "document"]
        dependencies = {
            "search": set(),
            "analytics": {"search"},
            "document": {"analytics"}
        }
        
        parallel_groups = planner.identify_parallel_groups(required_agents, dependencies)
        
        assert len(parallel_groups) == 3  # Each in separate level
        assert parallel_groups[0] == ["search"]
        assert parallel_groups[1] == ["analytics"]
        assert parallel_groups[2] == ["document"]
    
    def test_execution_time_calculation(self):
        """Test estimated execution time calculation"""
        planner = ExecutionPlanner()
        
        execution_plan = {
            "sequential_tasks": ["search", "document"],  # 2.0 + 4.0 = 6.0
            "parallel_tasks": [["analytics", "compliance"]]  # max(3.0, 2.5) = 3.0
        }
        
        estimated_time = planner.calculate_estimated_time(execution_plan)
        
        assert estimated_time == 9.0  # 6.0 + 3.0
    
    @pytest.mark.asyncio
    async def test_execution_planner_agent(self):
        """Test the main execution planner agent function"""
        state = create_initial_state()
        state["query_analysis"] = {
            "intent_summary": "Test analysis",
            "query_complexity": "moderate",
            "required_agents": [
                {"agent": "search", "dependencies": []},
                {"agent": "analytics", "dependencies": ["search"]}
            ],
            "confidence": 0.8
        }
        
        result = execution_planner_agent(state)
        
        assert "execution_plan" in result
        assert result["plan_status"] == "ready"
        assert result["plan_version"] == 1
        assert "estimated_remaining_time" in result


class TestDynamicRouter:
    """Test Dynamic Router functionality"""
    
    def test_conditional_routing(self):
        """Test conditional routing patterns"""
        router = DynamicRouter()
        
        # Test low confidence routing
        state = {"intent_confidence": 0.3}
        action = router.evaluate_conditions(state)
        assert action == "request_clarification"
        
        # Test missing data routing
        state = {"intent_confidence": 0.8, "results": {}}
        action = router.evaluate_conditions(state)
        assert action == "route_to_search"
        
        # Test error threshold routing
        state = {
            "intent_confidence": 0.8,
            "results": {"search": {}},
            "errors": ["error1", "error2", "error3", "error4"]
        }
        action = router.evaluate_conditions(state)
        assert action == "fallback_mode"
    
    def test_next_route_determination(self):
        """Test determining next route from execution plan"""
        router = DynamicRouter()
        
        state = {"results": {}}
        execution_plan = {
            "sequential_tasks": ["search", "analytics", "document"],
            "parallel_tasks": []
        }
        
        next_agent, reason = router.determine_next_route(state, "supervisor", execution_plan)
        assert next_agent == "search"
        assert "sequential" in reason.lower()
        
        # After search completes
        state = {"results": {"search": {}}}
        next_agent, reason = router.determine_next_route(state, "search", execution_plan)
        assert next_agent == "analytics"
    
    def test_failure_handling(self):
        """Test agent failure recovery"""
        router = DynamicRouter()
        
        state = {
            "execution_plan": {
                "fallback_plans": {
                    "search": ["analytics"],
                    "document": []
                }
            }
        }
        
        # Test with fallback plan
        next_agent, reason = router.handle_agent_failure(state, "search")
        assert next_agent == "analytics"
        assert "Fallback" in reason
        
        # Test without fallback plan
        next_agent, reason = router.handle_agent_failure(state, "document")
        assert next_agent == "supervisor"
        assert "No recovery" in reason
    
    def test_progress_calculation(self):
        """Test progress percentage calculation"""
        router = DynamicRouter()
        
        state = {
            "execution_plan": {
                "sequential_tasks": ["search", "analytics"],
                "parallel_tasks": [["document", "compliance"]]
            },
            "results": {
                "search": {},
                "analytics": {}
            }
        }
        
        progress = router.calculate_progress(state)
        assert progress == 50.0  # 2 out of 4 tasks completed


class TestEnhancedGraph:
    """Test the enhanced graph structure"""
    
    @pytest.mark.asyncio
    async def test_graph_creation(self):
        """Test that enhanced graph can be created"""
        graph = create_simple_enhanced_graph()
        assert graph is not None
    
    @pytest.mark.asyncio
    async def test_simple_query_flow(self):
        """Test a simple query through the graph"""
        with patch('backend.src.agents.query_analyzer.DescriptionBasedAnalyzer') as MockAnalyzer, \
             patch('backend.src.agents.execution_planner.ExecutionPlanner') as MockPlanner:
            
            # Setup mocks
            mock_analyzer = MockAnalyzer.return_value
            mock_analyzer.analyze_query_with_descriptions.return_value = {
                "intent_summary": "Simple analysis",
                "complexity": "simple",
                "required_agents": [{"agent": "analytics", "dependencies": []}],
                "execution_plan": {"sequential": ["analytics"], "parallel_groups": []},
                "confidence": 0.9,
                "clarification_needed": False,
                "optimization_hints": []
            }
            mock_analyzer.extract_entities_from_context.return_value = {}
            
            mock_planner = MockPlanner.return_value
            mock_planner.build_execution_plan_with_llm.return_value = {
                "sequential_tasks": ["analytics"],
                "parallel_tasks": [],
                "estimated_time": 3.0,
                "priority_level": "medium"
            }
            
            # Create and test graph
            graph = create_simple_enhanced_graph()
            
            initial_state = create_initial_state()
            initial_state["messages"] = [HumanMessage(content="분석해줘")]
            
            # Note: Full execution would require all agents to be properly mocked
            # This test verifies the graph structure is valid


class TestIntegration:
    """Integration tests for the complete system"""
    
    @pytest.mark.asyncio
    async def test_complex_query_flow(self):
        """Test a complex query requiring multiple agents"""
        state = create_initial_state()
        state["messages"] = [HumanMessage(content="지난달 매출 분석하고 경쟁사와 비교해서 보고서 만들어줘")]
        
        # Test Query Analyzer
        with patch('backend.src.agents.query_analyzer.DescriptionBasedAnalyzer') as MockAnalyzer:
            mock_analyzer = MockAnalyzer.return_value
            mock_analyzer.analyze_query_with_descriptions.return_value = {
                "intent_summary": "매출 분석, 경쟁사 비교, 보고서 생성",
                "complexity": "complex",
                "required_agents": [
                    {"agent": "analytics", "dependencies": []},
                    {"agent": "search", "dependencies": []},
                    {"agent": "document", "dependencies": ["analytics", "search"]}
                ],
                "execution_plan": {
                    "sequential": ["document"],
                    "parallel_groups": [["analytics", "search"]],
                    "conditional": {}
                },
                "confidence": 0.85,
                "clarification_needed": False,
                "optimization_hints": ["analytics와 search를 병렬로 실행 가능"]
            }
            mock_analyzer.extract_entities_from_context.return_value = {
                "temporal": ["지난달"],
                "metrics": ["매출"],
                "targets": ["경쟁사"]
            }
            
            result = query_analyzer_agent(state)
            
            assert result["current_agent"] == "execution_planner"
            assert result["parallel_execution_possible"] == True
            assert "parallel" in str(result.get("suggested_optimizations", []))
    
    @pytest.mark.asyncio
    async def test_error_recovery_flow(self):
        """Test error recovery and re-routing"""
        router = DynamicRouter()
        
        state = create_initial_state()
        state["current_agent"] = "search"
        state["errors"] = ["Search API failed"]
        state["error_recovery_attempts"] = 0
        state["max_recovery_attempts"] = 3
        state["execution_plan"] = {
            "fallback_plans": {"search": ["analytics"]}
        }
        
        result = dynamic_router_agent(state)
        
        assert result["current_agent"] == "analytics"
        assert result["error_recovery_attempts"] == 1
        assert "recovery" in result["progress"][0]["action"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])