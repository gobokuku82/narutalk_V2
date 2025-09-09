# 🔍 Narutalk Sales AI 시스템 분석 보고서

## 📅 작성일: 2025-09-09
## 🎯 목적: 시스템 구조 파악 및 개선 방향 제시

---

## 1. 🏗️ 시스템 아키텍처 개요

### 1.1 기술 스택
- **Backend**: Python 3.x, FastAPI, LangGraph 0.6.6, LangChain
- **Frontend**: React.js, WebSocket
- **Database**: SQLite (체크포인터), ChromaDB (벡터 저장소)
- **AI Model**: OpenAI GPT-4o-mini

### 1.2 시스템 구조
```
┌─────────────┐     WebSocket      ┌──────────────┐
│   Frontend  │ ◄──────────────────►│   Backend    │
│   (React)   │                     │  (FastAPI)   │
└─────────────┘                     └──────────────┘
                                            │
                                    ┌───────▼────────┐
                                    │   LangGraph    │
                                    │    0.6.6       │
                                    └────────────────┘
```

---

## 2. 📁 Backend 구조 분석

### 2.1 디렉토리 구조
```
backend/
├── main.py                 # 진입점
├── src/
│   ├── agents/            # 에이전트 모듈 (이중 구현 문제!)
│   │   ├── supervisor.py
│   │   ├── analytics.py
│   │   ├── search.py
│   │   ├── document.py
│   │   ├── compliance.py
│   │   ├── query_analyzer.py    # ⚠️ 새로 추가
│   │   ├── execution_planner.py # ⚠️ 새로 추가
│   │   └── dynamic_router.py    # ⚠️ 새로 추가
│   ├── api/
│   │   └── app.py         # FastAPI 앱
│   ├── core/
│   │   └── graph.py       # 기본 그래프 구현
│   ├── graph/
│   │   └── enhanced_graph.py  # ⚠️ 고도화된 그래프 (중복!)
│   ├── state/
│   │   ├── agent_state.py     # 기본 상태
│   │   └── enhanced_state.py  # ⚠️ 고도화된 상태 (중복!)
│   └── tools/             # 도구 모듈
```

### 2.2 핵심 문제점

#### 🔴 **문제 1: 그래프 구현 이중화**
- `core/graph.py`: 기본 supervisor 기반 그래프
- `graph/enhanced_graph.py`: query_analyzer 기반 고도화 그래프
- **현재 app.py는 기본 그래프만 사용 중!**

#### 🔴 **문제 2: Import 오류**
```python
# enhanced_graph.py의 잘못된 import
from ..agents.analytics_agent import analytics_agent  # ❌ 파일명 오류
from ..agents.search_agent import search_agent        # ❌ 파일명 오류
from ..agents.document_agent import document_agent    # ❌ 파일명 오류
from ..agents.compliance_agent import compliance_agent # ❌ 파일명 오류

# 실제 파일명
from ..agents.analytics import analytics_agent   # ✅
from ..agents.search import search_agent        # ✅
from ..agents.document import document_agent    # ✅
from ..agents.compliance import compliance_agent # ✅
```

#### 🔴 **문제 3: 상태 관리 혼재**
- `AgentState`: 기본 상태
- `EnhancedAgentState`: 고도화된 상태
- 두 상태가 호환되지 않음

#### 🔴 **문제 4: WebSocket 메시지 포맷 불일치**
- Backend: `node_output`, `progress` 타입 전송
- Frontend: `agent_update`, `execution_plan` 타입 기대
- 메시지 변환 로직이 불완전

---

## 3. 💻 Frontend 구조 분석

### 3.1 디렉토리 구조
```
frontend/
├── src/
│   ├── components/
│   │   ├── ChatBot.jsx      # 메인 컴포넌트
│   │   ├── ChatHeader.jsx   # 헤더
│   │   ├── MessageList.jsx  # 메시지 목록
│   │   ├── MessageItem.jsx  # 메시지 아이템
│   │   ├── ChatInput.jsx    # 입력창
│   │   └── ProgressBar.jsx  # 진행 표시
│   ├── services/
│   │   └── websocket.js     # WebSocket 통신
│   └── styles/
│       └── ChatBot.css      # 스타일
```

### 3.2 핵심 문제점

#### 🟡 **문제 1: 복잡한 상태 관리**
- 9개의 useState 훅 사용
- isPlanning, executionPhase 등 중복된 상태

#### 🟡 **문제 2: WebSocket 메시지 처리**
- 메시지 타입 변환이 websocket.js에 하드코딩
- Backend 메시지 포맷과 불일치

#### 🟡 **문제 3: 스피너 로직**
- 계획/실행 단계 구분이 명확하지 않음
- agent 이름 기반으로만 판단

---

## 4. 🚨 주요 문제점 진단

### 4.1 시스템 통합 문제
| 문제 | 심각도 | 설명 |
|------|--------|------|
| 그래프 이중 구현 | 🔴 높음 | 기본/고도화 그래프가 별도로 존재하나 연결 안됨 |
| Import 오류 | 🔴 높음 | enhanced_graph.py가 잘못된 파일명 참조 |
| 메시지 포맷 불일치 | 🟡 중간 | Frontend-Backend 간 메시지 규격 불일치 |
| 상태 호환성 | 🟡 중간 | AgentState와 EnhancedAgentState 비호환 |

### 4.2 기능 작동 상태
| 기능 | 상태 | 비고 |
|------|------|------|
| 기본 supervisor 라우팅 | ✅ 작동 | core/graph.py 사용 시 |
| Query Analyzer | ❌ 미작동 | enhanced_graph.py 미연결 |
| Execution Planner | ❌ 미작동 | enhanced_graph.py 미연결 |
| Dynamic Router | ❌ 미작동 | enhanced_graph.py 미연결 |
| WebSocket 통신 | ⚠️ 부분작동 | 메시지 변환 필요 |

---

## 5. 🛠️ 개선 방향 제안

### 5.1 즉시 수정 필요 (Priority 1)

#### 1️⃣ **Import 오류 수정**
```python
# backend/src/graph/enhanced_graph.py 수정
# Line 20-23
from ..agents.analytics import analytics_agent     # _agent 제거
from ..agents.search import search_agent          # _agent 제거
from ..agents.document import document_agent      # _agent 제거
from ..agents.compliance import compliance_agent  # _agent 제거
```

#### 2️⃣ **그래프 통합 또는 선택**
```python
# backend/src/api/app.py 수정
# Option A: Enhanced Graph 사용
from ..graph.enhanced_graph import create_enhanced_graph
sales_app = create_enhanced_graph()

# Option B: 기본 그래프 유지
# 현재 상태 유지하되 enhanced 기능 제거
```

#### 3️⃣ **WebSocket 메시지 표준화**
```python
# 표준 메시지 포맷 정의
MESSAGE_TYPES = {
    "PLANNING": "planning",       # 계획 수립 중
    "EXECUTING": "executing",     # 실행 중
    "AGENT_UPDATE": "agent_update",
    "COMPLETE": "complete",
    "ERROR": "error"
}
```

### 5.2 단계별 개선 계획

#### **Phase 1: 안정화 (1-2일)**
1. Import 오류 수정
2. 기본 그래프로 통합 (enhanced 제거 또는 수정)
3. WebSocket 메시지 포맷 통일

#### **Phase 2: 기능 복원 (3-4일)**
1. Query Analyzer 통합 결정
   - 필요하면 기본 그래프에 추가
   - 불필요하면 완전 제거
2. 상태 관리 단순화
3. Frontend 상태 최적화

#### **Phase 3: 최적화 (5-7일)**
1. 테스트 코드 작성
2. 에러 핸들링 강화
3. 로깅 시스템 개선

### 5.3 아키텍처 개선안

#### Option A: 단순화 접근
```
User → Supervisor → Agent → Response
(기존 supervisor 방식 유지, enhanced 제거)
```

#### Option B: 고도화 접근
```
User → Query Analyzer → Planner → Router → Agents → Response
(enhanced 방식 수정 및 적용)
```

**권장: Option A로 먼저 안정화 후, 필요시 Option B 점진적 도입**

---

## 6. 📋 Action Items

### 즉시 수행
- [ ] enhanced_graph.py의 import 오류 수정
- [ ] app.py에서 사용할 그래프 결정
- [ ] WebSocket 메시지 포맷 문서화

### 단기 (1주일 내)
- [ ] 불필요한 코드 제거
- [ ] 상태 관리 통합
- [ ] 기본 테스트 작성

### 중기 (2주일 내)
- [ ] 전체 시스템 테스트
- [ ] 성능 최적화
- [ ] 문서화 완성

---

## 7. 🎯 결론

현재 시스템은 **기본 기능은 작동하나 고도화 기능이 연결되지 않은 상태**입니다.

### 핵심 권장사항:
1. **먼저 안정화**: Import 오류 수정, 기본 그래프로 통합
2. **점진적 개선**: 안정화 후 필요한 고도화 기능만 선택적 도입
3. **테스트 우선**: 각 수정 단계마다 테스트 코드 작성

### 예상 소요 시간:
- 긴급 수정: 1-2일
- 전체 안정화: 1주일
- 완전한 개선: 2-3주일

---

*이 보고서는 현재 코드베이스 분석을 기반으로 작성되었습니다.*
*추가 분석이 필요한 부분이 있으면 말씀해 주세요.*