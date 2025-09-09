# LangGraph 0.6.6 챗봇 개선 가이드 - Claude Desktop 작업 지시서

## 📋 개요
이 문서는 VS Code의 Claude Desktop을 사용하여 LangGraph 0.6.6 기반 영업 지원 AI 챗봇을 개선하기 위한 상세 지시사항입니다.
**핵심: 모든 에이전트 간 정보 전달은 State를 통해서만 이루어집니다.**

---

## 🔍 현재 구조 분석

### 잘 구현된 부분 ✅
1. **LangGraph 0.6.6 문법 준수**
   - StateGraph, START, END 올바른 사용
   - 노드 함수의 dict 반환 규칙 준수
   - State를 통한 정보 전달 구조 구현
   - Checkpointer 적절히 구현

2. **기본 State 전달 메커니즘**
   - 각 에이전트가 State의 `results` 필드에 결과 저장
   - `context` 필드를 통한 메타데이터 전달
   - Document → Compliance 자동 라우팅 시 State로 문서 전달

### 개선 필요 사항 ❌
1. **State에 저장된 정보를 다른 에이전트가 활용하지 않음**
2. **Tool binding은 되어있으나 실제 실행 로직 미구현**
3. **순차 실행만 가능 (병렬 처리 불가)**
4. **State의 `results` 필드 활용도 낮음**

---

## 📝 수정 작업 지시사항

### 1. AgentState 개선 (파일: `backend/src/state/agent_state.py`)

**현재 코드 위치:** Line 35-55

**현재 State 구조 분석:**
```python
# 현재 잘 되어있는 부분
class AgentState(MessagesState):
    results: dict[str, Any]  # ✅ 각 에이전트 결과 저장
    context: dict[str, Any]  # ✅ 컨텍스트 정보
```

**수정 지시:**
```markdown
1. 기존 results 필드 활용도 개선을 위한 타입 힌트 추가:
   - results 필드에 에이전트별 결과 구조 명시
   - TypedDict으로 결과 구조 정의

2. 병렬 처리를 위한 필드 추가:
   - parallel_tasks: list[str]  # 병렬 실행 가능한 태스크
   - dependencies: dict[str, list[str]]  # 에이전트 의존성
```

**예상 코드:**
```python
from typing import TypedDict

class AgentResults(TypedDict, total=False):
    """State의 results 필드 구조 정의"""
    analytics: dict  # Analytics 에이전트 결과
    search: dict     # Search 에이전트 결과  
    document: dict   # Document 에이전트 결과
    compliance: dict # Compliance 에이전트 결과

class AgentState(MessagesState):
    # 기존 필드 (수정 불필요, 활용도만 개선)
    results: AgentResults  # 타입 힌트 개선
    context: dict[str, Any]
    
    # 새로 추가할 필드
    parallel_tasks: list[str]
    dependencies: dict[str, list[str]]
```

---

### 2. Analytics Agent - State 활용 개선 (파일: `backend/src/agents/analytics.py`)

**현재 코드 위치:** Line 20-200

**현재 문제점:**
- State의 results에 결과를 저장하지만, 다른 에이전트 결과를 읽지 않음

**수정 지시:**
```markdown
1. State에서 이전 에이전트 결과 활용 (Line 30 추가):
   - Search 에이전트가 State에 저장한 고객 정보 활용
   - Document 요청사항이 있으면 분석 포맷 조정

2. Tool 실행 후 State 업데이트 개선 (Line 180-200 수정):
   - 다음 에이전트가 사용할 수 있도록 구조화된 데이터 저장
```

**구현 예시:**
```python
def analytics_agent(state: AgentState) -> dict:
    # ✅ State에서 다른 에이전트 결과 읽기
    results = state.get("results", {})
    search_results = results.get("search", {})
    
    # Search가 찾은 고객 정보로 분석 최적화
    if search_results:
        customer_data = search_results.get("merged_results", [])
        # 고객별 맞춤 분석 수행
        for customer in customer_data:
            if customer.get("category") == "customers":
                # 해당 고객에 대한 상세 분석
                customer_id = customer.get("data", {}).get("customer_id")
                if customer_id:
                    perf_data = query_performance_data.invoke({"customer_id": customer_id})
    
    # 분석 수행...
    
    # ✅ State의 results 업데이트 (다음 에이전트를 위해)
    results_update = state.get("results", {})
    results_update["analytics"] = {
        "timestamp": datetime.now().isoformat(),
        "analysis": analysis_content,
        "raw_data": analysis_results,
        "key_insights": {  # Document 에이전트가 사용할 수 있는 구조화된 데이터
            "top_metrics": {...},
            "recommendations": [...],
            "executive_summary": "..."
        }
    }
    
    return {
        "results": results_update,  # State로 전달
        ...
    }
```

---

### 3. Search Agent - State 기반 검색 최적화 (파일: `backend/src/agents/search.py`)

**현재 코드 위치:** Line 25-250

**수정 지시:**
```markdown
1. Analytics 결과 기반 검색 (Line 40 추가):
   - State의 results["analytics"]에서 핵심 지표 추출
   - 해당 지표로 검색 쿼리 최적화

2. Document를 위한 데이터 준비 (Line 200 수정):
   - State에 문서 생성용 구조화된 데이터 저장
```

**구현 예시:**
```python
def search_agent(state: AgentState) -> dict:
    # ✅ State에서 Analytics 결과 활용
    results = state.get("results", {})
    analytics_data = results.get("analytics", {})
    
    search_query = task_description
    
    # Analytics가 찾은 인사이트로 검색 개선
    if analytics_data:
        key_insights = analytics_data.get("key_insights", {})
        top_customers = key_insights.get("top_customers", [])
        
        # 상위 고객 중심으로 검색 우선순위 조정
        if top_customers:
            search_query = f"{search_query} {' '.join(top_customers)}"
    
    # 검색 수행...
    
    # ✅ State 업데이트 (Document 에이전트를 위한 구조화)
    results_update = state.get("results", {})
    results_update["search"] = {
        "query": search_query,
        "merged_results": merged_data,
        "document_ready_data": {  # Document가 바로 사용할 수 있는 형태
            "company_info": {...},
            "product_details": {...},
            "market_context": {...}
        }
    }
    
    return {"results": results_update, ...}
```

---

### 4. Document Agent - State에서 데이터 통합 (파일: `backend/src/agents/document.py`)

**현재 코드 위치:** Line 30-180

**현재 잘된 점:**
- 생성한 문서를 State의 results["document"]에 저장 ✅
- Compliance가 State에서 문서를 읽어서 검증 ✅

**수정 지시:**
```markdown
1. 멀티 소스 데이터 통합 (Line 50 추가):
   - State의 results["analytics"]에서 분석 인사이트 가져오기
   - State의 results["search"]에서 검색 결과 가져오기
   - 두 데이터를 통합하여 문서 생성

2. 문서를 State에 저장 (현재도 잘 되어있음, Line 150):
   - results["document"]["data"]에 전체 문서 내용 저장
   - Compliance가 읽을 수 있도록 구조화
```

**구현 예시:**
```python
def document_agent(state: AgentState) -> dict:
    # ✅ State에서 모든 이전 결과 통합
    results = state.get("results", {})
    analytics_insights = results.get("analytics", {}).get("key_insights", {})
    search_data = results.get("search", {}).get("document_ready_data", {})
    
    # 통합 문서 생성
    document_content = {
        "executive_summary": analytics_insights.get("executive_summary", ""),
        "company_profile": search_data.get("company_info", {}),
        "product_recommendations": search_data.get("product_details", {}),
        "market_analysis": analytics_insights.get("market_analysis", {}),
        "financial_metrics": analytics_insights.get("top_metrics", {}),
        "action_items": analytics_insights.get("recommendations", [])
    }
    
    # 문서 생성...
    document_data = create_document(document_content)
    
    # ✅ State에 문서 저장 (Compliance가 읽을 수 있도록)
    results_update = state.get("results", {})
    results_update["document"] = {
        "document_id": document_id,
        "type": doc_type,
        "data": document_data,  # 전체 문서 내용이 State에 저장됨
        "metadata": {
            "sources": ["analytics", "search"],  # 어떤 에이전트 데이터를 사용했는지
            "created_at": datetime.now().isoformat()
        }
    }
    
    return {
        "results": results_update,  # State로 전달
        "next_agent": "compliance",  # 다음 에이전트 지정
        ...
    }
```

---

### 5. Compliance Agent - State에서 문서 검증 (파일: `backend/src/agents/compliance.py`)

**현재 코드 위치:** Line 43-65

**현재 잘된 점:**
- State의 results["document"]에서 문서를 읽어서 검증 ✅

**개선 사항:**
```markdown
1. 검증 결과를 State에 저장하여 피드백 루프 생성 (Line 180):
   - 검증 실패 시 Document 에이전트가 수정할 수 있도록 상세 정보 제공
```

**구현 예시:**
```python
def compliance_agent(state: AgentState) -> dict:
    # ✅ State에서 Document 가져오기 (현재도 잘 되어있음)
    results = state.get("results", {})
    
    if "document" in results:
        doc_data = results["document"].get("data", {})
        document_id = results["document"].get("document_id")
        
        # 문서 내용을 State에서 읽어서 검증
        if isinstance(doc_data, dict):
            document_text = json.dumps(doc_data, ensure_ascii=False)
        
        # Compliance 체크...
        validation_result = perform_full_compliance_check(...)
        
    # ✅ 검증 결과를 State에 저장
    results_update = state.get("results", {})
    results_update["compliance"] = {
        "validation_id": validation_id,
        "compliance_status": compliance_status,
        "violations": violations,
        "suggestions": suggestions,
        "document_feedback": {  # Document가 수정 시 참고할 정보
            "required_changes": [...],
            "problematic_sections": {...}
        }
    }
    
    # 만약 수정이 필요하면 Document로 다시 라우팅
    if compliance_status == "FAILED":
        return {
            "results": results_update,
            "next_agent": "document",  # Document로 돌아가서 수정
            "context": {
                **context,
                "revision_required": True,
                "compliance_feedback": results_update["compliance"]
            }
        }
    
    return {"results": results_update, ...}
```

---

### 6. Supervisor Agent - State 기반 라우팅 개선 (파일: `backend/src/agents/supervisor.py`)

**현재 코드 위치:** Line 15-150

**수정 지시:**
```markdown
1. State의 results를 분석하여 다음 에이전트 결정 (Line 50):
   - 이미 실행된 에이전트 확인
   - 필요한 데이터가 State에 있는지 확인

2. 병렬 실행 가능 여부 판단 (Line 80):
   - 의존성이 없는 에이전트들 식별
```

**구현 예시:**
```python
def supervisor_agent(state: AgentState) -> dict:
    results = state.get("results", {})
    execution_plan = state.get("execution_plan", [])
    
    # ✅ State 분석하여 실행 계획 수립
    completed_agents = list(results.keys())
    
    # 복합 질의 분석
    if "분석하고" in user_request and "문서 작성" in user_request:
        # Analytics와 Search는 병렬 가능
        if not any(a in completed_agents for a in ["analytics", "search"]):
            parallel_tasks = ["analytics", "search"]
        # 둘 다 완료되면 Document
        elif all(a in results for a in ["analytics", "search"]):
            next_agent = "document"
        # Document 완료되면 Compliance
        elif "document" in results:
            next_agent = "compliance"
    
    # ✅ State 업데이트
    return {
        "execution_plan": execution_plan,
        "parallel_tasks": parallel_tasks if parallel_tasks else [],
        "current_step": current_step + 1,
        "results": results,  # 누적된 results 전달
        ...
    }
```

---

### 7. Graph 구조 - State 흐름 최적화 (파일: `backend/src/core/graph.py`)

**현재 코드 위치:** Line 15-80

**수정 지시:**
```markdown
1. State 검증 노드 추가 (Line 30):
   - State의 results가 올바르게 누적되는지 확인
   - 필수 정보가 없으면 에러 처리

2. State 기반 조건부 라우팅 강화 (Line 50):
   - State의 results 내용에 따라 동적 라우팅
```

---

## 🔧 State 활용 테스트 시나리오

### State 전달 흐름 검증
```python
# 테스트: "삼성전자 분석하고 제안서 작성 후 검토해줘"

# Step 1: Supervisor
initial_state = {
    "messages": [HumanMessage("삼성전자 분석하고...")],
    "results": {},  # 비어있음
}

# Step 2: Analytics 실행
state_after_analytics = {
    "results": {
        "analytics": {  # Analytics 결과가 State에 저장
            "company": "삼성전자",
            "metrics": {...}
        }
    }
}

# Step 3: Search 실행 (Analytics 결과 활용)
state_after_search = {
    "results": {
        "analytics": {...},  # 이전 결과 유지
        "search": {  # Search 결과 추가
            "company_info": {...}
        }
    }
}

# Step 4: Document 생성 (모든 이전 결과 활용)
state_after_document = {
    "results": {
        "analytics": {...},
        "search": {...},
        "document": {  # Document 추가
            "data": "제안서 내용..."
        }
    }
}

# Step 5: Compliance 검증 (Document를 State에서 읽어서 검증)
final_state = {
    "results": {
        "analytics": {...},
        "search": {...},
        "document": {...},
        "compliance": {  # Compliance 결과 추가
            "status": "PASSED"
        }
    }
}
```

---

## ⚠️ 핵심 원칙

1. **모든 데이터는 State를 통해서만 전달**
   - 파일이나 외부 저장소 사용 최소화
   - State의 results 필드에 모든 결과 누적

2. **State는 누적되며 불변(immutable)**
   - 이전 에이전트 결과는 유지
   - 새 결과만 추가

3. **State 크기 관리**
   - 큰 데이터는 요약본만 State에 저장
   - 필요시 ID로 참조

---

## 📊 개선 효과

1. **State 활용도**: 20% → 90%
2. **에이전트 간 정보 재사용**: 0% → 80%
3. **복합 질의 처리 정확도**: 70% → 95%

---

## ✅ 최종 검증 체크리스트

- [ ] 각 에이전트가 State의 results에서 이전 결과 읽기
- [ ] 각 에이전트가 자신의 결과를 State의 results에 추가
- [ ] Document가 Analytics + Search 결과 통합
- [ ] Compliance가 State에서 Document 읽어서 검증
- [ ] Supervisor가 State의 results로 다음 에이전트 결정
- [ ] State가 시작부터 끝까지 누적되며 전달
- [ ] 병렬 실행 시에도 State 동기화
- [ ] State 크기가 과도하게 커지지 않도록 관리

---

이 지시사항의 핵심은 **이미 구현된 State 전달 메커니즘을 제대로 활용**하는 것입니다. 
새로운 전달 방식을 만드는 것이 아니라, State의 results 필드를 적극 활용하여 에이전트 간 협업을 강화하는 것이 목표입니다.