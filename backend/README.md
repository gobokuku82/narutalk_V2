# Sales Support AI Backend - LangGraph 0.6.6

## 🏗️ 프로젝트 구조

```
backend/
├── main.py                   # 메인 진입점
├── src/
│   ├── api/
│   │   ├── app.py           # FastAPI 애플리케이션
│   │   ├── routes.py        # API 라우트
│   │   └── mock_db.py       # Mock DB API
│   ├── core/
│   │   └── graph.py         # LangGraph StateGraph 정의
│   ├── agents/              # 에이전트 노드들
│   │   ├── supervisor.py    # 라우팅 에이전트
│   │   ├── analytics.py     # 분석 에이전트
│   │   ├── search.py        # 검색 에이전트
│   │   ├── document.py      # 문서 생성 에이전트
│   │   └── compliance.py    # 규정 준수 에이전트
│   ├── state/
│   │   └── agent_state.py   # State 정의
│   └── tools/               # 도구 모듈
│       ├── database.py      # SQLite Mock DB
│       └── analytics_tools.py # 분석 도구
├── tests/                   # 테스트 파일
├── data/                    # SQLite 데이터베이스
└── logs/                    # 로그 파일
```

## 🚀 실행 방법

### 1. 환경 설정
```bash
# .env 파일 생성 (backend/.env)
cp .env.example .env
# OpenAI API 키 설정 필요
```

### 2. 패키지 설치
```bash
pip install -r requirements.txt
```

### 3. 서버 실행
```bash
# 개발 모드 (자동 리로드)
python main.py

# 또는 직접 uvicorn 실행
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
```

## 📡 API 엔드포인트

### 메인 엔드포인트
- `POST /api/graph/invoke` - LangGraph 실행
- `WS /ws/stream` - WebSocket 실시간 스트리밍

### Mock DB
- `GET /api/db/mock/customers` - 고객 조회
- `GET /api/db/mock/products` - 제품 조회
- `GET /api/db/mock/sales` - 판매 조회
- `POST /api/db/mock/analytics/generate` - 분석 생성

### 상태 확인
- `GET /` - 루트 (시스템 정보)
- `GET /health` - 헬스 체크
- `GET /metrics` - 메트릭스

## 🔧 LangGraph 0.6.6 특징

- **StateGraph 패턴**: 상태 기반 그래프 실행
- **START/END 노드**: 명시적 시작/종료 포인트
- **Checkpointer**: 대화 기록 저장 (MemorySaver/SqliteSaver)
- **Tool Integration**: @tool 데코레이터로 도구 통합

## 📊 에이전트 역할

1. **Supervisor**: 작업 라우팅 및 조정
2. **Analytics**: SQLite 데이터 분석, KPI 계산
3. **Search**: 정보 검색 및 수집
4. **Document**: 문서 및 보고서 생성
5. **Compliance**: 규정 준수 검증

## 🧪 테스트

```bash
# 전체 테스트 실행
pytest

# 특정 테스트 실행
pytest tests/test_analytics.py
pytest tests/test_supervisor.py
```

## 📝 환경 변수

```env
# API 설정
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true

# OpenAI
OPENAI_API_KEY=your-key-here

# LangGraph
USE_SQLITE_CHECKPOINTER=false

# Mock DB
MOCK_DB_ENABLED=true
```

## 🛠️ 개발 도구

- **LangGraph**: 0.6.6
- **FastAPI**: 비동기 웹 프레임워크
- **SQLite**: Mock 데이터베이스
- **Pandas**: 데이터 분석
- **Loguru**: 로깅

## 📚 문서

- [ARCHITECTURE.md](ARCHITECTURE.md) - 상세 아키텍처
- [rule.md](../rule.md) - LangGraph 0.6.6 규칙