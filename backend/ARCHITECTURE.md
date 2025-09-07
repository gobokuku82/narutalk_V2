# 🏗️ LangGraph 0.6.6 Architecture

## 📊 세부 작동 원리

### 1. Graph 실행 흐름
```
사용자 입력
    ↓
FastAPI (/api/graph/invoke)
    ↓
StateGraph.invoke()
    ↓
START → supervisor → [analytics/search/document/compliance] → supervisor → END
    ↓
응답 반환
```

### 2. State 업데이트 과정
```python
# 각 노드 실행 시
1. 노드 함수 호출: node(state)
2. 반환값 받기: updates = {"messages": [...], ...}
3. State 병합: state = merge(state, updates)
4. 다음 노드로 전달
```

### 3. Checkpointer 메커니즘
- 각 노드 실행 후 State 스냅샷 저장
- thread_id로 대화 세션 관리
- MemorySaver: 메모리 임시 저장
- SqliteSaver: 영구 저장

## 📁 파일 구조

### ✅ 핵심 파일 (필수)
```
backend/
├── main.py                    # 진입점 (run_enhanced.py 통합)
├── src/
│   ├── core/
│   │   └── graph.py          # StateGraph 정의
│   ├── agents/
│   │   ├── supervisor.py     # 라우팅 노드
│   │   ├── analytics.py      # 분석 노드
│   │   ├── search.py         # 검색 노드
│   │   ├── document.py       # 문서 노드
│   │   └── compliance.py     # 규정 노드
│   ├── state/
│   │   └── agent_state.py    # State 정의
│   ├── tools/
│   │   ├── database.py       # SQLite Mock DB
│   │   └── analytics_tools.py # 분석 도구
│   └── api/
│       ├── main.py           # FastAPI 앱 (enhanced_main.py 내용)
│       ├── routes.py         # API 라우트
│       └── mock_db.py        # Mock DB API
```

### 🔴 삭제 가능 (중복)
- `run_enhanced.py` → `main.py`로 통합
- `src/api/enhanced_main.py` → `src/api/main.py`로 이름 변경

## 🔄 실행 방법

```bash
# 개발 모드
python main.py

# 프로덕션 모드
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

## 🎯 API 엔드포인트

### Graph 실행
- `POST /api/graph/invoke` - StateGraph 실행
- `WS /ws/stream` - 실시간 스트리밍

### Mock DB
- `/api/db/mock/*` - Mock 데이터베이스 API

### 상태 확인
- `GET /health` - 헬스 체크
- `GET /metrics` - 메트릭스

## 💡 핵심 이해 포인트

1. **StateGraph가 중심**
   - 모든 노드는 State를 통해 통신
   - 각 노드는 독립적인 함수
   - Graph가 실행 순서 제어

2. **도구 분리**
   - agents/: 노드 로직
   - tools/: 재사용 가능한 도구
   - state/: 데이터 구조

3. **확장 방법**
   - 새 에이전트: agents/ 폴더에 추가
   - 새 도구: tools/ 폴더에 추가
   - graph.py에 노드 등록