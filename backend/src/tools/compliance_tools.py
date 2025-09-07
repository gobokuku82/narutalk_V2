"""
Compliance Tools for LangGraph 0.6.6
Rule Engine Pattern for Legal and Policy Validation
Following rules.md: tools must use @tool decorator
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import re
from enum import Enum
from langchain_core.tools import tool
from loguru import logger
import sqlite3
import os


class ViolationType(Enum):
    """Types of compliance violations"""
    MEDICAL_LAW = "medical_law"  # 의료법
    REBATE_LAW = "rebate_law"  # 리베이트법
    FAIR_TRADE = "fair_trade"  # 공정거래법
    INTERNAL_POLICY = "internal_policy"  # 회사 내규
    DATA_PRIVACY = "data_privacy"  # 개인정보보호
    CONTRACT_TERMS = "contract_terms"  # 계약 조건


class ComplianceLevel(Enum):
    """Compliance check severity levels"""
    CRITICAL = "critical"  # 즉시 조치 필요
    HIGH = "high"  # 높은 위험
    MEDIUM = "medium"  # 중간 위험
    LOW = "low"  # 낮은 위험
    INFO = "info"  # 정보성


class RuleEngine:
    """Rule Engine for compliance validation"""
    
    def __init__(self):
        self.rules = self._initialize_rules()
        
    def _initialize_rules(self) -> Dict[str, List[Dict]]:
        """Initialize compliance rules"""
        return {
            ViolationType.MEDICAL_LAW.value: [
                {
                    "id": "MED001",
                    "name": "의료기기 광고 제한",
                    "pattern": r"(치료|완치|의학적|임상|FDA승인)",
                    "level": ComplianceLevel.CRITICAL,
                    "description": "의료기기는 의학적 효능을 직접 광고할 수 없음",
                    "suggestion": "의학적 표현을 제거하고 기능 중심으로 설명"
                },
                {
                    "id": "MED002",
                    "name": "처방전 필요 제품",
                    "pattern": r"(처방|진단|투약|수술)",
                    "level": ComplianceLevel.HIGH,
                    "description": "처방전이 필요한 제품의 일반 판매 금지",
                    "suggestion": "의료진 대상 판매로 제한"
                }
            ],
            ViolationType.REBATE_LAW.value: [
                {
                    "id": "REB001",
                    "name": "부당한 경제적 이익 제공",
                    "pattern": r"(리베이트|현금.*지급|금품.*제공|무료.*제공)",
                    "level": ComplianceLevel.CRITICAL,
                    "description": "의료인에게 부당한 경제적 이익 제공 금지",
                    "suggestion": "정당한 할인이나 계약 조건으로 변경"
                },
                {
                    "id": "REB002",
                    "name": "과도한 접대",
                    "pattern": r"(접대|식사.*제공|골프|여행.*지원)",
                    "level": ComplianceLevel.HIGH,
                    "description": "5만원 초과 접대 금지",
                    "suggestion": "5만원 이하로 제한하거나 제거"
                },
                {
                    "id": "REB003",
                    "name": "학회 지원 제한",
                    "pattern": r"(학회.*지원|세미나.*비용|교육.*지원)",
                    "level": ComplianceLevel.MEDIUM,
                    "description": "학회 지원은 투명하게 공개되어야 함",
                    "suggestion": "공식 후원 계약서 작성 필요"
                }
            ],
            ViolationType.FAIR_TRADE.value: [
                {
                    "id": "FT001",
                    "name": "부당한 거래 거절",
                    "pattern": r"(독점|거래.*거절|공급.*중단)",
                    "level": ComplianceLevel.HIGH,
                    "description": "시장 지배적 지위 남용 금지",
                    "suggestion": "공정한 거래 조건 명시"
                },
                {
                    "id": "FT002",
                    "name": "가격 담합",
                    "pattern": r"(가격.*협의|담합|경쟁사.*가격)",
                    "level": ComplianceLevel.CRITICAL,
                    "description": "경쟁사와 가격 담합 금지",
                    "suggestion": "독립적인 가격 정책 수립"
                },
                {
                    "id": "FT003",
                    "name": "허위 광고",
                    "pattern": r"(최고|유일|1위|100%.*보장)",
                    "level": ComplianceLevel.MEDIUM,
                    "description": "과장되거나 허위 광고 금지",
                    "suggestion": "객관적 근거 제시 또는 표현 수정"
                }
            ],
            ViolationType.INTERNAL_POLICY.value: [
                {
                    "id": "POL001",
                    "name": "할인율 제한",
                    "pattern": r"(\d{3,}%.*할인|50%.*이상.*할인)",
                    "level": ComplianceLevel.MEDIUM,
                    "description": "회사 정책상 최대 할인율 30% 제한",
                    "suggestion": "할인율을 30% 이하로 조정"
                },
                {
                    "id": "POL002",
                    "name": "계약 기간",
                    "pattern": r"(5년.*이상|장기.*계약)",
                    "level": ComplianceLevel.LOW,
                    "description": "5년 이상 장기 계약 제한",
                    "suggestion": "계약 기간을 3년으로 조정"
                },
                {
                    "id": "POL003",
                    "name": "결제 조건",
                    "pattern": r"(선불|전액.*선납)",
                    "level": ComplianceLevel.INFO,
                    "description": "선불 결제는 승인 필요",
                    "suggestion": "분할 납부 조건 추가"
                }
            ],
            ViolationType.DATA_PRIVACY.value: [
                {
                    "id": "PRIV001",
                    "name": "개인정보 수집",
                    "pattern": r"(주민등록번호|여권.*번호|운전면허)",
                    "level": ComplianceLevel.CRITICAL,
                    "description": "민감 개인정보 수집 제한",
                    "suggestion": "필수 정보만 수집하도록 수정"
                },
                {
                    "id": "PRIV002",
                    "name": "제3자 제공",
                    "pattern": r"(정보.*제공|데이터.*공유|제3자)",
                    "level": ComplianceLevel.HIGH,
                    "description": "개인정보 제3자 제공시 동의 필요",
                    "suggestion": "명시적 동의 조항 추가"
                }
            ]
        }
    
    def check_violations(self, text: str, rule_types: List[str] = None) -> List[Dict]:
        """Check text for compliance violations"""
        violations = []
        
        # Default to all rule types if not specified
        if not rule_types:
            rule_types = [vt.value for vt in ViolationType]
        
        for rule_type in rule_types:
            if rule_type not in self.rules:
                continue
                
            for rule in self.rules[rule_type]:
                if re.search(rule["pattern"], text, re.IGNORECASE):
                    violations.append({
                        "rule_id": rule["id"],
                        "rule_name": rule["name"],
                        "violation_type": rule_type,
                        "level": rule["level"].value,
                        "description": rule["description"],
                        "suggestion": rule["suggestion"],
                        "matched_text": re.findall(rule["pattern"], text, re.IGNORECASE)
                    })
        
        return violations


class ValidationDB:
    """Database for storing validation results"""
    
    def __init__(self, db_path: str = "data/validation_results.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize validation database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create validation results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS validation_results (
                validation_id TEXT PRIMARY KEY,
                document_id TEXT,
                document_type TEXT,
                validation_date TEXT,
                total_violations INTEGER,
                critical_count INTEGER,
                high_count INTEGER,
                medium_count INTEGER,
                low_count INTEGER,
                compliance_score REAL,
                status TEXT,
                violations TEXT,
                suggestions TEXT,
                metadata TEXT
            )
        """)
        
        # Create violation details table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS violation_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                validation_id TEXT,
                rule_id TEXT,
                rule_name TEXT,
                violation_type TEXT,
                level TEXT,
                description TEXT,
                suggestion TEXT,
                matched_text TEXT,
                FOREIGN KEY (validation_id) REFERENCES validation_results(validation_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def save_validation_result(self, result: Dict) -> str:
        """Save validation result to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        validation_id = f"VAL-{datetime.now().strftime('%Y%m%d%H%M%S')}-{result.get('document_id', 'UNKNOWN')[:8]}"
        
        # Count violations by level
        violations = result.get("violations", [])
        level_counts = {
            "critical": sum(1 for v in violations if v.get("level") == "critical"),
            "high": sum(1 for v in violations if v.get("level") == "high"),
            "medium": sum(1 for v in violations if v.get("level") == "medium"),
            "low": sum(1 for v in violations if v.get("level") == "low")
        }
        
        # Calculate compliance score (100 - penalties)
        penalty = (level_counts["critical"] * 25 + 
                  level_counts["high"] * 15 + 
                  level_counts["medium"] * 5 + 
                  level_counts["low"] * 2)
        compliance_score = max(0, 100 - penalty)
        
        # Insert main validation result
        cursor.execute("""
            INSERT INTO validation_results 
            (validation_id, document_id, document_type, validation_date, 
             total_violations, critical_count, high_count, medium_count, low_count,
             compliance_score, status, violations, suggestions, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            validation_id,
            result.get("document_id"),
            result.get("document_type"),
            datetime.now().isoformat(),
            len(violations),
            level_counts["critical"],
            level_counts["high"],
            level_counts["medium"],
            level_counts["low"],
            compliance_score,
            "PASSED" if compliance_score >= 70 else "FAILED",
            json.dumps(violations, ensure_ascii=False),
            json.dumps(result.get("suggestions", []), ensure_ascii=False),
            json.dumps(result.get("metadata", {}), ensure_ascii=False)
        ))
        
        # Insert violation details
        for violation in violations:
            cursor.execute("""
                INSERT INTO violation_details
                (validation_id, rule_id, rule_name, violation_type, level, 
                 description, suggestion, matched_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                validation_id,
                violation.get("rule_id"),
                violation.get("rule_name"),
                violation.get("violation_type"),
                violation.get("level"),
                violation.get("description"),
                violation.get("suggestion"),
                json.dumps(violation.get("matched_text", []), ensure_ascii=False)
            ))
        
        conn.commit()
        conn.close()
        
        return validation_id


# Initialize singletons
rule_engine = RuleEngine()
validation_db = ValidationDB()


@tool
def check_medical_law_compliance(text: str) -> str:
    """
    Check document for medical law violations (의료법 위반 체크)
    
    Args:
        text: Document text to validate
    """
    violations = rule_engine.check_violations(text, [ViolationType.MEDICAL_LAW.value])
    
    result = {
        "check_type": "medical_law",
        "violations_found": len(violations),
        "violations": violations,
        "status": "PASSED" if len(violations) == 0 else "NEEDS_REVIEW",
        "checked_at": datetime.now().isoformat()
    }
    
    logger.info(f"Medical law check: {len(violations)} violations found")
    return json.dumps(result, ensure_ascii=False)


@tool
def check_rebate_law_compliance(text: str) -> str:
    """
    Check document for rebate law violations (리베이트법 위반 체크)
    
    Args:
        text: Document text to validate
    """
    violations = rule_engine.check_violations(text, [ViolationType.REBATE_LAW.value])
    
    result = {
        "check_type": "rebate_law",
        "violations_found": len(violations),
        "violations": violations,
        "status": "PASSED" if len(violations) == 0 else "NEEDS_REVIEW",
        "checked_at": datetime.now().isoformat()
    }
    
    logger.info(f"Rebate law check: {len(violations)} violations found")
    return json.dumps(result, ensure_ascii=False)


@tool
def check_fair_trade_compliance(text: str) -> str:
    """
    Check document for fair trade law violations (공정거래법 위반 체크)
    
    Args:
        text: Document text to validate
    """
    violations = rule_engine.check_violations(text, [ViolationType.FAIR_TRADE.value])
    
    result = {
        "check_type": "fair_trade",
        "violations_found": len(violations),
        "violations": violations,
        "status": "PASSED" if len(violations) == 0 else "NEEDS_REVIEW",
        "checked_at": datetime.now().isoformat()
    }
    
    logger.info(f"Fair trade check: {len(violations)} violations found")
    return json.dumps(result, ensure_ascii=False)


@tool
def check_internal_policy_compliance(text: str) -> str:
    """
    Check document for internal policy violations (회사 내규 위반 체크)
    
    Args:
        text: Document text to validate
    """
    violations = rule_engine.check_violations(text, [ViolationType.INTERNAL_POLICY.value])
    
    result = {
        "check_type": "internal_policy",
        "violations_found": len(violations),
        "violations": violations,
        "status": "PASSED" if len(violations) == 0 else "NEEDS_REVIEW",
        "checked_at": datetime.now().isoformat()
    }
    
    logger.info(f"Internal policy check: {len(violations)} violations found")
    return json.dumps(result, ensure_ascii=False)


@tool
def perform_full_compliance_check(document_id: str, document_text: str, document_type: str = "general") -> str:
    """
    Perform comprehensive compliance check (1차 법률 + 2차 내규)
    
    Args:
        document_id: Document identifier
        document_text: Full document text to validate
        document_type: Type of document (proposal, contract, report, etc.)
    """
    logger.info(f"Starting full compliance check for document {document_id}")
    
    # 1차 검증: 법률 위반 체크
    legal_violations = []
    
    # Medical law check
    medical_check = rule_engine.check_violations(
        document_text, [ViolationType.MEDICAL_LAW.value]
    )
    legal_violations.extend(medical_check)
    
    # Rebate law check
    rebate_check = rule_engine.check_violations(
        document_text, [ViolationType.REBATE_LAW.value]
    )
    legal_violations.extend(rebate_check)
    
    # Fair trade check
    fair_trade_check = rule_engine.check_violations(
        document_text, [ViolationType.FAIR_TRADE.value]
    )
    legal_violations.extend(fair_trade_check)
    
    # Data privacy check
    privacy_check = rule_engine.check_violations(
        document_text, [ViolationType.DATA_PRIVACY.value]
    )
    legal_violations.extend(privacy_check)
    
    # 2차 검증: 회사 내규 체크
    policy_violations = rule_engine.check_violations(
        document_text, [ViolationType.INTERNAL_POLICY.value]
    )
    
    # Combine all violations
    all_violations = legal_violations + policy_violations
    
    # Generate suggestions
    suggestions = []
    critical_violations = [v for v in all_violations if v.get("level") == "critical"]
    high_violations = [v for v in all_violations if v.get("level") == "high"]
    
    if critical_violations:
        suggestions.append({
            "priority": "IMMEDIATE",
            "message": "Critical violations found - document must be revised before proceeding",
            "violations": [v["rule_name"] for v in critical_violations]
        })
    
    if high_violations:
        suggestions.append({
            "priority": "HIGH",
            "message": "High-risk violations require management approval",
            "violations": [v["rule_name"] for v in high_violations]
        })
    
    # Prepare validation result
    validation_result = {
        "document_id": document_id,
        "document_type": document_type,
        "legal_violations": legal_violations,
        "policy_violations": policy_violations,
        "violations": all_violations,
        "total_violations": len(all_violations),
        "critical_count": len(critical_violations),
        "suggestions": suggestions,
        "metadata": {
            "checked_at": datetime.now().isoformat(),
            "rule_engine_version": "1.0"
        }
    }
    
    # Save to database
    validation_id = validation_db.save_validation_result(validation_result)
    validation_result["validation_id"] = validation_id
    
    # Calculate compliance status
    if len(critical_violations) > 0:
        validation_result["compliance_status"] = "FAILED"
        validation_result["action_required"] = "REVISION_REQUIRED"
    elif len(high_violations) > 0:
        validation_result["compliance_status"] = "CONDITIONAL"
        validation_result["action_required"] = "APPROVAL_REQUIRED"
    elif len(all_violations) > 0:
        validation_result["compliance_status"] = "PASSED_WITH_WARNINGS"
        validation_result["action_required"] = "REVIEW_RECOMMENDED"
    else:
        validation_result["compliance_status"] = "PASSED"
        validation_result["action_required"] = "NONE"
    
    logger.info(f"Compliance check completed: {validation_result['compliance_status']}")
    return json.dumps(validation_result, ensure_ascii=False)


@tool
def generate_compliance_suggestions(violations: List[Dict]) -> str:
    """
    Generate detailed suggestions for fixing compliance violations
    
    Args:
        violations: List of violations found
    """
    suggestions = {
        "revision_suggestions": [],
        "alternative_text": {},
        "approval_requirements": [],
        "risk_mitigation": []
    }
    
    for violation in violations:
        level = violation.get("level", "low")
        rule_id = violation.get("rule_id", "")
        
        # Generate specific suggestions based on violation type
        if violation.get("violation_type") == ViolationType.MEDICAL_LAW.value:
            suggestions["revision_suggestions"].append({
                "rule_id": rule_id,
                "original_issue": violation.get("matched_text", []),
                "suggestion": violation.get("suggestion"),
                "alternative": "Consider using factual product features instead of medical claims"
            })
            
        elif violation.get("violation_type") == ViolationType.REBATE_LAW.value:
            suggestions["revision_suggestions"].append({
                "rule_id": rule_id,
                "original_issue": violation.get("matched_text", []),
                "suggestion": violation.get("suggestion"),
                "alternative": "Replace with transparent pricing or legitimate business expenses"
            })
            suggestions["approval_requirements"].append(
                f"Legal team approval required for {violation.get('rule_name')}"
            )
            
        elif violation.get("violation_type") == ViolationType.FAIR_TRADE.value:
            suggestions["revision_suggestions"].append({
                "rule_id": rule_id,
                "original_issue": violation.get("matched_text", []),
                "suggestion": violation.get("suggestion"),
                "alternative": "Ensure competitive practices comply with antitrust laws"
            })
            
        elif violation.get("violation_type") == ViolationType.INTERNAL_POLICY.value:
            suggestions["revision_suggestions"].append({
                "rule_id": rule_id,
                "original_issue": violation.get("matched_text", []),
                "suggestion": violation.get("suggestion"),
                "alternative": "Adjust to comply with company policy guidelines"
            })
        
        # Add risk mitigation strategies for critical/high violations
        if level in ["critical", "high"]:
            suggestions["risk_mitigation"].append({
                "violation": violation.get("rule_name"),
                "risk_level": level,
                "mitigation": f"Immediate review and revision required for {violation.get('description')}"
            })
    
    # Summary
    suggestions["summary"] = {
        "total_suggestions": len(suggestions["revision_suggestions"]),
        "approvals_needed": len(suggestions["approval_requirements"]),
        "risk_items": len(suggestions["risk_mitigation"]),
        "estimated_revision_time": f"{len(violations) * 15} minutes"
    }
    
    return json.dumps(suggestions, ensure_ascii=False)


@tool
def save_validation_results(validation_data: Dict) -> str:
    """
    Save validation results to database
    
    Args:
        validation_data: Complete validation data to save
    """
    try:
        validation_id = validation_db.save_validation_result(validation_data)
        
        result = {
            "success": True,
            "validation_id": validation_id,
            "message": "Validation results saved successfully",
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Validation results saved: {validation_id}")
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Error saving validation results: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "Failed to save validation results"
        }, ensure_ascii=False)


@tool
def query_validation_history(document_id: str = None, status: str = None, 
                            date_from: str = None, date_to: str = None) -> str:
    """
    Query validation history from database
    
    Args:
        document_id: Filter by document ID
        status: Filter by status (PASSED, FAILED, CONDITIONAL)
        date_from: Start date for filtering
        date_to: End date for filtering
    """
    conn = sqlite3.connect(validation_db.db_path)
    cursor = conn.cursor()
    
    query = "SELECT * FROM validation_results WHERE 1=1"
    params = []
    
    if document_id:
        query += " AND document_id = ?"
        params.append(document_id)
    
    if status:
        query += " AND status = ?"
        params.append(status)
    
    if date_from:
        query += " AND validation_date >= ?"
        params.append(date_from)
    
    if date_to:
        query += " AND validation_date <= ?"
        params.append(date_to)
    
    query += " ORDER BY validation_date DESC LIMIT 100"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    results = []
    for row in rows:
        results.append({
            "validation_id": row[0],
            "document_id": row[1],
            "document_type": row[2],
            "validation_date": row[3],
            "total_violations": row[4],
            "compliance_score": row[9],
            "status": row[10]
        })
    
    conn.close()
    
    return json.dumps({
        "count": len(results),
        "results": results
    }, ensure_ascii=False)


@tool
def get_compliance_report(validation_id: str) -> str:
    """
    Get detailed compliance report for a validation
    
    Args:
        validation_id: Validation ID to retrieve
    """
    conn = sqlite3.connect(validation_db.db_path)
    cursor = conn.cursor()
    
    # Get main validation result
    cursor.execute(
        "SELECT * FROM validation_results WHERE validation_id = ?",
        (validation_id,)
    )
    main_result = cursor.fetchone()
    
    if not main_result:
        return json.dumps({
            "error": "Validation not found",
            "validation_id": validation_id
        }, ensure_ascii=False)
    
    # Get violation details
    cursor.execute(
        "SELECT * FROM violation_details WHERE validation_id = ?",
        (validation_id,)
    )
    violations = cursor.fetchall()
    
    conn.close()
    
    # Format report
    report = {
        "validation_id": main_result[0],
        "document_id": main_result[1],
        "document_type": main_result[2],
        "validation_date": main_result[3],
        "compliance_score": main_result[9],
        "status": main_result[10],
        "summary": {
            "total_violations": main_result[4],
            "critical": main_result[5],
            "high": main_result[6],
            "medium": main_result[7],
            "low": main_result[8]
        },
        "violations": [],
        "suggestions": json.loads(main_result[12]) if main_result[12] else []
    }
    
    for violation in violations:
        report["violations"].append({
            "rule_id": violation[2],
            "rule_name": violation[3],
            "type": violation[4],
            "level": violation[5],
            "description": violation[6],
            "suggestion": violation[7],
            "matched_text": json.loads(violation[8]) if violation[8] else []
        })
    
    return json.dumps(report, ensure_ascii=False)