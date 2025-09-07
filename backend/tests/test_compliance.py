"""
Test cases for Enhanced Compliance Agent with Rule Engine
Testing two-stage validation and violation suggestions
"""
import pytest
import json
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage
from src.state.agent_state import AgentState
from src.agents.compliance import compliance_agent
from src.tools.compliance_tools import (
    check_medical_law_compliance,
    check_rebate_law_compliance,
    check_fair_trade_compliance,
    check_internal_policy_compliance,
    perform_full_compliance_check,
    generate_compliance_suggestions,
    save_validation_results,
    query_validation_history,
    get_compliance_report,
    RuleEngine,
    ValidationDB,
    ViolationType,
    ComplianceLevel
)


class TestComplianceTools:
    """Test suite for compliance tools"""
    
    @pytest.fixture
    def rule_engine(self):
        """Create a test rule engine instance"""
        return RuleEngine()
    
    @pytest.fixture
    def validation_db(self):
        """Create a test validation database instance"""
        return ValidationDB(db_path="data/test_validation.db")
    
    def test_medical_law_compliance(self):
        """Test medical law violation detection"""
        # Test with violations
        result = check_medical_law_compliance.invoke({
            "text": "이 제품은 암을 완치할 수 있으며 FDA 승인을 받았습니다."
        })
        data = json.loads(result)
        
        assert data["check_type"] == "medical_law"
        assert data["violations_found"] > 0
        assert data["status"] == "NEEDS_REVIEW"
        
        # Test without violations
        result = check_medical_law_compliance.invoke({
            "text": "이 제품은 데이터 분석 기능을 제공합니다."
        })
        data = json.loads(result)
        
        assert data["violations_found"] == 0
        assert data["status"] == "PASSED"
    
    def test_rebate_law_compliance(self):
        """Test rebate law violation detection"""
        # Test with violations
        result = check_rebate_law_compliance.invoke({
            "text": "의사에게 현금 100만원을 리베이트로 제공하고 골프 접대를 진행합니다."
        })
        data = json.loads(result)
        
        assert data["check_type"] == "rebate_law"
        assert data["violations_found"] > 0
        
        # Check specific violations
        violations = data["violations"]
        violation_types = [v["rule_id"] for v in violations]
        assert "REB001" in violation_types  # 부당한 경제적 이익
        assert "REB002" in violation_types  # 과도한 접대
    
    def test_fair_trade_compliance(self):
        """Test fair trade law violation detection"""
        # Test with violations
        result = check_fair_trade_compliance.invoke({
            "text": "우리 제품이 시장 1위이며 경쟁사와 가격을 협의하여 독점적 지위를 유지합니다."
        })
        data = json.loads(result)
        
        assert data["check_type"] == "fair_trade"
        assert data["violations_found"] > 0
        
        # Check for specific violations
        violations = data["violations"]
        assert any(v["rule_id"] == "FT002" for v in violations)  # 가격 담합
    
    def test_internal_policy_compliance(self):
        """Test internal policy violation detection"""
        # Test with violations
        result = check_internal_policy_compliance.invoke({
            "text": "특별 프로모션으로 80% 할인을 제공하며 10년 장기 계약을 체결합니다."
        })
        data = json.loads(result)
        
        assert data["check_type"] == "internal_policy"
        assert data["violations_found"] > 0
        
        # Check specific policy violations
        violations = data["violations"]
        violation_types = [v["rule_id"] for v in violations]
        assert "POL001" in violation_types  # 할인율 제한
        assert "POL002" in violation_types  # 계약 기간
    
    def test_perform_full_compliance_check(self):
        """Test comprehensive compliance check"""
        test_document = """
        삼성전자와의 제안서
        
        1. 제품 소개
        우리의 AI 솔루션은 암을 치료할 수 있으며, 의사에게 리베이트 10%를 제공합니다.
        
        2. 가격 정책
        경쟁사와 협의하여 가격을 설정하며, 70% 특별 할인을 제공합니다.
        
        3. 계약 조건
        7년 장기 계약이며, 전액 선불 결제가 필요합니다.
        """
        
        result = perform_full_compliance_check.invoke({
            "document_id": "TEST-001",
            "document_text": test_document,
            "document_type": "proposal"
        })
        data = json.loads(result)
        
        assert "validation_id" in data
        assert data["total_violations"] > 0
        assert data["critical_count"] > 0  # Should have critical violations
        assert data["compliance_status"] == "FAILED"
        assert data["action_required"] == "REVISION_REQUIRED"
        
        # Check both legal and policy violations
        assert len(data["legal_violations"]) > 0
        assert len(data["policy_violations"]) > 0
    
    def test_generate_compliance_suggestions(self):
        """Test suggestion generation for violations"""
        test_violations = [
            {
                "rule_id": "MED001",
                "rule_name": "의료기기 광고 제한",
                "violation_type": "medical_law",
                "level": "critical",
                "description": "의학적 효능 직접 광고 금지",
                "suggestion": "의학적 표현 제거",
                "matched_text": ["치료", "완치"]
            },
            {
                "rule_id": "POL001",
                "rule_name": "할인율 제한",
                "violation_type": "internal_policy",
                "level": "medium",
                "description": "최대 할인율 30% 제한",
                "suggestion": "할인율 조정",
                "matched_text": ["70% 할인"]
            }
        ]
        
        result = generate_compliance_suggestions.invoke({
            "violations": test_violations
        })
        data = json.loads(result)
        
        assert "revision_suggestions" in data
        assert len(data["revision_suggestions"]) == 2
        assert "risk_mitigation" in data
        assert data["summary"]["total_suggestions"] == 2
    
    def test_save_and_query_validation_results(self, validation_db):
        """Test saving and querying validation results"""
        # Create test validation data
        test_validation = {
            "document_id": "TEST-002",
            "document_type": "contract",
            "violations": [
                {
                    "rule_id": "REB001",
                    "rule_name": "부당한 경제적 이익",
                    "violation_type": "rebate_law",
                    "level": "critical",
                    "description": "리베이트 제공 금지",
                    "suggestion": "제거 필요",
                    "matched_text": ["리베이트"]
                }
            ],
            "metadata": {"test": True}
        }
        
        # Save validation
        validation_id = validation_db.save_validation_result(test_validation)
        assert validation_id.startswith("VAL-")
        
        # Query validation history
        result = query_validation_history.invoke({
            "document_id": "TEST-002"
        })
        data = json.loads(result)
        
        assert data["count"] > 0
        assert any(r["document_id"] == "TEST-002" for r in data["results"])
    
    def test_get_compliance_report(self, validation_db):
        """Test retrieving detailed compliance report"""
        # First save a validation
        test_validation = {
            "document_id": "TEST-003",
            "document_type": "proposal",
            "violations": [
                {
                    "rule_id": "FT003",
                    "rule_name": "허위 광고",
                    "violation_type": "fair_trade",
                    "level": "medium",
                    "description": "과장 광고 금지",
                    "suggestion": "객관적 근거 제시",
                    "matched_text": ["최고", "1위"]
                }
            ],
            "suggestions": [{"priority": "MEDIUM", "message": "Review required"}]
        }
        
        validation_id = validation_db.save_validation_result(test_validation)
        
        # Get compliance report
        result = get_compliance_report.invoke({
            "validation_id": validation_id
        })
        data = json.loads(result)
        
        assert data["validation_id"] == validation_id
        assert data["document_id"] == "TEST-003"
        assert len(data["violations"]) == 1
        assert data["violations"][0]["rule_id"] == "FT003"


class TestRuleEngine:
    """Test Rule Engine functionality"""
    
    def test_rule_initialization(self):
        """Test that rules are properly initialized"""
        engine = RuleEngine()
        
        assert ViolationType.MEDICAL_LAW.value in engine.rules
        assert ViolationType.REBATE_LAW.value in engine.rules
        assert ViolationType.FAIR_TRADE.value in engine.rules
        assert ViolationType.INTERNAL_POLICY.value in engine.rules
        
        # Check rule structure
        medical_rules = engine.rules[ViolationType.MEDICAL_LAW.value]
        assert len(medical_rules) > 0
        assert "id" in medical_rules[0]
        assert "pattern" in medical_rules[0]
        assert "level" in medical_rules[0]
    
    def test_check_violations_multiple_types(self):
        """Test checking violations across multiple rule types"""
        engine = RuleEngine()
        
        test_text = """
        우리 제품은 암을 완치시킬 수 있으며,
        의사에게 현금 리베이트를 제공합니다.
        경쟁사와 가격을 협의하고,
        80% 할인을 제공합니다.
        """
        
        violations = engine.check_violations(test_text)
        
        # Should find violations from multiple categories
        violation_types = set(v["violation_type"] for v in violations)
        assert ViolationType.MEDICAL_LAW.value in violation_types
        assert ViolationType.REBATE_LAW.value in violation_types
        assert ViolationType.FAIR_TRADE.value in violation_types
        assert ViolationType.INTERNAL_POLICY.value in violation_types
    
    def test_check_violations_specific_types(self):
        """Test checking violations for specific rule types only"""
        engine = RuleEngine()
        
        test_text = "의사에게 현금 리베이트 제공 및 80% 할인"
        
        # Check only rebate law
        violations = engine.check_violations(
            test_text,
            [ViolationType.REBATE_LAW.value]
        )
        
        assert all(v["violation_type"] == ViolationType.REBATE_LAW.value 
                  for v in violations)
        assert len(violations) > 0


class TestComplianceAgent:
    """Test suite for the enhanced compliance agent"""
    
    def test_compliance_agent_with_document(self):
        """Test compliance agent validating a document"""
        state = {
            "messages": [HumanMessage(content="Validate the generated document")],
            "current_agent": "compliance",
            "task_type": "compliance",
            "task_description": "Validate the generated document",
            "progress": [],
            "context": {
                "document_id": "DOC-TEST-001",
                "document_type": "proposal",
                "compliance_ready": True
            },
            "metadata": {},
            "results": {
                "document": {
                    "data": {
                        "document_type": "proposal",
                        "content": {
                            "client_name": "Test Corp",
                            "proposal": "의사에게 리베이트 10% 제공하며 70% 할인"
                        }
                    }
                }
            },
            "errors": [],
            "is_complete": False
        }
        
        result = compliance_agent(state)
        
        # Check result structure
        assert result is not None
        assert "messages" in result
        assert len(result["messages"]) > 0
        assert "results" in result
        assert "compliance" in result["results"]
        
        # Check compliance validation
        compliance_result = result["results"]["compliance"]
        assert "compliance_status" in compliance_result
        assert "violations" in compliance_result
        assert len(compliance_result["violations"]) > 0  # Should find violations
        assert compliance_result["compliance_status"] in ["FAILED", "CONDITIONAL"]
    
    def test_compliance_agent_clean_document(self):
        """Test compliance agent with a clean document"""
        state = {
            "messages": [HumanMessage(content="Validate clean document")],
            "current_agent": "compliance",
            "task_type": "compliance",
            "task_description": "Validate clean document",
            "progress": [],
            "context": {
                "document_id": "DOC-CLEAN-001",
                "document_type": "report"
            },
            "metadata": {},
            "results": {
                "document": {
                    "data": {
                        "document_type": "report",
                        "content": {
                            "title": "Sales Report",
                            "data": "Q1 sales increased by 15%"
                        }
                    }
                }
            },
            "errors": [],
            "is_complete": False
        }
        
        result = compliance_agent(state)
        
        # Check clean validation
        compliance_result = result["results"]["compliance"]
        assert compliance_result["compliance_status"] in ["PASSED", "PASSED_WITH_WARNINGS"]
        assert len(compliance_result.get("violations", [])) == 0 or \
               all(v.get("level") in ["low", "info"] for v in compliance_result["violations"])
    
    def test_compliance_agent_error_handling(self):
        """Test compliance agent error handling"""
        state = {
            "messages": [],
            "current_agent": "compliance",
            "task_type": "compliance",
            "task_description": "",
            "progress": [],
            "context": {},
            "metadata": {},
            "results": {},  # No document to validate
            "errors": [],
            "is_complete": False
        }
        
        result = compliance_agent(state)
        
        # Should still return a valid result
        assert result is not None
        assert "messages" in result
        assert "current_agent" in result
    
    def test_compliance_agent_suggestions(self):
        """Test that compliance agent generates suggestions"""
        state = {
            "messages": [HumanMessage(content="Check compliance")],
            "current_agent": "compliance",
            "task_type": "compliance",
            "task_description": "Check compliance",
            "progress": [],
            "context": {
                "document_type": "proposal"
            },
            "metadata": {},
            "results": {
                "document": {
                    "data": {
                        "content": "우리 제품은 최고이며 100% 효과를 보장합니다. 90% 할인 제공."
                    }
                }
            },
            "errors": [],
            "is_complete": False
        }
        
        result = compliance_agent(state)
        
        # Check suggestions are generated
        compliance_result = result["results"]["compliance"]
        assert "suggestions" in compliance_result
        suggestions = compliance_result["suggestions"]
        
        if compliance_result.get("violations"):
            assert suggestions.get("revision_suggestions") or \
                   suggestions.get("risk_mitigation") or \
                   suggestions.get("approval_requirements")


class TestValidationDB:
    """Test ValidationDB storage functionality"""
    
    def test_database_initialization(self):
        """Test that database tables are created"""
        db = ValidationDB(db_path="data/test_init.db")
        
        # Check tables exist by attempting to query
        import sqlite3
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        # Check validation_results table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='validation_results'")
        assert cursor.fetchone() is not None
        
        # Check violation_details table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='violation_details'")
        assert cursor.fetchone() is not None
        
        conn.close()
    
    def test_compliance_score_calculation(self):
        """Test compliance score calculation logic"""
        db = ValidationDB(db_path="data/test_score.db")
        
        # Test with different violation levels
        test_data = {
            "document_id": "SCORE-TEST",
            "document_type": "test",
            "violations": [
                {"level": "critical"},  # -25
                {"level": "high"},      # -15
                {"level": "medium"},    # -5
                {"level": "low"}        # -2
            ]
        }
        
        validation_id = db.save_validation_result(test_data)
        
        # Check saved score
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT compliance_score FROM validation_results WHERE validation_id = ?",
            (validation_id,)
        )
        score = cursor.fetchone()[0]
        conn.close()
        
        # Score should be 100 - (25 + 15 + 5 + 2) = 53
        assert score == 53


@pytest.mark.asyncio
class TestComplianceIntegration:
    """Integration tests for compliance with StateGraph"""
    
    async def test_compliance_in_graph_flow(self):
        """Test compliance agent within the graph flow"""
        from src.core.graph import SalesSupportApp
        
        app = SalesSupportApp(use_sqlite=False)
        
        # Request compliance check
        result = await app.aprocess_request(
            user_input="Check compliance for proposal with 80% discount and rebate offers",
            thread_id="test_compliance_1"
        )
        
        # Check that compliance was involved
        progress = result.get("progress", [])
        agents = [p.get("agent") for p in progress]
        
        assert "supervisor" in agents or "compliance" in agents
        
        # Check results if compliance was executed
        if "compliance" in result.get("results", {}):
            compliance_results = result["results"]["compliance"]
            assert "compliance_status" in compliance_results
            assert "violations" in compliance_results
    
    async def test_document_to_compliance_flow(self):
        """Test document generation followed by compliance check"""
        from src.core.graph import SalesSupportApp
        
        app = SalesSupportApp(use_sqlite=False)
        
        # Request that should trigger document then compliance
        result = await app.aprocess_request(
            user_input="Create a proposal for Samsung with special pricing and validate compliance",
            thread_id="test_doc_compliance_flow"
        )
        
        # Check flow
        progress = result.get("progress", [])
        agents = [p.get("agent") for p in progress]
        
        # Should have both document and compliance
        if "document" in agents and "compliance" in agents:
            doc_index = agents.index("document")
            comp_index = agents.index("compliance")
            # Compliance should come after document
            assert comp_index > doc_index