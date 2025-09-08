"""
Enhanced Compliance Agent for LangGraph 0.6.6
Rule Engine Pattern with Two-stage Validation
Following rules.md: Node functions MUST return dict
"""
from typing import Dict, Any
from datetime import datetime
import json
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from loguru import logger

from ..state.agent_state import AgentState
from ..tools.compliance_tools import (
    check_medical_law_compliance,
    check_rebate_law_compliance,
    check_fair_trade_compliance,
    check_internal_policy_compliance,
    perform_full_compliance_check,
    generate_compliance_suggestions,
    save_validation_results,
    query_validation_history,
    get_compliance_report
)


def compliance_agent(state: AgentState) -> dict:
    """
    Enhanced Compliance Agent with Rule Engine Pattern
    Two-stage validation: 1차 법률 검증 → 2차 내규 검증
    Following rules.md: Node functions MUST return dict
    """
    # Initialize LLM with tools binding
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    tools = [
        check_medical_law_compliance,
        check_rebate_law_compliance,
        check_fair_trade_compliance,
        check_internal_policy_compliance,
        perform_full_compliance_check,
        generate_compliance_suggestions,
        save_validation_results,
        query_validation_history,
        get_compliance_report
    ]
    llm_with_tools = llm.bind_tools(tools)
    
    # Get task description and context
    task_description = state.get("task_description", "")
    context = state.get("context", {})
    results = state.get("results", {})
    messages = state.get("messages", [])
    
    # Progress tracking
    progress_update = {
        "agent": "compliance",
        "timestamp": datetime.now().isoformat(),
        "action": "performing_compliance_validation"
    }
    
    logger.info(f"Compliance agent processing: {task_description[:100]}...")
    
    try:
        # Get document to validate
        document_text = ""
        document_id = context.get("document_id", "UNKNOWN")
        document_type = context.get("document_type", "general")
        
        # Extract document text from results or context
        if "document" in results:
            doc_data = results["document"].get("data", {})
            if doc_data:
                # Convert document data to text for validation
                if isinstance(doc_data, dict):
                    if "content" in doc_data:
                        document_text = json.dumps(doc_data["content"], ensure_ascii=False)
                    elif "proposal_sections" in doc_data:
                        document_text = json.dumps(doc_data["proposal_sections"], ensure_ascii=False)
                    elif "formatted_notes" in doc_data:
                        document_text = doc_data["formatted_notes"]
                    else:
                        document_text = json.dumps(doc_data, ensure_ascii=False)
                else:
                    document_text = str(doc_data)
        
        # If no document from results, check if task description contains text to validate
        if not document_text and task_description:
            document_text = task_description
        
        logger.info(f"Validating document {document_id} of type {document_type}")
        
        # Perform comprehensive compliance check
        validation_result = perform_full_compliance_check.invoke({
            "document_id": document_id,
            "document_text": document_text,
            "document_type": document_type
        })
        validation_data = json.loads(validation_result)
        
        # Generate suggestions for violations
        suggestions_result = None
        if validation_data.get("violations"):
            suggestions_result = generate_compliance_suggestions.invoke({
                "violations": validation_data["violations"]
            })
            suggestions_data = json.loads(suggestions_result)
        else:
            suggestions_data = {"summary": {"total_suggestions": 0}}
        
        # Format compliance report
        compliance_status = validation_data.get("compliance_status", "UNKNOWN")
        action_required = validation_data.get("action_required", "NONE")
        
        # Determine status emoji
        status_emoji = {
            "PASSED": "✅",
            "PASSED_WITH_WARNINGS": "⚠️",
            "CONDITIONAL": "🔶",
            "FAILED": "❌"
        }.get(compliance_status, "❓")
        
        compliance_report = f"""
{status_emoji} **Compliance Validation Report**

**Document ID:** {document_id}
**Document Type:** {document_type.replace('_', ' ').title()}
**Validation ID:** {validation_data.get('validation_id', 'N/A')}
**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📊 Validation Summary

**Overall Status:** {compliance_status}
**Action Required:** {action_required}
**Total Violations:** {validation_data.get('total_violations', 0)}

### Violation Breakdown:
- 🔴 Critical: {validation_data.get('critical_count', 0)}
- 🟠 High: {len([v for v in validation_data.get('violations', []) if v.get('level') == 'high'])}
- 🟡 Medium: {len([v for v in validation_data.get('violations', []) if v.get('level') == 'medium'])}
- 🟢 Low: {len([v for v in validation_data.get('violations', []) if v.get('level') == 'low'])}

---

## 🔍 1차 검증: 법률 위반 체크

### 의료법 (Medical Law)
{_format_violations(validation_data.get('legal_violations', []), 'medical_law')}

### 리베이트법 (Rebate Law)
{_format_violations(validation_data.get('legal_violations', []), 'rebate_law')}

### 공정거래법 (Fair Trade Law)
{_format_violations(validation_data.get('legal_violations', []), 'fair_trade')}

### 개인정보보호법 (Data Privacy)
{_format_violations(validation_data.get('legal_violations', []), 'data_privacy')}

---

## 📋 2차 검증: 회사 내규 체크

{_format_violations(validation_data.get('policy_violations', []), 'internal_policy')}

---

## 💡 수정 제안 (Revision Suggestions)

{_format_suggestions(suggestions_data) if suggestions_data else "No suggestions needed - document is compliant."}

---

## 📈 Compliance Score

**Score:** {_calculate_compliance_score(validation_data)}/100
**Risk Level:** {_determine_risk_level(validation_data)}

---

## ✅ Next Steps

{_generate_next_steps(compliance_status, action_required)}
"""
        
        # Save validation results to database
        save_result = save_validation_results.invoke({
            "validation_data": validation_data
        })
        save_data = json.loads(save_result)
        
        if save_data.get("success"):
            logger.info(f"Validation results saved: {save_data.get('validation_id')}")
        
        # Update progress
        progress_update["status"] = "completed"
        progress_update["summary"] = f"Compliance check {compliance_status}"
        progress_update["validation_id"] = validation_data.get("validation_id")
        progress_update["violations_found"] = validation_data.get("total_violations", 0)
        
        # Store validation results
        results_update = state.get("results", {})
        results_update["compliance"] = {
            "validation_id": validation_data.get("validation_id"),
            "compliance_status": compliance_status,
            "action_required": action_required,
            "violations": validation_data.get("violations", []),
            "suggestions": suggestions_data,
            "timestamp": datetime.now().isoformat(),
            "status": "completed"
        }
        
        # Determine if re-routing is needed based on compliance status
        needs_rework = compliance_status in ["FAILED", "CONDITIONAL"]
        next_agent = None
        
        if needs_rework:
            # Determine which agent to route back to
            if validation_data.get("critical_count", 0) > 0:
                # Critical violations - need to regenerate document
                next_agent = "document"
                logger.warning(f"Critical violations found - routing back to document agent")
            elif len([v for v in validation_data.get("violations", []) if v.get("level") == "high"]) > 2:
                # Multiple high violations - may need different search parameters
                next_agent = "search"
                logger.warning(f"Multiple high violations - routing back to search agent")
            elif action_required == "REVISION_REQUIRED":
                # Document needs revision
                next_agent = "document"
                logger.warning(f"Document revision required - routing back to document agent")
        
        # Update context with compliance results and routing decision
        updated_context = {
            **context,
            "compliance_checked": True,
            "compliance_status": compliance_status,
            "compliance_passed": compliance_status in ["PASSED", "PASSED_WITH_WARNINGS"],
            "validation_id": validation_data.get("validation_id"),
            "needs_rework": needs_rework,
            "compliance_violations": validation_data.get("violations", []),
            "compliance_suggestions": suggestions_data.get("revision_suggestions", [])
        }
        
        # If re-routing, add information for the target agent
        if next_agent == "document":
            updated_context["document_revision_needed"] = True
            updated_context["revision_reason"] = "compliance_violations"
            updated_context["revision_suggestions"] = suggestions_data.get("revision_suggestions", [])
        elif next_agent == "search":
            updated_context["search_refinement_needed"] = True
            updated_context["search_focus"] = "compliance_requirements"
        
        return {
            "messages": [AIMessage(
                content=compliance_report,
                metadata={
                    "agent": "compliance",
                    "status": "completed",
                    "compliance_status": compliance_status,
                    "needs_rework": needs_rework
                }
            )],
            "current_agent": "compliance",
            "progress": [progress_update],
            "results": results_update,
            "context": updated_context,
            "execution_plan": state.get("execution_plan", []),
            "current_step": state.get("current_step", 0),
            "next_agent": next_agent  # Will trigger re-routing if not None
        }
        
    except Exception as e:
        logger.error(f"Error in compliance agent: {str(e)}")
        
        # Error handling
        error_message = f"⚠️ Compliance Validation Error: {str(e)}"
        progress_update["status"] = "error"
        progress_update["error"] = str(e)
        
        return {
            "messages": [AIMessage(
                content=error_message,
                metadata={"agent": "compliance", "status": "error"}
            )],
            "current_agent": "compliance",
            "progress": [progress_update],
            "errors": state.get("errors", []) + [str(e)],
            "context": context,
            "execution_plan": state.get("execution_plan", []),
            "current_step": state.get("current_step", 0),
            "next_agent": None
        }
    
def _format_violations(violations: list, violation_type: str) -> str:
    """Format violations for display"""
    filtered = [v for v in violations if v.get("violation_type") == violation_type]
    if not filtered:
        return "✅ No violations found"
    
    result = ""
    for v in filtered:
        level_emoji = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢"
        }.get(v.get("level", "low"), "⚪")
        
        result += f"\n{level_emoji} **{v.get('rule_name', 'Unknown')}**\n"
        result += f"   - Description: {v.get('description', '')}\n"
        result += f"   - Matched: {', '.join(v.get('matched_text', []))}\n"
        result += f"   - Suggestion: {v.get('suggestion', '')}\n"
    
    return result


def _format_suggestions(suggestions: dict) -> str:
    """Format suggestions for display"""
    if not suggestions or suggestions.get("summary", {}).get("total_suggestions", 0) == 0:
        return "No modifications required."
    
    result = ""
    
    # Revision suggestions
    if suggestions.get("revision_suggestions"):
        result += "### Recommended Revisions:\n"
        for i, rev in enumerate(suggestions["revision_suggestions"], 1):
            result += f"{i}. **{rev.get('rule_id', '')}**\n"
            result += f"   - Issue: {rev.get('original_issue', [])}\n"
            result += f"   - Fix: {rev.get('suggestion', '')}\n"
            result += f"   - Alternative: {rev.get('alternative', '')}\n\n"
    
    # Approval requirements
    if suggestions.get("approval_requirements"):
        result += "\n### Approvals Required:\n"
        for req in suggestions["approval_requirements"]:
            result += f"- {req}\n"
    
    # Risk mitigation
    if suggestions.get("risk_mitigation"):
        result += "\n### Risk Mitigation:\n"
        for risk in suggestions["risk_mitigation"]:
            result += f"- **{risk.get('risk_level', '').upper()}**: {risk.get('mitigation', '')}\n"
    
    return result


def _calculate_compliance_score(validation_data: dict) -> int:
    """Calculate compliance score"""
    violations = validation_data.get("violations", [])
    if not violations:
        return 100
    
    penalty = 0
    for v in violations:
        level = v.get("level", "low")
        if level == "critical":
            penalty += 25
        elif level == "high":
            penalty += 15
        elif level == "medium":
            penalty += 5
        elif level == "low":
            penalty += 2
    
    return max(0, 100 - penalty)


def _determine_risk_level(validation_data: dict) -> str:
    """Determine overall risk level"""
    critical = validation_data.get("critical_count", 0)
    if critical > 0:
        return "🔴 CRITICAL RISK"
    
    high = len([v for v in validation_data.get("violations", []) if v.get("level") == "high"])
    if high > 0:
        return "🟠 HIGH RISK"
    
    medium = len([v for v in validation_data.get("violations", []) if v.get("level") == "medium"])
    if medium > 0:
        return "🟡 MEDIUM RISK"
    
    low = len([v for v in validation_data.get("violations", []) if v.get("level") == "low"])
    if low > 0:
        return "🟢 LOW RISK"
    
    return "✅ NO RISK"


def _generate_next_steps(status: str, action: str) -> str:
    """Generate next steps based on compliance status"""
    steps = {
        "FAILED": [
            "1. Review and address all critical violations immediately",
            "2. Revise document according to suggestions",
            "3. Submit for re-validation",
            "4. Obtain necessary approvals before proceeding"
        ],
        "CONDITIONAL": [
            "1. Address high-priority violations",
            "2. Obtain management approval",
            "3. Document risk mitigation measures",
            "4. Proceed with caution"
        ],
        "PASSED_WITH_WARNINGS": [
            "1. Review warnings and consider improvements",
            "2. Document acceptance of minor risks",
            "3. Monitor for future compliance updates",
            "4. Proceed with standard process"
        ],
        "PASSED": [
            "1. Document is compliant and ready for use",
            "2. No immediate action required",
            "3. Maintain for audit records",
            "4. Proceed with confidence"
        ]
    }
    
    step_list = steps.get(status, ["No specific steps available"])
    return "\n".join(step_list)