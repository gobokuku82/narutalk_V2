"""
Enhanced Document Agent for LangGraph 0.6.6
Natural language parsing and document generation
Following rules.md: Node functions MUST return dict
"""
from typing import Dict, Any
from datetime import datetime
import json
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from loguru import logger

from ..state.agent_state import AgentState
from ..tools.document_tools import (
    parse_natural_language,
    natural_language_to_document,
    create_visit_report,
    create_product_demo_request,
    create_sample_request,
    create_general_document
)


def document_agent(state: AgentState) -> dict:
    """
    Enhanced Document Agent with natural language parsing
    Following rules.md: Node functions MUST return dict
    Auto-routes to compliance when document is completed
    """
    # Initialize LLM with tools binding
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
    tools = [
        parse_natural_language,
        natural_language_to_document,
        create_visit_report,
        create_product_demo_request,
        create_sample_request,
        create_general_document
    ]
    llm_with_tools = llm.bind_tools(tools)
    
    # Get task description and context
    task_description = state.get("task_description", "")
    context = state.get("context", {})
    results = state.get("results", {})
    messages = state.get("messages", [])
    
    # Progress tracking
    progress_update = {
        "agent": "document",
        "timestamp": datetime.now().isoformat(),
        "action": "generating_document"
    }
    
    logger.info(f"Document agent processing: {task_description[:100]}...")
    
    try:
        # Check if this is natural language input
        is_natural_language = any([
            "방문" in task_description or "visit" in task_description.lower(),
            "데모" in task_description or "demo" in task_description.lower(),
            "샘플" in task_description or "sample" in task_description.lower(),
            "제안서" in task_description or "proposal" in task_description.lower(),
            "회의" in task_description or "meeting" in task_description.lower(),
            "보고서" in task_description or "report" in task_description.lower()
        ])
        
        document_data = None
        doc_type = "general"
        
        if is_natural_language:
            # Parse natural language and create structured document
            logger.info("Processing natural language input...")
            nl_result = natural_language_to_document.invoke({"text": task_description})
            document_data = json.loads(nl_result)
            doc_type = document_data.get("document_type", "general")
            
        else:
            # Use traditional document generation based on context
            if "proposal" in task_description.lower() or "제안서" in task_description:
                doc_type = "proposal"
                document_data = {
                    "document_type": "proposal",
                    "content": {
                        "client_name": context.get("client_name", "Client"),
                        "product_info": context.get("product_info", "Our solutions"),
                        "pricing": context.get("pricing", "Custom pricing"),
                        "terms": context.get("terms", "Standard terms")
                    }
                }
                
            elif "meeting" in task_description.lower() or "회의" in task_description:
                doc_type = "meeting_notes"
                document_data = {
                    "document_type": "meeting_notes",
                    "content": {
                        "meeting_title": context.get("meeting_title", "Team Meeting"),
                        "participants": context.get("participants", ["Team"]),
                        "agenda": context.get("agenda", "Discussion items"),
                        "decisions": context.get("decisions", []),
                        "action_items": context.get("action_items", [])
                    }
                }
                
            else:
                # Default to visit report or general document
                doc_type = "visit_report"
                result = create_visit_report.invoke({
                    "client_name": context.get("client_name", "Client"),
                    "visit_date": context.get("visit_date", datetime.now().strftime("%Y-%m-%d")),
                    "participants": context.get("participants", ["Sales Team"]),
                    "discussion_points": context.get("discussion_points", ["General discussion"]),
                    "action_items": context.get("action_items", ["Follow up"]),
                    "next_steps": context.get("next_steps", "Schedule next meeting")
                })
                document_data = json.loads(result)
        
        # Generate document ID
        document_id = f"DOC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Format output message
        document_message = f"""
📄 **Document Generated Successfully**

Document Type: {doc_type.replace('_', ' ').title()}
Document ID: {document_id}
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

**Document Summary:**
{json.dumps(document_data, ensure_ascii=False, indent=2) if document_data else 'No document generated'}

---

{"✅ Document ready for compliance check" if doc_type in ['proposal', 'visit_report'] else "📋 Document completed"}
"""
        
        # Update progress
        progress_update["status"] = "completed"
        progress_update["summary"] = f"Generated {doc_type} document"
        progress_update["document_id"] = document_id
        
        # Store document in results
        results_update = state.get("results", {})
        results_update["document"] = {
            "document_id": document_id,
            "type": doc_type,
            "data": document_data,
            "timestamp": datetime.now().isoformat(),
            "status": "generated"
        }
        
        # Update context to trigger compliance check if needed
        requires_compliance = doc_type in ['proposal', 'visit_report', 'contract']
        updated_context = {
            **context,
            "document_generated": True,
            "document_type": doc_type,
            "document_id": document_id,
            "requires_compliance_check": requires_compliance,
            "compliance_ready": requires_compliance  # Signal for auto-routing
        }
        
        return {
            "messages": [AIMessage(
                content=document_message,
                metadata={
                    "agent": "document",
                    "status": "completed",
                    "requires_compliance": requires_compliance
                }
            )],
            "current_agent": "document",
            "progress": [progress_update],
            "results": results_update,
            "context": updated_context,
            # Signal for supervisor to route to compliance
            "next_agent": "compliance" if requires_compliance else None,
            "execution_plan": state.get("execution_plan", []),
            "current_step": state.get("current_step", 0)
        }
        
    except Exception as e:
        logger.error(f"Error in document agent: {str(e)}")
        
        # Error handling
        error_message = f"⚠️ Document Generation Error: {str(e)}"
        progress_update["status"] = "error"
        progress_update["error"] = str(e)
        
        return {
            "messages": [AIMessage(
                content=error_message,
                metadata={"agent": "document", "status": "error"}
            )],
            "current_agent": "document",
            "progress": [progress_update],
            "errors": state.get("errors", []) + [str(e)],
            "context": context,
            "execution_plan": state.get("execution_plan", []),
            "current_step": state.get("current_step", 0),
            "next_agent": None
        }