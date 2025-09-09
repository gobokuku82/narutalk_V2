"""
Enhanced Agent State for Advanced Query Analysis
LangGraph 0.6.6 compatible state with query analysis capabilities
"""
from typing import Annotated, List, Dict, Any, Optional, Tuple
from langgraph.graph.message import MessagesState, add_messages
from langchain_core.messages import BaseMessage
from enum import Enum
from datetime import datetime


class IntentType(str, Enum):
    """Primary intent types for query classification"""
    ANALYZE = "analyze"
    SEARCH = "search"
    GENERATE = "generate"
    VALIDATE = "validate"
    COMPARE = "compare"
    PREDICT = "predict"
    RECOMMEND = "recommend"
    SUMMARIZE = "summarize"


class SecondaryIntent(str, Enum):
    """Secondary intent modifiers"""
    URGENT = "urgent"
    DETAILED = "detailed"
    SUMMARY = "summary"
    VISUAL = "visual"
    HISTORICAL = "historical"
    COMPARATIVE = "comparative"


class EntityType(str, Enum):
    """Entity types for extraction"""
    TEMPORAL = "temporal"  # 시간 관련
    TARGET = "target"      # 대상 (고객사, 제품 등)
    METRIC = "metric"      # 지표 (매출, 성장률 등)
    ACTION = "action"      # 액션 (비교, 예측, 분석)
    FORMAT = "format"      # 포맷 (보고서, 프레젠테이션 등)
    LOCATION = "location"  # 위치 정보
    PERSON = "person"      # 사람 이름
    QUANTITY = "quantity"  # 수량


def add_progress(existing: list[dict], new: list[dict]) -> list[dict]:
    """Reducer function to accumulate progress logs"""
    if not existing:
        existing = []
    if not new:
        return existing
    return existing + new


def merge_entities(existing: Dict[str, List[str]], new: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Reducer function to merge entity dictionaries"""
    if not existing:
        return new
    if not new:
        return existing
    
    merged = existing.copy()
    for key, values in new.items():
        if key in merged:
            # Avoid duplicates while preserving order
            for value in values:
                if value not in merged[key]:
                    merged[key].append(value)
        else:
            merged[key] = values.copy()
    return merged


class QueryAnalysis(dict):
    """Query analysis results structure"""
    raw_query: str
    normalized_query: str
    query_language: str  # ko, en, etc.
    primary_intent: IntentType
    secondary_intents: List[SecondaryIntent]
    intent_confidence: float
    entities: Dict[EntityType, List[str]]
    entity_relations: List[Tuple[str, str, str]]  # (entity1, relation, entity2)
    query_complexity: str  # simple, moderate, complex
    estimated_steps: int
    ambiguity_score: float  # 0-1, higher means more ambiguous
    clarification_needed: bool
    suggested_clarifications: List[str]


class ExecutionPlan(dict):
    """Execution plan structure"""
    sequential_tasks: List[str]  # Tasks to run in sequence
    parallel_tasks: List[List[str]]  # Groups of tasks to run in parallel
    conditional_tasks: Dict[str, Dict[str, Any]]  # Conditional execution branches
    estimated_time: float  # Estimated time in seconds
    priority_level: str  # low, medium, high, critical
    dependencies: Dict[str, List[str]]  # Task dependencies
    fallback_plans: Dict[str, List[str]]  # Fallback options for each task
    optimization_hints: List[str]  # Suggestions for optimization


class AgentResults(dict):
    """Enhanced results structure for agent outputs"""
    analytics: Optional[Dict[str, Any]]
    search: Optional[Dict[str, Any]]
    document: Optional[Dict[str, Any]]
    compliance: Optional[Dict[str, Any]]
    query_analysis: Optional[QueryAnalysis]
    execution_metrics: Optional[Dict[str, Any]]


class EnhancedAgentState(MessagesState):
    """
    Enhanced State for Advanced Query Analysis System
    Extends MessagesState with sophisticated query analysis capabilities
    """
    
    # === Core Agent Management ===
    current_agent: str
    task_type: str
    task_description: str
    
    # === Query Analysis Results ===
    query_analysis: Optional[QueryAnalysis]
    raw_query: str
    normalized_query: str
    query_language: str  # ko, en, etc.
    
    # === Intent Classification ===
    primary_intent: Optional[IntentType]
    secondary_intents: List[SecondaryIntent]
    intent_confidence: float
    intent_history: List[Dict[str, Any]]  # Track intent changes over conversation
    
    # === Entity Extraction ===
    entities: Annotated[Dict[str, List[str]], merge_entities]
    entity_relations: List[Tuple[str, str, str]]
    entity_confidence_scores: Dict[str, float]
    
    # === Execution Planning ===
    execution_plan: Optional[ExecutionPlan]
    plan_version: int
    plan_status: str  # planning, executing, completed, failed
    original_plan: Optional[ExecutionPlan]  # Keep original for comparison
    plan_modifications: List[Dict[str, Any]]  # Track plan changes
    
    # === Dynamic Routing ===
    next_agents: List[str]  # Ordered list of next agents
    parallel_agents: List[str]  # Agents to run in parallel
    conditional_branches: Dict[str, str]  # Condition -> agent mapping
    routing_history: List[Dict[str, Any]]  # Track routing decisions
    
    # === Context & Memory ===
    context: Dict[str, Any]
    conversation_context: List[Dict[str, Any]]  # Recent conversation history
    domain_context: Dict[str, Any]  # Domain-specific context
    user_preferences: Dict[str, Any]  # Learned user preferences
    
    # === Progress Tracking ===
    progress: Annotated[List[Dict], add_progress]
    completion_percentage: float
    estimated_remaining_time: float
    bottlenecks: List[str]  # Identified bottlenecks
    
    # === Results & Outputs ===
    results: AgentResults
    intermediate_results: Dict[str, Any]  # Store intermediate processing results
    cached_results: Dict[str, Any]  # Cache for reusable results
    
    # === Error Handling ===
    errors: List[str]
    error_recovery_attempts: int
    max_recovery_attempts: int
    fallback_triggered: bool
    
    # === Performance Metrics ===
    query_processing_time: float
    total_execution_time: float
    agent_execution_times: Dict[str, float]
    llm_call_count: int
    llm_token_usage: Dict[str, int]  # prompt_tokens, completion_tokens, total_tokens
    
    # === Control Flags ===
    is_complete: bool
    requires_human_input: bool
    auto_mode: bool  # Enable automatic decision making
    debug_mode: bool  # Enable detailed logging
    
    # === Optimization Hints ===
    suggested_optimizations: List[str]
    parallel_execution_possible: bool
    cacheable_operations: List[str]
    
    # === Metadata ===
    session_id: str
    user_id: Optional[str]
    timestamp: str
    version: str  # State schema version
    metadata: Dict[str, Any]


class QueryComplexity(str, Enum):
    """Query complexity levels"""
    SIMPLE = "simple"      # Single agent, straightforward
    MODERATE = "moderate"  # 2-3 agents, some coordination
    COMPLEX = "complex"    # Multiple agents, complex coordination
    ADVANCED = "advanced"  # Parallel execution, conditional logic


class ConfidenceLevel(str, Enum):
    """Confidence levels for classifications"""
    VERY_LOW = "very_low"    # < 0.2
    LOW = "low"              # 0.2 - 0.4
    MEDIUM = "medium"        # 0.4 - 0.6
    HIGH = "high"            # 0.6 - 0.8
    VERY_HIGH = "very_high"  # > 0.8


def calculate_confidence_level(score: float) -> ConfidenceLevel:
    """Convert numeric confidence score to level"""
    if score < 0.2:
        return ConfidenceLevel.VERY_LOW
    elif score < 0.4:
        return ConfidenceLevel.LOW
    elif score < 0.6:
        return ConfidenceLevel.MEDIUM
    elif score < 0.8:
        return ConfidenceLevel.HIGH
    else:
        return ConfidenceLevel.VERY_HIGH


def create_initial_state() -> Dict[str, Any]:
    """Create initial enhanced state with default values"""
    return {
        "messages": [],
        "current_agent": "supervisor",
        "task_type": "",
        "task_description": "",
        "query_analysis": None,
        "raw_query": "",
        "normalized_query": "",
        "query_language": "ko",
        "primary_intent": None,
        "secondary_intents": [],
        "intent_confidence": 0.0,
        "intent_history": [],
        "entities": {},
        "entity_relations": [],
        "entity_confidence_scores": {},
        "execution_plan": None,
        "plan_version": 0,
        "plan_status": "idle",
        "original_plan": None,
        "plan_modifications": [],
        "next_agents": [],
        "parallel_agents": [],
        "conditional_branches": {},
        "routing_history": [],
        "context": {},
        "conversation_context": [],
        "domain_context": {},
        "user_preferences": {},
        "progress": [],
        "completion_percentage": 0.0,
        "estimated_remaining_time": 0.0,
        "bottlenecks": [],
        "results": {},
        "intermediate_results": {},
        "cached_results": {},
        "errors": [],
        "error_recovery_attempts": 0,
        "max_recovery_attempts": 3,
        "fallback_triggered": False,
        "query_processing_time": 0.0,
        "total_execution_time": 0.0,
        "agent_execution_times": {},
        "llm_call_count": 0,
        "llm_token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "is_complete": False,
        "requires_human_input": False,
        "auto_mode": True,
        "debug_mode": False,
        "suggested_optimizations": [],
        "parallel_execution_possible": False,
        "cacheable_operations": [],
        "session_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "user_id": None,
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "metadata": {}
    }