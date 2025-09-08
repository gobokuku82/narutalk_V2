# LangGraph 0.6.6 챗봇 개선 가이드 (수정판)

## 📋 현재 상태 분석 및 개선 지시사항

### ⚠️ 핵심 규칙 (MUST FOLLOW)

1. **동시성 안전성**: 모든 State 수정은 thread-safe해야 함
2. **스트리밍 순서**: WebSocket 메시지는 논리적 순서 유지 필수
3. **부분 실패 허용**: 한 에이전트 실패가 전체 중단으로 이어지면 안됨
4. **메모리 제한**: 동시 실행 에이전트는 최대 3개로 제한
5. **Checkpointer 호환**: SQLite 사용 시 WAL 모드 필수

---

## 🚀 Phase 0: 기초 안전장치 구현 [최우선]

### 0.1 State 동시성 보호

#### ✅ 구현 지시사항

**새 파일: `backend/src/core/concurrency.py`**

```python
import asyncio
from threading import Lock
from typing import Dict, Any
from contextlib import contextmanager
import copy

class ThreadSafeState:
    """Thread-safe State wrapper for parallel execution"""
    
    def __init__(self, state: Dict[str, Any]):
        self._state = state
        self._lock = asyncio.Lock()
        self._write_locks = {}  # Per-agent write locks
    
    async def get(self, key: str, default=None):
        """Thread-safe read"""
        async with self._lock:
            return copy.deepcopy(self._state.get(key, default))
    
    async def update_results(self, agent_name: str, data: Dict):
        """Thread-safe results update"""
        async with self._lock:
            if "results" not in self._state:
                self._state["results"] = {}
            self._state["results"][agent_name] = data
            
            # Update progress
            if "progress" not in self._state:
                self._state["progress"] = []
            self._state["progress"].append({
                "agent": agent_name,
                "timestamp": datetime.now().isoformat(),
                "action": "completed"
            })
    
    async def get_snapshot(self) -> Dict:
        """Get complete state snapshot"""
        async with self._lock:
            return copy.deepcopy(self._state)
    
    def to_dict(self) -> Dict:
        """Convert back to regular dict for graph compatibility"""
        return self._state
```

### 0.2 Checkpointer 최적화

#### ✅ 구현 지시사항

**파일: `backend/src/core/graph.py` 수정**

```python
def create_optimized_checkpointer(use_sqlite: bool = False):
    """Create optimized checkpointer with concurrency support"""
    if use_sqlite and SqliteSaver:
        db_path = os.path.join(os.path.dirname(__file__), "..", "..", "checkpoints.db")
        
        # Enable WAL mode for concurrent access
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.close()
        
        return SqliteSaver.from_conn_string(f"sqlite:///{db_path}")
    else:
        # Consider Redis for production
        return MemorySaver()
```

### 0.3 WebSocket 스트리밍 조정자

#### ✅ 구현 지시사항

**새 파일: `backend/src/core/streaming.py`**

```python
import asyncio
from typing import Dict, List, Any
from collections import OrderedDict

class StreamingCoordinator:
    """Coordinate streaming messages during parallel execution"""
    
    def __init__(self):
        self.message_queues: Dict[str, asyncio.Queue] = {}
        self.agent_order = []
        self.completed_agents = set()
    
    async def register_agent(self, agent_name: str):
        """Register an agent for streaming coordination"""
        if agent_name not in self.message_queues:
            self.message_queues[agent_name] = asyncio.Queue()
    
    async def queue_message(self, agent_name: str, message: Dict):
        """Queue a message from an agent"""
        if agent_name in self.message_queues:
            await self.message_queues[agent_name].put(message)
    
    async def stream_in_order(self, websocket, client_id: str, parallel_groups: List[List[str]]):
        """Stream messages maintaining logical order"""
        for group in parallel_groups:
            # Collect messages from parallel agents
            group_messages = OrderedDict()
            
            # Start collectors for each agent in group
            tasks = []
            for agent in group:
                tasks.append(self._collect_agent_messages(agent, group_messages))
            
            # Wait for all agents in group
            await asyncio.gather(*tasks)
            
            # Stream collected messages in order
            for agent in group:
                if agent in group_messages:
                    for message in group_messages[agent]:
                        await websocket.send_json({
                            "type": "agent_output",
                            "agent": agent,
                            "message": message,
                            "timestamp": datetime.now().isoformat()
                        })
    
    async def _collect_agent_messages(self, agent_name: str, storage: OrderedDict):
        """Collect all messages from an agent"""
        storage[agent_name] = []
        queue = self.message_queues.get(agent_name)
        
        if queue:
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=0.1)
                    storage[agent_name].append(message)
                except asyncio.TimeoutError:
                    break
```

---

## 🚀 Phase 1: Tool 실행 메커니즘 개선 [높음]

### 1.1 LLM 기반 Tool 실행 구현

#### ✅ 구현 지시사항

**파일: `backend/src/agents/analytics.py` 수정**

```python
from langchain_core.messages import ToolMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from typing import List, Dict, Any

async def analytics_agent_with_llm_tools(state: AgentState) -> dict:
    """Enhanced Analytics agent with LLM-based tool execution"""
    
    # Thread-safe state wrapper
    safe_state = ThreadSafeState(state)
    
    # Initialize LLM
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    # Define tools
    tools = [
        query_performance_data,
        analyze_sales_trend,
        calculate_kpis,
        predict_sales_trend
    ]
    
    # Create ReAct agent for tool execution
    tool_executor = create_react_agent(llm, tools)
    
    # Get task and context
    task_description = await safe_state.get("task_description", "")
    context = await safe_state.get("context", {})
    
    # Prepare prompt with context
    enhanced_prompt = f"""
    Task: {task_description}
    
    Available context:
    - Previous results: {await safe_state.get("results", {})}
    
    Instructions:
    1. Analyze what data is needed
    2. Use appropriate tools to gather data
    3. Synthesize insights from the data
    4. Provide actionable recommendations
    
    Available tools: {[tool.name for tool in tools]}
    """
    
    try:
        # Execute with tools
        result = await tool_executor.ainvoke({
            "messages": [HumanMessage(content=enhanced_prompt)]
        })
        
        # Extract tool usage and results
        tool_calls = []
        analysis_results = {}
        
        for message in result["messages"]:
            if hasattr(message, "tool_calls"):
                tool_calls.extend(message.tool_calls)
            if isinstance(message, ToolMessage):
                # Parse tool results
                try:
                    tool_result = json.loads(message.content)
                    analysis_results[message.name] = tool_result
                except:
                    analysis_results[message.name] = message.content
        
        # Update state safely
        await safe_state.update_results("analytics", {
            "timestamp": datetime.now().isoformat(),
            "analysis": result["messages"][-1].content if result["messages"] else "",
            "raw_data": analysis_results,
            "tool_calls": tool_calls,
            "status": "success"
        })
        
        return safe_state.to_dict()
        
    except Exception as e:
        logger.error(f"Error in analytics agent: {str(e)}")
        # Fallback handling
        return await handle_agent_error("analytics", e, safe_state)
```

### 1.2 Tool Node를 Graph에 통합

#### ✅ 구현 지시사항

**파일: `backend/src/core/graph.py` 수정**

```python
from langgraph.prebuilt import ToolNode

def create_sales_support_graph(use_sqlite: bool = False):
    """Create graph with integrated tool nodes"""
    
    # Initialize StateGraph
    graph = StateGraph(AgentState)
    
    # Add agent nodes
    graph.add_node("supervisor", supervisor_agent)
    graph.add_node("analytics", analytics_agent_with_llm_tools)  # Updated
    graph.add_node("search", search_agent_with_llm_tools)  # Updated
    graph.add_node("document", document_agent_with_llm_tools)  # Updated
    graph.add_node("compliance", compliance_agent_with_llm_tools)  # Updated
    
    # Add tool nodes for each agent (optional - for explicit tool execution)
    graph.add_node("analytics_tools", ToolNode(analytics_tools))
    graph.add_node("search_tools", ToolNode(search_tools))
    
    # Add parallel executor
    graph.add_node("parallel_executor", parallel_executor)
    
    # Entry point
    graph.add_edge(START, "supervisor")
    
    # Smart routing with parallel execution
    graph.add_conditional_edges(
        "supervisor",
        determine_execution_path,
        {
            "parallel": "parallel_executor",
            "sequential": route_by_task_type,
            "end": END
        }
    )
    
    # Tool node connections (if needed)
    graph.add_conditional_edges(
        "analytics",
        lambda x: "analytics_tools" if x.get("needs_tools") else "supervisor"
    )
    
    # Optimized checkpointer
    checkpointer = create_optimized_checkpointer(use_sqlite)
    
    return graph.compile(checkpointer=checkpointer)
```

---

## 🚀 Phase 2: 에러 복구 메커니즘 [높음]

### 2.1 재시도 전략 구현

#### ✅ 구현 지시사항

**새 파일: `backend/src/core/retry_strategy.py`**

```python
import asyncio
from typing import Callable, Dict, Any, Optional
from functools import wraps
from loguru import logger
from enum import Enum

class RetryPolicy(Enum):
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIBONACCI = "fibonacci"

class CircuitBreaker:
    """Circuit breaker pattern for agent protection"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = {}
        self.last_failure_time = {}
    
    def is_open(self, agent_name: str) -> bool:
        """Check if circuit is open (blocking requests)"""
        if agent_name not in self.failures:
            return False
        
        if self.failures[agent_name] >= self.failure_threshold:
            time_since_failure = time.time() - self.last_failure_time.get(agent_name, 0)
            if time_since_failure < self.timeout:
                return True
            else:
                # Reset after timeout
                self.reset(agent_name)
        return False
    
    def record_failure(self, agent_name: str):
        """Record a failure"""
        self.failures[agent_name] = self.failures.get(agent_name, 0) + 1
        self.last_failure_time[agent_name] = time.time()
    
    def record_success(self, agent_name: str):
        """Record a success and reset counter"""
        self.reset(agent_name)
    
    def reset(self, agent_name: str):
        """Reset circuit breaker for agent"""
        self.failures[agent_name] = 0
        self.last_failure_time.pop(agent_name, None)

# Global circuit breaker
circuit_breaker = CircuitBreaker()

class RetryStrategy:
    MAX_RETRIES = 3
    BASE_DELAY = 1  # seconds
    MAX_DELAY = 30  # seconds
    
    @staticmethod
    def calculate_delay(attempt: int, policy: RetryPolicy = RetryPolicy.EXPONENTIAL) -> float:
        """Calculate retry delay based on policy"""
        if policy == RetryPolicy.EXPONENTIAL:
            delay = min(RetryStrategy.BASE_DELAY * (2 ** attempt), RetryStrategy.MAX_DELAY)
        elif policy == RetryPolicy.LINEAR:
            delay = min(RetryStrategy.BASE_DELAY * attempt, RetryStrategy.MAX_DELAY)
        else:  # Fibonacci
            fib = [1, 1]
            for _ in range(attempt):
                fib.append(fib[-1] + fib[-2])
            delay = min(RetryStrategy.BASE_DELAY * fib[attempt], RetryStrategy.MAX_DELAY)
        
        # Add jitter to prevent thundering herd
        import random
        jitter = random.uniform(0, delay * 0.1)
        return delay + jitter
    
    @staticmethod
    def with_retry(agent_name: str, policy: RetryPolicy = RetryPolicy.EXPONENTIAL):
        """Decorator for retry logic"""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
                # Check circuit breaker
                if circuit_breaker.is_open(agent_name):
                    logger.warning(f"Circuit breaker open for {agent_name}")
                    return RetryStrategy.create_fallback_response(agent_name, "Circuit breaker open", state)
                
                last_error = None
                
                for attempt in range(RetryStrategy.MAX_RETRIES):
                    try:
                        result = await func(state)
                        circuit_breaker.record_success(agent_name)
                        return result
                        
                    except Exception as e:
                        last_error = e
                        logger.warning(f"Agent {agent_name} attempt {attempt + 1} failed: {str(e)}")
                        
                        if attempt < RetryStrategy.MAX_RETRIES - 1:
                            delay = RetryStrategy.calculate_delay(attempt, policy)
                            logger.info(f"Retrying {agent_name} in {delay:.2f} seconds...")
                            await asyncio.sleep(delay)
                        
                        # Record error in state
                        if "errors" not in state:
                            state["errors"] = []
                        state["errors"].append({
                            "agent": agent_name,
                            "error": str(e),
                            "attempt": attempt + 1,
                            "timestamp": datetime.now().isoformat()
                        })
                
                # All retries failed
                circuit_breaker.record_failure(agent_name)
                logger.error(f"Agent {agent_name} failed after {RetryStrategy.MAX_RETRIES} attempts")
                return RetryStrategy.create_fallback_response(agent_name, last_error, state)
            
            return wrapper
        return decorator
    
    @staticmethod
    def create_fallback_response(agent_name: str, error: Any, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create fallback response for failed agent"""
        fallback_data = {
            "analytics": {
                "analysis": "Analysis temporarily unavailable - using cached data",
                "status": "fallback",
                "cached_data": state.get("context", {}).get("last_analytics", {})
            },
            "search": {
                "results": [],
                "status": "fallback",
                "message": "Search service temporarily unavailable"
            },
            "document": {
                "document": "Document generation failed - please retry",
                "status": "fallback"
            },
            "compliance": {
                "compliance_status": "PENDING",
                "status": "fallback",
                "message": "Compliance check pending - manual review required"
            }
        }
        
        # Update state with fallback
        if "results" not in state:
            state["results"] = {}
        state["results"][agent_name] = fallback_data.get(agent_name, {"status": "fallback"})
        
        # Mark as needing retry
        state["context"] = state.get("context", {})
        state["context"][f"{agent_name}_needs_retry"] = True
        state["context"][f"{agent_name}_fallback_used"] = True
        
        return state

# Apply retry decorator to all agents
@RetryStrategy.with_retry("analytics")
async def analytics_agent_with_retry(state: AgentState) -> dict:
    return await analytics_agent_with_llm_tools(state)
```

---

## 🚀 Phase 3: 병렬 실행 구현 [중간]

### 3.1 리소스 제한된 병렬 실행

#### ✅ 구현 지시사항

**파일: `backend/src/core/graph.py` 추가**

```python
import asyncio
from typing import List, Dict, Any

class ParallelExecutor:
    MAX_CONCURRENT = 3  # Resource limit
    
    def __init__(self, streaming_coordinator: StreamingCoordinator = None):
        self.coordinator = streaming_coordinator or StreamingCoordinator()
        self.semaphore = asyncio.Semaphore(self.MAX_CONCURRENT)
    
    async def execute_parallel_groups(self, state: AgentState) -> dict:
        """Execute agents in parallel groups with resource limits"""
        safe_state = ThreadSafeState(state)
        
        # Get execution plan
        parallel_groups = state.get("context", {}).get("parallel_groups", [])
        
        if not parallel_groups:
            logger.warning("No parallel groups defined")
            return state
        
        # Process each group
        for group_idx, group in enumerate(parallel_groups):
            logger.info(f"Executing parallel group {group_idx}: {group}")
            
            # Create tasks with resource limits
            tasks = []
            for agent_name in group:
                agent_func = self._get_agent_function(agent_name)
                if agent_func:
                    # Wrap with semaphore for resource limiting
                    task = self._execute_with_limit(agent_func, safe_state, agent_name)
                    tasks.append(task)
            
            # Execute with partial failure handling
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                agent_name = group[i]
                
                if isinstance(result, Exception):
                    logger.error(f"Agent {agent_name} failed in parallel execution: {result}")
                    # Use fallback
                    fallback_state = RetryStrategy.create_fallback_response(
                        agent_name, result, safe_state.to_dict()
                    )
                    await safe_state.update_results(agent_name, 
                        fallback_state["results"].get(agent_name, {}))
                else:
                    # Success - merge results
                    if isinstance(result, dict) and "results" in result:
                        agent_results = result["results"].get(agent_name, {})
                        await safe_state.update_results(agent_name, agent_results)
            
            # Update progress
            state["context"]["completed_groups"] = group_idx + 1
        
        return safe_state.to_dict()
    
    async def _execute_with_limit(self, agent_func, safe_state, agent_name):
        """Execute agent with resource limits"""
        async with self.semaphore:
            logger.info(f"Starting {agent_name} (semaphore acquired)")
            
            # Monitor memory usage
            import psutil
            process = psutil.Process()
            mem_before = process.memory_info().rss / 1024 / 1024  # MB
            
            try:
                result = await agent_func(safe_state.to_dict())
                
                mem_after = process.memory_info().rss / 1024 / 1024  # MB
                mem_increase = mem_after - mem_before
                
                if mem_increase > 100:  # Warning if >100MB increase
                    logger.warning(f"Agent {agent_name} increased memory by {mem_increase:.2f}MB")
                
                return result
                
            finally:
                logger.info(f"Completed {agent_name} (semaphore released)")
    
    def _get_agent_function(self, agent_name: str):
        """Get agent function by name"""
        agents = {
            "analytics": analytics_agent_with_retry,
            "search": search_agent_with_retry,
            "document": document_agent_with_retry,
            "compliance": compliance_agent_with_retry
        }
        return agents.get(agent_name)

# Create global parallel executor
parallel_executor_instance = ParallelExecutor()

async def parallel_executor(state: AgentState) -> dict:
    """Parallel executor node for graph"""
    return await parallel_executor_instance.execute_parallel_groups(state)
```

### 3.2 의존성 분석 및 그룹화

#### ✅ 구현 지시사항

**파일: `backend/src/agents/supervisor.py` 수정**

```python
def analyze_task_dependencies(user_request: str, agents_needed: List[str]) -> Dict[str, List[str]]:
    """Analyze dependencies between agents"""
    # Define static dependencies
    dependencies = {
        "analytics": [],  # Can run independently
        "search": [],     # Can run independently
        "document": [],   # Now can run independently with fallback
        "compliance": ["document"]  # Must run after document
    }
    
    # Dynamic dependency injection based on request
    request_lower = user_request.lower()
    
    # If document generation needs data, add dependencies
    if "document" in agents_needed:
        if "분석" in request_lower or "analysis" in request_lower:
            dependencies["document"].append("analytics")
        if "검색" in request_lower or "search" in request_lower:
            dependencies["document"].append("search")
    
    return dependencies

def create_parallel_groups(agents: List[str], dependencies: Dict[str, List[str]]) -> List[List[str]]:
    """Create optimal parallel execution groups"""
    groups = []
    completed = set()
    remaining = set(agents)
    
    while remaining:
        current_group = []
        
        for agent in remaining:
            agent_deps = dependencies.get(agent, [])
            # Can execute if all dependencies are completed
            if all(dep in completed for dep in agent_deps):
                current_group.append(agent)
        
        if not current_group:
            # Circular dependency or error
            logger.error(f"Cannot resolve dependencies for agents: {remaining}")
            current_group = list(remaining)  # Force execution
        
        groups.append(current_group)
        completed.update(current_group)
        remaining -= set(current_group)
    
    return groups

# Update supervisor_agent function
def supervisor_agent(state: AgentState) -> dict:
    """Enhanced supervisor with parallel execution planning"""
    # ... existing code ...
    
    # After determining agents needed
    planned_agents = execution_plan.get("agents", ["analytics"])
    
    # Analyze dependencies
    dependencies = analyze_task_dependencies(user_request, planned_agents)
    
    # Create parallel groups
    parallel_groups = create_parallel_groups(planned_agents, dependencies)
    
    # Determine execution mode
    execution_mode = "parallel" if len(parallel_groups[0]) > 1 else "sequential"
    
    updated_context = {
        **context,
        "execution_plan": planned_agents,
        "dependencies": dependencies,
        "parallel_groups": parallel_groups,
        "execution_mode": execution_mode,
        "current_group": 0
    }
    
    # Route to parallel executor if needed
    if execution_mode == "parallel":
        return {
            **state,
            "context": updated_context,
            "next_node": "parallel_executor"
        }
    
    # ... rest of existing code ...
```

---

## 🚀 Phase 4: 라우팅 최적화 [중간]

### 4.1 스마트 라우팅 구현

#### ✅ 구현 지시사항

**파일: `backend/src/core/graph.py` 수정**

```python
def create_smart_router():
    """Create intelligent routing function"""
    
    def smart_route(state: AgentState) -> str:
        current_agent = state.get("current_agent")
        context = state.get("context", {})
        results = state.get("results", {})
        errors = state.get("errors", [])
        
        # Check for critical errors
        recent_errors = [e for e in errors if e.get("agent") == current_agent]
        if len(recent_errors) >= 3:
            logger.error(f"Agent {current_agent} failed multiple times, ending")
            return END
        
        # Parallel execution mode
        if context.get("execution_mode") == "parallel":
            current_group = context.get("current_group", 0)
            parallel_groups = context.get("parallel_groups", [])
            
            if current_group < len(parallel_groups) - 1:
                return "parallel_executor"
        
        # Direct routing rules
        routing_rules = {
            ("document", "requires_compliance"): "compliance",
            ("compliance", "needs_rework"): lambda: context.get("rework_target", "document"),
            ("analytics", "search_needed"): "search",
            ("search", "document_ready"): "document"
        }
        
        for (agent, condition), target in routing_rules.items():
            if current_agent == agent and context.get(condition):
                if callable(target):
                    return target()
                return target
        
        # Check if all planned agents completed
        execution_plan = context.get("execution_plan", [])
        completed_agents = list(results.keys())
        
        if all(agent in completed_agents for agent in execution_plan):
            return END
        
        # Default to supervisor for coordination
        return "supervisor"
    
    return smart_route

# Apply to graph
smart_router = create_smart_router()

graph.add_conditional_edges("analytics", smart_router)
graph.add_conditional_edges("search", smart_router)
graph.add_conditional_edges("document", smart_router)
graph.add_conditional_edges("compliance", smart_router)
graph.add_conditional_edges("parallel_executor", smart_router)
```

---

## 📝 구현 우선순위 및 일정

### 우선순위별 구현 계획

1. **Phase 0**: 기초 안전장치 [1시간]
   - ThreadSafeState 구현
   - Checkpointer 최적화
   - StreamingCoordinator 구현

2. **Phase 1-2**: Tool 실행 + 에러 복구 [3시간]
   - LLM 기반 tool 실행
   - RetryStrategy 구현
   - CircuitBreaker 패턴

3. **Phase 3-4**: 병렬 실행 + 라우팅 [2.5시간]
   - ParallelExecutor 구현
   - 의존성 분석
   - Smart routing

4. **테스트 및 검증**: [1.5시간]
   - 통합 테스트
   - 성능 측정
   - 메모리 프로파일링

**총 예상 시간: 8시간**

## 🎯 성공 지표

### 필수 달성 목표
- ✅ 동시성 안전성 100%
- ✅ 부분 실패 시에도 서비스 지속
- ✅ WebSocket 메시지 순서 보장
- ✅ 메모리 사용량 증가 < 30%

### 성능 목표
- 📈 응답 시간 30-40% 단축 (병렬 실행)
- 📈 가용성 95% 이상 (에러 복구)
- 📈 Tool 실행 정확도 90% 이상

## ⚠️ 주의사항

1. **메모리 모니터링 필수**
   - 병렬 실행 시 메모리 사용량 추적
   - OOM 방지를 위한 제한 설정

2. **WebSocket 클라이언트 수정 필요**
   - 병렬 메시지 처리 로직 추가
   - 순서 재정렬 가능성 대비

3. **데이터베이스 부하 고려**
   - SQLite WAL 모드 필수
   - 필요시 Redis 전환 검토

4. **로깅 레벨 조정**
   - Production: INFO 레벨
   - 디버깅: DEBUG 레벨 (성능 영향 주의)

## 📁 파일 변경 요약

### 신규 파일 (5개)
- `backend/src/core/concurrency.py` - Thread 안전성
- `backend/src/core/streaming.py` - 스트리밍 조정
- `backend/src/core/retry_strategy.py` - 재시도 전략
- `backend/src/core/monitoring.py` - 성능 모니터링
- `backend/tests/test_parallel_execution.py` - 병렬 실행 테스트

### 수정 파일 (7개)
- `backend/src/agents/analytics.py` - LLM tool 실행
- `backend/src/agents/search.py` - LLM tool 실행
- `backend/src/agents/document.py` - LLM tool 실행
- `backend/src/agents/compliance.py` - LLM tool 실행
- `backend/src/agents/supervisor.py` - 병렬 계획 수립
- `backend/src/core/graph.py` - 병렬 실행, 스마트 라우팅
- `backend/src/api/app.py` - WebSocket 스트리밍 조정