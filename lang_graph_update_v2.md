# LangGraph 0.6.6 챗봇 개선 가이드

## 📋 현재 상태 분석 및 개선 지시사항

### 1. Tool 실행 메커니즘 개선

#### 🔴 현재 문제점
- Tool이 LLM에 바인딩만 되고 실제로는 하드코딩된 직접 호출 사용
- LLM의 판단이 아닌 개발자의 조건문으로 tool 실행 결정
- Tool 실행 결과가 LLM 컨텍스트에 제대로 전달되지 않음

#### ✅ 수정 지시사항

**파일: `backend/src/agents/analytics.py`**

1. 현재 코드에서 다음 패턴을 찾아서 수정:
```python
# 잘못된 패턴 (현재)
if "performance" in task_description.lower():
    perf_data = query_performance_data.invoke({"employee_id": context.get("employee_id")})
    analysis_results["performance"] = json.loads(perf_data)
```

2. 다음과 같이 LLM 기반 tool 실행으로 변경:
```python
# 올바른 패턴 (수정 후)
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import ToolNode

# Tool Node 생성
tool_node = ToolNode(tools)

# LLM에게 tool 사용 결정 위임
messages = [
    SystemMessage(content="You are a data analyst. Use tools to analyze the data."),
    HumanMessage(content=task_description)
]

# LLM이 tool 호출 결정
response = llm_with_tools.invoke(messages)

# Tool 호출이 있으면 실행
if response.tool_calls:
    tool_results = tool_node.invoke({"messages": [response]})
    # Tool 결과를 메시지에 추가
    messages.extend(tool_results["messages"])
    # 최종 응답 생성
    final_response = llm.invoke(messages)
```

**모든 에이전트 파일에 동일하게 적용:**
- `backend/src/agents/search.py`
- `backend/src/agents/document.py`
- `backend/src/agents/compliance.py`

### 2. 병렬 실행 구현

#### 🔴 현재 문제점
- `parallel_tasks`와 `dependencies` 필드가 State에 정의되어 있지만 사용되지 않음
- 모든 에이전트가 순차적으로만 실행됨
- 독립적인 작업도 순서대로 기다려야 함

#### ✅ 수정 지시사항

**파일: `backend/src/agents/supervisor.py`**

1. 병렬 실행 가능 여부 판단 로직 추가:
```python
def analyze_dependencies(user_request: str) -> Dict[str, List[str]]:
    """
    작업 간 의존성 분석
    예: document는 search 결과가 필요, compliance는 document가 필요
    """
    dependencies = {
        "analytics": [],  # 독립적 실행 가능
        "search": [],     # 독립적 실행 가능
        "document": ["search", "analytics"],  # search와 analytics 후 실행
        "compliance": ["document"]  # document 후 실행
    }
    return dependencies

def identify_parallel_tasks(execution_plan: List[str], dependencies: Dict) -> List[List[str]]:
    """
    병렬 실행 가능한 작업 그룹 식별
    """
    parallel_groups = []
    completed = set()
    
    while len(completed) < len(execution_plan):
        current_group = []
        for agent in execution_plan:
            if agent not in completed:
                deps = dependencies.get(agent, [])
                if all(d in completed for d in deps):
                    current_group.append(agent)
        
        if current_group:
            parallel_groups.append(current_group)
            completed.update(current_group)
    
    return parallel_groups
```

2. Supervisor agent에서 병렬 실행 계획 수립:
```python
# supervisor_agent 함수 내부 수정
parallel_groups = identify_parallel_tasks(planned_agents, dependencies)

updated_context = {
    **context,
    "execution_plan": planned_agents,
    "parallel_groups": parallel_groups,  # [[analytics, search], [document], [compliance]]
    "current_group": 0
}
```

**파일: `backend/src/core/graph.py`**

3. 병렬 실행 노드 추가:
```python
async def parallel_executor(state: AgentState) -> dict:
    """병렬 실행 노드"""
    current_group = state["parallel_groups"][state["current_group"]]
    
    # 병렬 실행
    tasks = []
    for agent_name in current_group:
        agent_func = {
            "analytics": analytics_agent,
            "search": search_agent,
            "document": document_agent,
            "compliance": compliance_agent
        }[agent_name]
        tasks.append(agent_func(state))
    
    # 모든 작업 완료 대기
    results = await asyncio.gather(*tasks)
    
    # 결과 병합
    merged_results = state.get("results", {})
    for result in results:
        merged_results.update(result.get("results", {}))
    
    return {
        **state,
        "results": merged_results,
        "current_group": state["current_group"] + 1
    }

# Graph에 추가
graph.add_node("parallel_executor", parallel_executor)
```

### 3. 라우팅 최적화

#### 🔴 현재 문제점
- 모든 에이전트가 무조건 supervisor로 돌아감
- Document → Compliance 직접 라우팅이 있지만 제한적
- 불필요한 supervisor 재방문으로 성능 저하

#### ✅ 수정 지시사항

**파일: `backend/src/core/graph.py`**

1. 조건부 라우팅 강화:
```python
def smart_routing(state: AgentState) -> str:
    """지능형 라우팅 함수"""
    current = state.get("current_agent")
    context = state.get("context", {})
    results = state.get("results", {})
    
    # Document 완료 후 자동으로 Compliance로
    if current == "document" and context.get("requires_compliance"):
        return "compliance"
    
    # Analytics와 Search가 모두 완료되면 Document로
    if current in ["analytics", "search"]:
        if "analytics" in results and "search" in results:
            return "document"
    
    # Compliance 완료 후 재작업 필요 여부 확인
    if current == "compliance":
        if context.get("needs_rework"):
            return context.get("rework_target", "document")
        return END
    
    # 기본: supervisor로
    return "supervisor"

# 각 에이전트에 조건부 라우팅 적용
graph.add_conditional_edges("analytics", smart_routing)
graph.add_conditional_edges("search", smart_routing)
graph.add_conditional_edges("document", smart_routing)
graph.add_conditional_edges("compliance", smart_routing)
```

### 4. State 타입 안전성 강화

#### 🔴 현재 문제점
- results 필드가 느슨한 타입 정의
- 에이전트 간 데이터 구조 불일치 가능
- 런타임 에러 위험

#### ✅ 수정 지시사항

**파일: `backend/src/state/agent_state.py`**

1. Strict typing 추가:
```python
from typing import TypedDict, Required, NotRequired
from pydantic import BaseModel, Field

class AnalyticsResult(BaseModel):
    timestamp: str
    analysis: str
    raw_data: Dict[str, Any]
    key_insights: Dict[str, Any]
    status: Literal["success", "error", "pending"]

class SearchResult(BaseModel):
    timestamp: str
    query: str
    search_stats: Dict[str, Any]
    merged_results: Dict[str, Any]
    status: Literal["success", "error", "pending"]

class StrictAgentResults(TypedDict):
    analytics: NotRequired[AnalyticsResult]
    search: NotRequired[SearchResult]
    document: NotRequired[Dict]
    compliance: NotRequired[Dict]

# AgentState 수정
class AgentState(MessagesState):
    results: StrictAgentResults  # 타입 강화
```

### 5. 에러 복구 메커니즘

#### 🔴 현재 문제점
- 에러 발생 시 단순 로깅만 수행
- 복구 전략 없음
- 전체 실행 중단 위험

#### ✅ 수정 지시사항

**파일: `backend/src/agents/supervisor.py`**

1. 재시도 로직 추가:
```python
class RetryStrategy:
    MAX_RETRIES = 3
    BACKOFF_FACTOR = 2
    
    @staticmethod
    async def execute_with_retry(agent_func, state, agent_name):
        retries = 0
        last_error = None
        
        while retries < RetryStrategy.MAX_RETRIES:
            try:
                result = await agent_func(state)
                # 성공 시 에러 카운터 리셋
                state["context"][f"{agent_name}_errors"] = 0
                return result
            except Exception as e:
                retries += 1
                last_error = e
                wait_time = RetryStrategy.BACKOFF_FACTOR ** retries
                logger.warning(f"Agent {agent_name} failed (attempt {retries}), retrying in {wait_time}s")
                await asyncio.sleep(wait_time)
                
                # State에 에러 정보 저장
                state["context"][f"{agent_name}_errors"] = retries
                state["errors"].append({
                    "agent": agent_name,
                    "error": str(e),
                    "attempt": retries,
                    "timestamp": datetime.now().isoformat()
                })
        
        # 최대 재시도 후 폴백
        return fallback_response(agent_name, last_error, state)

def fallback_response(agent_name: str, error: Exception, state: AgentState) -> dict:
    """에러 발생 시 폴백 응답 생성"""
    fallback_data = {
        "analytics": {"analysis": "분석 실패 - 기본 데이터 사용", "status": "fallback"},
        "search": {"results": [], "status": "fallback"},
        "document": {"document": "문서 생성 실패", "status": "fallback"},
        "compliance": {"compliance_status": "UNKNOWN", "status": "fallback"}
    }
    
    return {
        **state,
        "results": {
            **state.get("results", {}),
            agent_name: fallback_data.get(agent_name, {})
        },
        "context": {
            **state.get("context", {}),
            f"{agent_name}_fallback": True
        }
    }
```

### 6. Tool 통합 테스트 추가

#### ✅ 구현 지시사항

**새 파일: `backend/tests/test_tools_integration.py`**

```python
import pytest
from unittest.mock import Mock, patch
from src.agents.analytics import analytics_agent
from src.state.agent_state import AgentState

@pytest.mark.asyncio
async def test_tool_execution_flow():
    """Tool 실행 흐름 테스트"""
    # Mock state 생성
    state = {
        "messages": [HumanMessage(content="분석해줘")],
        "task_description": "매출 분석",
        "context": {},
        "results": {}
    }
    
    # Tool 실행 확인
    with patch('src.tools.analytics_tools.query_performance_data') as mock_tool:
        mock_tool.invoke.return_value = '{"test": "data"}'
        result = await analytics_agent(state)
        
        # Tool이 호출되었는지 확인
        assert mock_tool.invoke.called
        # 결과가 state에 저장되었는지 확인
        assert "analytics" in result["results"]

@pytest.mark.asyncio
async def test_parallel_execution():
    """병렬 실행 테스트"""
    # 병렬 실행 가능한 작업 테스트
    state = {
        "parallel_groups": [["analytics", "search"]],
        "current_group": 0
    }
    
    # 두 에이전트가 동시에 실행되는지 확인
    start_time = time.time()
    result = await parallel_executor(state)
    execution_time = time.time() - start_time
    
    # 순차 실행보다 빠른지 확인
    assert execution_time < 2.0  # 병렬이면 2초 이내
```

### 7. 모니터링 및 로깅 개선

#### ✅ 구현 지시사항

**파일: `backend/src/core/monitoring.py` (새 파일)**

```python
from prometheus_client import Counter, Histogram, Gauge
import time

# Metrics 정의
agent_execution_counter = Counter('agent_executions_total', 'Total agent executions', ['agent_name'])
agent_execution_time = Histogram('agent_execution_seconds', 'Agent execution time', ['agent_name'])
tool_usage_counter = Counter('tool_usage_total', 'Total tool usage', ['tool_name'])
error_counter = Counter('agent_errors_total', 'Total agent errors', ['agent_name'])

class PerformanceMonitor:
    @staticmethod
    def track_agent_execution(agent_name: str):
        def decorator(func):
            async def wrapper(state):
                start_time = time.time()
                agent_execution_counter.labels(agent_name=agent_name).inc()
                
                try:
                    result = await func(state)
                    execution_time = time.time() - start_time
                    agent_execution_time.labels(agent_name=agent_name).observe(execution_time)
                    
                    # State에 성능 메트릭 추가
                    state["context"][f"{agent_name}_execution_time"] = execution_time
                    return result
                except Exception as e:
                    error_counter.labels(agent_name=agent_name).inc()
                    raise
            
            return wrapper
        return decorator

# 각 에이전트에 적용
@PerformanceMonitor.track_agent_execution("analytics")
async def analytics_agent_monitored(state: AgentState) -> dict:
    return await analytics_agent(state)
```

## 📝 구현 우선순위

1. **높음**: Tool 실행 메커니즘 개선 (LLM 기반 실행)
2. **높음**: 에러 복구 메커니즘 구현
3. **중간**: 병렬 실행 구현
4. **중간**: 라우팅 최적화
5. **낮음**: State 타입 안전성 강화
6. **낮음**: 모니터링 및 로깅 개선

## 🎯 예상 성과

- **성능 향상**: 병렬 실행으로 30-50% 응답 시간 단축
- **안정성 향상**: 에러 복구로 99% 이상 가용성
- **유연성 향상**: LLM 기반 tool 실행으로 다양한 쿼리 처리
- **유지보수성 향상**: 타입 안전성과 모니터링으로 디버깅 시간 50% 단축