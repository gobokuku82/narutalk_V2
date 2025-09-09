# 🎯 질의 분석 & 계획 수립 체계 고도화 계획서

## 1. 현재 상태 분석

### 현재 구현 (supervisor.py)
- **단순 키워드 매칭**: "분석", "search", "document" 등 단순 텍스트 포함 여부로 라우팅
- **고정된 실행 순서**: 정해진 에이전트 순서대로만 실행
- **컨텍스트 부족**: 이전 대화나 사용자 의도 고려 없음
- **계획 수정 불가**: 한번 결정된 실행 계획 변경 불가능

### 문제점
1. **낮은 정확도**: 복잡한 질의 처리 실패 (예: "지난달 실적 분석하고 경쟁사와 비교해서 보고서 만들어줘")
2. **비효율적 실행**: 불필요한 에이전트 호출
3. **오류 전파**: 잘못된 라우팅이 끝까지 영향

## 2. 고도화 아키텍처

### 2.1 새로운 노드 구조
```
[START]
   ↓
[Query Preprocessor] - 전처리 & 정규화
   ↓
[Intent Classifier] - 의도 분류 (Multi-label)
   ↓
[Entity Extractor] - 엔티티 추출
   ↓
[Context Analyzer] - 컨텍스트 분석
   ↓
[Execution Planner] - 실행 계획 생성
   ↓
[Plan Validator] - 계획 검증
   ↓
[Dynamic Router] - 동적 라우팅
   ↓
[Agent Execution]
```

### 2.2 Intent Classification 체계

#### Primary Intents (주요 의도)
- `ANALYZE`: 데이터 분석, 통계, 트렌드
- `SEARCH`: 정보 검색, 조회
- `GENERATE`: 문서 생성, 보고서 작성
- `VALIDATE`: 규정 검토, 컴플라이언스
- `COMPARE`: 비교 분석
- `PREDICT`: 예측, 전망

#### Secondary Intents (보조 의도)
- `URGENT`: 긴급 처리 필요
- `DETAILED`: 상세 분석 요구
- `SUMMARY`: 요약 필요
- `VISUAL`: 시각화 요구

### 2.3 Entity Extraction 체계

#### Entity Types
```python
entities = {
    "temporal": ["지난달", "이번주", "Q3", "2024년"],
    "target": ["고객사", "경쟁사", "제품A"],
    "metric": ["매출", "성장률", "만족도"],
    "action": ["비교", "예측", "분석"],
    "format": ["보고서", "프레젠테이션", "요약"]
}
```

## 3. 구현 상세

### 3.1 Query Preprocessor
```python
def preprocess_query(state: AgentState) -> dict:
    """
    - 오타 교정
    - 축약어 확장 (Q3 → 3분기)
    - 동의어 통합
    - 문장 분할
    """
```

### 3.2 Intent Classifier with LLM
```python
def classify_intent(state: AgentState) -> dict:
    """
    GPT-4를 사용한 Multi-label Classification
    
    프롬프트:
    1. 주요 의도 식별
    2. 보조 의도 태깅
    3. 신뢰도 점수 (0-1)
    4. 모호성 플래그
    """
```

### 3.3 Execution Planner
```python
def create_execution_plan(state: AgentState) -> dict:
    """
    동적 실행 계획 생성
    
    1. 의존성 그래프 구성
    2. 병렬 실행 가능 작업 식별
    3. 우선순위 설정
    4. 예상 실행 시간 계산
    
    반환: {
        "sequential_tasks": [...],
        "parallel_tasks": [...],
        "conditional_tasks": [...],
        "estimated_time": 10
    }
    """
```

### 3.4 Plan Validator
```python
def validate_plan(state: AgentState) -> dict:
    """
    계획 타당성 검증
    
    체크리스트:
    - 순환 의존성 확인
    - 리소스 충돌 검사
    - 실행 가능성 평가
    - 대안 계획 생성
    """
```

## 4. State 확장

```python
class EnhancedAgentState(MessagesState):
    # 질의 분석
    raw_query: str
    normalized_query: str
    query_language: str  # ko, en
    
    # 의도 분류
    primary_intent: str
    secondary_intents: List[str]
    intent_confidence: float
    
    # 엔티티
    entities: Dict[str, List[str]]
    entity_relations: List[Tuple]
    
    # 실행 계획
    execution_plan: Dict[str, Any]
    plan_version: int
    plan_status: str  # planning, executing, completed
    
    # 동적 라우팅
    next_agents: List[str]
    parallel_agents: List[str]
    conditional_branches: Dict[str, str]
```

## 5. 구현 단계

### Phase 1: 기본 분류기 (1주)
- Intent Classifier 구현
- 기본 Entity Extractor
- 단순 규칙 기반 Planner

### Phase 2: LLM 통합 (1주)
- GPT-4 기반 분류기
- 컨텍스트 인식 계획
- 신뢰도 측정

### Phase 3: 동적 계획 (2주)
- 병렬 실행 지원
- 조건부 분기
- 계획 수정 메커니즘

## 6. 성공 지표

### 정량 지표
- 의도 분류 정확도: > 95%
- 엔티티 추출 F1 Score: > 0.9
- 계획 성공률: > 90%
- 평균 처리 시간: 20% 감소

### 정성 지표
- 복잡한 다중 작업 처리 가능
- 모호한 질의 명확화
- 사용자 피드백 반영

## 7. 예상 결과

### Before
```
"지난달 매출 분석해줘" 
→ analytics_agent만 실행
```

### After
```
"지난달 매출 분석해줘"
→ Intent: ANALYZE
→ Entities: {temporal: "지난달", metric: "매출"}
→ Plan: 
   1. search_agent (경쟁사 데이터)
   2. analytics_agent (내부 데이터)
   3. document_agent (보고서 생성)
→ 병렬 실행: search + analytics
→ 결과 통합 후 문서 생성
```

## 8. 리스크 및 대응

### 리스크 1: LLM 지연
- 대응: 캐싱, 경량 모델 폴백

### 리스크 2: 과도한 복잡성
- 대응: 점진적 롤아웃, A/B 테스트

### 리스크 3: 잘못된 분류
- 대응: Human-in-the-loop 검증

## 9. 필요 리소스

### 기술 스택
- LangChain 0.6.6
- GPT-4 API
- Redis (캐싱)
- Prometheus (모니터링)

### 개발 리소스
- 시니어 개발자 1명 (4주)
- 주니어 개발자 1명 (보조)
- QA 엔지니어 (2주)

## 10. 검증 계획

### 단위 테스트
- 각 분류기별 테스트 케이스 100개
- 엣지 케이스 처리

### 통합 테스트
- End-to-end 시나리오 50개
- 성능 벤치마크

### 사용자 테스트
- 베타 사용자 10명
- 2주간 실사용 피드백