"""
Query Analyzer Agent - Description-based Intent Classification
Uses LLM to understand query context through detailed agent descriptions
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json
import re
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from ..state.enhanced_state import (
    EnhancedAgentState, 
    IntentType, 
    SecondaryIntent,
    QueryComplexity,
    calculate_confidence_level
)


# Agent descriptions for LLM understanding
AGENT_DESCRIPTIONS = {
    "analytics": {
        "name": "Analytics Agent",
        "description": "데이터 분석 및 인사이트 도출 전문 에이전트",
        "capabilities": [
            "매출, 수익, 성장률 등 KPI 분석",
            "시계열 데이터 트렌드 분석",
            "성과 지표 계산 및 평가",
            "데이터 패턴 및 이상치 탐지",
            "통계적 분석 및 상관관계 파악"
        ],
        "triggers": [
            "데이터를 분석해야 할 때",
            "트렌드나 패턴을 찾아야 할 때",
            "KPI나 성과 지표를 계산해야 할 때",
            "인사이트가 필요할 때"
        ],
        "output": "분석 결과, 인사이트, 지표, 그래프"
    },
    "search": {
        "name": "Search Agent",
        "description": "정보 검색 및 데이터 수집 전문 에이전트",
        "capabilities": [
            "회사 정보 검색 및 수집",
            "제품/서비스 정보 조회",
            "시장 데이터 검색",
            "경쟁사 정보 수집",
            "고객 정보 및 피드백 검색"
        ],
        "triggers": [
            "특정 정보를 찾아야 할 때",
            "데이터를 수집해야 할 때",
            "외부 정보가 필요할 때",
            "최신 정보를 확인해야 할 때"
        ],
        "output": "검색 결과, 수집된 데이터, 정보 목록"
    },
    "document": {
        "name": "Document Agent",
        "description": "문서 생성 및 보고서 작성 전문 에이전트",
        "capabilities": [
            "보고서 자동 생성",
            "제안서 및 계획서 작성",
            "분석 결과 문서화",
            "프레젠테이션 자료 생성",
            "요약 문서 작성"
        ],
        "triggers": [
            "보고서를 만들어야 할 때",
            "문서를 생성해야 할 때",
            "결과를 정리해야 할 때",
            "프레젠테이션이 필요할 때"
        ],
        "output": "문서, 보고서, 프레젠테이션, PDF"
    },
    "compliance": {
        "name": "Compliance Agent",
        "description": "규정 준수 및 검증 전문 에이전트",
        "capabilities": [
            "규정 및 정책 준수 확인",
            "문서 유효성 검증",
            "리스크 평가",
            "법적 요구사항 체크",
            "감사 준비 지원"
        ],
        "triggers": [
            "규정 준수를 확인해야 할 때",
            "문서를 검증해야 할 때",
            "리스크를 평가해야 할 때",
            "감사 준비가 필요할 때"
        ],
        "output": "검증 결과, 컴플라이언스 체크리스트, 리스크 평가"
    }
}


class DescriptionBasedAnalyzer:
    """Description-based query analyzer using LLM"""
    
    def __init__(self, llm_model: str = "gpt-4o-mini", temperature: float = 0):
        self.llm = ChatOpenAI(model=llm_model, temperature=temperature)
        self.agent_descriptions = AGENT_DESCRIPTIONS
    
    def analyze_query_with_descriptions(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze query using agent descriptions instead of keywords
        Returns comprehensive analysis including required agents and execution plan
        """
        
        # Build agent description context for LLM
        agents_context = self._build_agents_context()
        
        # Include conversation context if available
        context_info = ""
        if context and context.get("conversation_history"):
            recent_history = context["conversation_history"][-3:]  # Last 3 interactions
            context_info = f"\n\n최근 대화 내용:\n{json.dumps(recent_history, ensure_ascii=False, indent=2)}"
        
        # Create comprehensive prompt
        prompt = f"""당신은 사용자의 질의를 분석하고 적절한 AI 에이전트를 선택하는 Query Analyzer입니다.

사용자 질의: "{query}"{context_info}

사용 가능한 에이전트들:
{agents_context}

분석 작업:
1. 사용자의 의도와 목적을 파악하세요
2. 필요한 에이전트들을 선택하세요 (설명과 capabilities를 기반으로)
3. 에이전트 실행 순서를 결정하세요
4. 병렬 실행 가능한 작업을 식별하세요
5. 각 에이전트가 수행할 구체적인 작업을 정의하세요

고려사항:
- 에이전트는 단독 또는 조합으로 사용 가능
- 일부 작업은 병렬로 실행 가능 (예: search와 analytics 동시 실행)
- 의존성 고려 (예: document는 보통 다른 에이전트의 결과가 필요)
- 복잡한 질의는 여러 단계로 나누어 처리

JSON 형식으로 응답하세요:
{{
    "intent_summary": "사용자 의도 요약",
    "complexity": "simple|moderate|complex|advanced",
    "required_agents": [
        {{
            "agent": "agent_name",
            "reason": "선택 이유",
            "specific_task": "구체적인 작업 내용",
            "priority": 1-5,
            "dependencies": ["의존하는 다른 에이전트"]
        }}
    ],
    "execution_plan": {{
        "sequential": ["agent1", "agent2"],
        "parallel_groups": [["agent3", "agent4"]],
        "conditional": {{
            "condition": "조건 설명",
            "if_true": ["agent5"],
            "if_false": ["agent6"]
        }}
    }},
    "estimated_time_seconds": 10,
    "confidence": 0.95,
    "clarification_needed": false,
    "suggested_clarifications": [],
    "optimization_hints": ["최적화 제안"]
}}"""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            
            # Parse JSON response
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return self._validate_and_normalize_result(result)
            else:
                raise ValueError("Invalid LLM response format")
                
        except Exception as e:
            # Return fallback analysis
            return self._create_fallback_analysis(query)
    
    def _build_agents_context(self) -> str:
        """Build formatted agent descriptions for LLM context"""
        context_lines = []
        
        for agent_key, agent_info in self.agent_descriptions.items():
            context_lines.append(f"\n{agent_key}:")
            context_lines.append(f"  이름: {agent_info['name']}")
            context_lines.append(f"  설명: {agent_info['description']}")
            context_lines.append(f"  주요 기능:")
            for capability in agent_info['capabilities']:
                context_lines.append(f"    - {capability}")
            context_lines.append(f"  사용 시점:")
            for trigger in agent_info['triggers']:
                context_lines.append(f"    - {trigger}")
            context_lines.append(f"  출력: {agent_info['output']}")
        
        return "\n".join(context_lines)
    
    def _validate_and_normalize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize LLM analysis result"""
        
        # Ensure required fields exist
        normalized = {
            "intent_summary": result.get("intent_summary", "Query analysis"),
            "complexity": result.get("complexity", "moderate"),
            "required_agents": result.get("required_agents", []),
            "execution_plan": result.get("execution_plan", {}),
            "estimated_time_seconds": result.get("estimated_time_seconds", 10),
            "confidence": min(max(result.get("confidence", 0.7), 0.0), 1.0),
            "clarification_needed": result.get("clarification_needed", False),
            "suggested_clarifications": result.get("suggested_clarifications", []),
            "optimization_hints": result.get("optimization_hints", [])
        }
        
        # Validate agent names
        valid_agents = set(self.agent_descriptions.keys())
        for agent_info in normalized["required_agents"]:
            if agent_info.get("agent") not in valid_agents:
                agent_info["agent"] = "analytics"  # Default fallback
        
        # Ensure execution plan has required structure
        if not normalized["execution_plan"]:
            # Create simple sequential plan from required agents
            agent_names = [a["agent"] for a in normalized["required_agents"]]
            normalized["execution_plan"] = {
                "sequential": agent_names,
                "parallel_groups": [],
                "conditional": {}
            }
        
        return normalized
    
    def _create_fallback_analysis(self, query: str) -> Dict[str, Any]:
        """Create a simple fallback analysis when LLM fails"""
        return {
            "intent_summary": "General query processing",
            "complexity": "moderate",
            "required_agents": [
                {
                    "agent": "analytics",
                    "reason": "Default analysis",
                    "specific_task": "Analyze query data",
                    "priority": 1,
                    "dependencies": []
                }
            ],
            "execution_plan": {
                "sequential": ["analytics"],
                "parallel_groups": [],
                "conditional": {}
            },
            "estimated_time_seconds": 5,
            "confidence": 0.3,
            "clarification_needed": True,
            "suggested_clarifications": ["Please provide more specific details about your request"],
            "optimization_hints": []
        }
    
    def extract_entities_from_context(self, query: str, analysis_result: Dict[str, Any]) -> Dict[str, List[str]]:
        """Extract entities based on the analysis context"""
        entities = {}
        
        # Extract temporal entities
        temporal_patterns = [
            r"(지난달|이번달|다음달|지난주|이번주|다음주)",
            r"(\d{4}년|\d+월|\d+일)",
            r"(Q[1-4]|[1-4]분기)",
            r"(어제|오늘|내일|모레)"
        ]
        
        for pattern in temporal_patterns:
            matches = re.findall(pattern, query)
            if matches:
                entities["temporal"] = entities.get("temporal", []) + list(matches)
        
        # Extract metrics from agent tasks
        for agent_info in analysis_result.get("required_agents", []):
            task = agent_info.get("specific_task", "")
            
            # Look for metrics in task description
            metric_keywords = ["매출", "수익", "성장률", "비용", "ROI", "KPI", "효율성"]
            found_metrics = [m for m in metric_keywords if m in task or m in query]
            if found_metrics:
                entities["metrics"] = list(set(found_metrics))
        
        # Extract targets (companies, products, etc.)
        # Look for quoted strings or proper nouns
        quoted = re.findall(r'"([^"]+)"', query)
        if quoted:
            entities["targets"] = quoted
        
        # Extract formats based on document agent involvement
        if any(a["agent"] == "document" for a in analysis_result.get("required_agents", [])):
            format_keywords = ["보고서", "문서", "프레젠테이션", "요약", "PDF"]
            found_formats = [f for f in format_keywords if f in query]
            if found_formats:
                entities["formats"] = found_formats
        
        return entities


def query_analyzer_agent(state: EnhancedAgentState) -> Dict[str, Any]:
    """
    Main query analyzer agent function for LangGraph
    Uses description-based analysis for better understanding
    """
    # Initialize analyzer
    analyzer = DescriptionBasedAnalyzer()
    
    # Get the last message
    messages = state.get("messages", [])
    if not messages:
        return {
            "errors": ["No query to analyze"],
            "current_agent": "supervisor"
        }
    
    last_message = messages[-1]
    if not isinstance(last_message, HumanMessage):
        # Not a user query, skip analysis
        return {
            "current_agent": state.get("next_agents", ["supervisor"])[0] if state.get("next_agents") else "supervisor"
        }
    
    query = last_message.content
    start_time = datetime.now()
    
    # Build context from state
    context = {
        "conversation_history": state.get("conversation_context", []),
        "previous_results": state.get("results", {}),
        "user_preferences": state.get("user_preferences", {})
    }
    
    # Perform description-based analysis
    analysis_result = analyzer.analyze_query_with_descriptions(query, context)
    
    # Extract entities from context
    entities = analyzer.extract_entities_from_context(query, analysis_result)
    
    # Map complexity to enum
    complexity_map = {
        "simple": QueryComplexity.SIMPLE,
        "moderate": QueryComplexity.MODERATE,
        "complex": QueryComplexity.COMPLEX,
        "advanced": QueryComplexity.ADVANCED
    }
    query_complexity = complexity_map.get(analysis_result["complexity"], QueryComplexity.MODERATE)
    
    # Build execution plan from analysis
    execution_plan = {
        "sequential_tasks": analysis_result["execution_plan"].get("sequential", []),
        "parallel_tasks": analysis_result["execution_plan"].get("parallel_groups", []),
        "conditional_tasks": analysis_result["execution_plan"].get("conditional", {}),
        "estimated_time": analysis_result["estimated_time_seconds"],
        "priority_level": "high" if analysis_result["confidence"] > 0.8 else "medium",
        "dependencies": {
            agent["agent"]: agent.get("dependencies", [])
            for agent in analysis_result["required_agents"]
        },
        "fallback_plans": {},
        "optimization_hints": analysis_result["optimization_hints"]
    }
    
    # Prepare query analysis result
    query_analysis = {
        "raw_query": query,
        "normalized_query": query.strip(),
        "query_language": "ko" if re.search(r'[가-힣]', query) else "en",
        "intent_summary": analysis_result["intent_summary"],
        "query_complexity": query_complexity.value,
        "estimated_steps": len(analysis_result["required_agents"]),
        "confidence": analysis_result["confidence"],
        "clarification_needed": analysis_result["clarification_needed"],
        "suggested_clarifications": analysis_result["suggested_clarifications"],
        "required_agents": analysis_result["required_agents"],
        "entities": entities
    }
    
    # Calculate processing time
    processing_time = (datetime.now() - start_time).total_seconds()
    
    # Update progress
    progress_entry = {
        "agent": "query_analyzer",
        "timestamp": datetime.now().isoformat(),
        "action": "query_analyzed",
        "details": {
            "intent": analysis_result["intent_summary"],
            "confidence": analysis_result["confidence"],
            "complexity": analysis_result["complexity"],
            "agents_required": [a["agent"] for a in analysis_result["required_agents"]]
        }
    }
    
    # Prepare response message
    confidence_level = calculate_confidence_level(analysis_result["confidence"])
    agent_list = ", ".join([a["agent"] for a in analysis_result["required_agents"]])
    
    analysis_message = AIMessage(
        content=f"Query analyzed: {analysis_result['intent_summary']}\n"
                f"Required agents: {agent_list}\n"
                f"Confidence: {confidence_level.value}",
        metadata={
            "agent": "query_analyzer",
            "analysis_complete": True,
            "requires_clarification": analysis_result["clarification_needed"]
        }
    )
    
    # Determine next agent
    next_agent = "execution_planner"
    if analysis_result["clarification_needed"] and not state.get("auto_mode", True):
        next_agent = "supervisor"  # Return to supervisor for clarification
    
    # Check for parallel execution possibilities
    parallel_possible = len(analysis_result["execution_plan"].get("parallel_groups", [])) > 0
    
    # Return state updates
    return {
        "messages": [analysis_message],
        "query_analysis": query_analysis,
        "raw_query": query,
        "normalized_query": query.strip(),
        "query_language": "ko" if re.search(r'[가-힣]', query) else "en",
        "entities": entities,
        "execution_plan": execution_plan,
        "progress": [progress_entry],
        "query_processing_time": processing_time,
        "parallel_execution_possible": parallel_possible,
        "suggested_optimizations": analysis_result["optimization_hints"],
        "current_agent": next_agent,
        "next_agents": [a["agent"] for a in analysis_result["required_agents"]],
        "llm_call_count": state.get("llm_call_count", 0) + 1,
        "context": {
            **state.get("context", {}),
            "query_analysis_complete": True,
            "analysis_result": analysis_result
        }
    }