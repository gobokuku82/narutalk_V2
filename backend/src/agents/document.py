"""
Enhanced Document Agent for LangGraph 0.6.6
Natural language parsing, ChromaDB integration, and auto-routing to compliance
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
    create_product_demo_report,
    create_sample_request,
    generate_business_proposal,
    generate_meeting_notes,
    generate_compliance_report,
    save_document_to_db,
    query_documents,
    update_document_status
)


def document_agent(state: AgentState) -> dict:
    """
    Enhanced Document Agent with natural language parsing and DB storage
    Following rules.md: Node functions MUST return dict
    Uses StateGraph pattern with tool integration
    Auto-routes to compliance when document is completed
    """
    # Initialize LLM with tools binding
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
    tools = [
        parse_natural_language,
        natural_language_to_document,
        create_visit_report,
        create_product_demo_request,
        create_product_demo_report,
        create_sample_request,
        generate_business_proposal,
        generate_meeting_notes,
        generate_compliance_report,
        save_document_to_db,
        query_documents,
        update_document_status
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
        "action": "processing_natural_language"
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
                result = generate_business_proposal.invoke({
                    "client_name": context.get("client_name", "Client"),
                    "product_info": context.get("product_info", "Our solutions"),
                    "pricing": context.get("pricing", "Custom pricing"),
                    "terms": context.get("terms", "Standard terms"),
                    "benefits": context.get("benefits", "Key benefits")
                })
                document_data = json.loads(result)
                
            elif "meeting" in task_description.lower() or "회의" in task_description:
                doc_type = "meeting_notes"
                result = generate_meeting_notes.invoke({
                    "meeting_title": context.get("meeting_title", "Team Meeting"),
                    "participants": context.get("participants", ["Team"]),
                    "agenda": context.get("agenda", "Discussion items"),
                    "decisions": context.get("decisions", []),
                    "action_items": context.get("action_items", [])
                })
                document_data = json.loads(result)
                
            elif "compliance" in task_description.lower() or "규정" in task_description:
                doc_type = "compliance"
                result = generate_compliance_report.invoke({
                    "document_id": context.get("document_id", "DOC001"),
                    "checks_performed": context.get("checks", ["Basic compliance"]),
                    "violations": context.get("violations", []),
                    "recommendations": context.get("recommendations", [])
                })
                document_data = json.loads(result)
                
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
        
        # Save document to database
        document_id = None
        if document_data:
            save_result = save_document_to_db.invoke({
                "document": document_data,
                "metadata": {
                    "created_by": "document_agent",
                    "task_description": task_description,
                    "timestamp": datetime.now().isoformat()
                }
            })
            save_data = json.loads(save_result)
            document_id = save_data.get("document_id")
            
            logger.info(f"Document saved with ID: {document_id}")
        
        # Format output message
        document_message = f"""
📄 **Document Generated Successfully**

Document Type: {doc_type.replace('_', ' ').title()}
Document ID: {document_id if document_data else 'N/A'}
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Storage: {'Structured (SQLite)' if document_data and document_data.get('is_structured') else 'Unstructured (JSON)'}

---

**Document Summary:**
{json.dumps(document_data, ensure_ascii=False, indent=2) if document_data else 'No document generated'}

---

{"✅ Document ready for compliance check" if doc_type in ['proposal', 'visit_report', 'product_demo_report'] else "📋 Document completed"}
"""
        
        # Update progress
        progress_update["status"] = "completed"
        progress_update["summary"] = f"Generated and saved {doc_type} document"
        progress_update["document_id"] = document_id if document_data else None
        
        # Store document in results
        results_update = state.get("results", {})
        results_update["document"] = {
            "document_id": document_id if document_data else None,
            "type": doc_type,
            "data": document_data,
            "timestamp": datetime.now().isoformat(),
            "status": "generated",
            "storage_type": "structured" if document_data and document_data.get('is_structured') else "unstructured"
        }
        
        # Update context to trigger compliance check if needed
        requires_compliance = doc_type in ['proposal', 'visit_report', 'product_demo_report', 'compliance']
        updated_context = {
            **context,
            "document_generated": True,
            "document_type": doc_type,
            "document_id": document_id if document_data else None,
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
            "next_agent": "compliance" if requires_compliance else None
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
            "context": context
        }