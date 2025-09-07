"""
Test cases for Enhanced Document Agent with Natural Language Processing
Testing document generation, storage, and auto-routing to compliance
"""
import pytest
import json
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage
from src.state.agent_state import AgentState
from src.agents.document import document_agent
from src.tools.document_tools import (
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
    update_document_status,
    DocumentDB
)


class TestDocumentTools:
    """Test suite for document tools"""
    
    @pytest.fixture
    def document_db(self):
        """Create a test document database instance"""
        return DocumentDB()
    
    def test_parse_natural_language_korean(self):
        """Test parsing Korean natural language"""
        result = parse_natural_language.invoke({
            "text": "오늘 삼성전자 김부장님과 AI 솔루션 데모 진행했습니다. 참석자는 김부장, 이과장이었고 가격은 월 300만원으로 논의했습니다."
        })
        data = json.loads(result)
        
        assert "document_type" in data
        assert "parsed_info" in data
        assert data["document_type"] in ["visit_report", "product_demo_report"]
        assert "entities" in data["parsed_info"]
        
    def test_parse_natural_language_english(self):
        """Test parsing English natural language"""
        result = parse_natural_language.invoke({
            "text": "Met with Samsung Electronics today for AI solution demo. Discussed pricing at $3000/month with Mr. Kim and Ms. Lee."
        })
        data = json.loads(result)
        
        assert "document_type" in data
        assert data["document_type"] in ["visit_report", "product_demo_report"]
        
    def test_create_visit_report(self):
        """Test visit report creation"""
        result = create_visit_report.invoke({
            "client_name": "Samsung Electronics",
            "visit_date": "2024-01-15",
            "participants": ["김부장", "이과장", "Sales Team"],
            "discussion_points": ["AI Solution Demo", "Pricing Discussion", "Implementation Timeline"],
            "action_items": ["Send proposal", "Schedule follow-up"],
            "next_steps": "Contract negotiation next week"
        })
        data = json.loads(result)
        
        assert data["document_type"] == "visit_report"
        assert data["is_structured"] == True
        assert "content" in data
        assert data["content"]["client_name"] == "Samsung Electronics"
        assert len(data["content"]["participants"]) == 3
        
    def test_create_product_demo_request(self):
        """Test product demo request creation"""
        result = create_product_demo_request.invoke({
            "client_name": "LG Electronics",
            "product_name": "AI Sales Assistant",
            "requested_date": "2024-01-20",
            "participants": ["Product Manager", "Tech Lead"],
            "demo_requirements": ["Live demonstration", "Q&A session", "Technical architecture"]
        })
        data = json.loads(result)
        
        assert data["document_type"] == "product_demo_request"
        assert data["content"]["product_name"] == "AI Sales Assistant"
        assert "demo_requirements" in data["content"]
        
    def test_create_product_demo_report(self):
        """Test product demo report creation"""
        result = create_product_demo_report.invoke({
            "client_name": "Hyundai Motors",
            "product_name": "Analytics Platform",
            "demo_date": "2024-01-10",
            "participants": ["CTO", "Data Team"],
            "demo_highlights": ["Real-time analytics", "Custom dashboards"],
            "client_feedback": ["Impressed with performance", "Need more customization"],
            "follow_up_actions": ["Provide customization options", "Send pricing"]
        })
        data = json.loads(result)
        
        assert data["document_type"] == "product_demo_report"
        assert "client_feedback" in data["content"]
        assert len(data["content"]["client_feedback"]) == 2
        
    def test_create_sample_request(self):
        """Test sample request creation"""
        result = create_sample_request.invoke({
            "client_name": "SK Telecom",
            "product_name": "Cloud Solution",
            "requested_date": "2024-01-25",
            "sample_type": "Trial License",
            "duration": "30 days",
            "requirements": ["Full feature access", "Technical support"]
        })
        data = json.loads(result)
        
        assert data["document_type"] == "sample_request"
        assert data["content"]["sample_type"] == "Trial License"
        assert data["content"]["duration"] == "30 days"
        
    def test_generate_business_proposal(self):
        """Test business proposal generation"""
        result = generate_business_proposal.invoke({
            "client_name": "Samsung Electronics",
            "product_info": "AI-powered sales automation platform",
            "pricing": "$5000/month for enterprise license",
            "terms": "Annual contract with quarterly payments",
            "benefits": "30% increase in sales efficiency, 20% cost reduction"
        })
        data = json.loads(result)
        
        assert data["document_type"] == "business_proposal"
        assert data["is_structured"] == False  # Proposals are unstructured
        assert "proposal_sections" in data
        assert "executive_summary" in data["proposal_sections"]
        
    def test_generate_meeting_notes(self):
        """Test meeting notes generation"""
        result = generate_meeting_notes.invoke({
            "meeting_title": "Q1 Sales Strategy Meeting",
            "participants": ["Sales Director", "Regional Managers", "Product Team"],
            "agenda": "Q1 targets, New product launch, Territory planning",
            "decisions": ["Launch in March", "Focus on enterprise clients"],
            "action_items": ["Prepare launch materials", "Update CRM", "Train sales team"]
        })
        data = json.loads(result)
        
        assert data["document_type"] == "meeting_notes"
        assert "formatted_notes" in data
        assert len(data["action_items"]) == 3
        
    def test_generate_compliance_report(self):
        """Test compliance report generation"""
        result = generate_compliance_report.invoke({
            "document_id": "DOC-2024-001",
            "checks_performed": ["Data privacy", "Contract terms", "Pricing compliance"],
            "violations": [],
            "recommendations": ["Add GDPR clause", "Update payment terms"]
        })
        data = json.loads(result)
        
        assert data["document_type"] == "compliance_report"
        assert data["compliance_status"] == "PASSED"
        assert len(data["checks_performed"]) == 3
        assert len(data["violations"]) == 0
        
    def test_save_and_query_documents(self, document_db):
        """Test document storage and retrieval"""
        # Create a test document
        test_doc = {
            "document_type": "visit_report",
            "is_structured": True,
            "content": {
                "client_name": "Test Corp",
                "visit_date": "2024-01-15",
                "participants": ["Test User"]
            }
        }
        
        # Save document
        save_result = save_document_to_db.invoke({
            "document": test_doc,
            "metadata": {"created_by": "test"}
        })
        save_data = json.loads(save_result)
        
        assert "document_id" in save_data
        assert save_data["storage_type"] == "structured"
        
        # Query documents
        query_result = query_documents.invoke({
            "query": "Test Corp",
            "document_type": "visit_report"
        })
        query_data = json.loads(query_result)
        
        assert query_data["count"] > 0
        assert "results" in query_data
        
    def test_update_document_status(self, document_db):
        """Test document status update"""
        # First create a document
        test_doc = {
            "document_type": "sample_request",
            "is_structured": True,
            "content": {"client_name": "Status Test Corp"}
        }
        
        save_result = save_document_to_db.invoke({
            "document": test_doc,
            "metadata": {}
        })
        doc_id = json.loads(save_result)["document_id"]
        
        # Update status
        update_result = update_document_status.invoke({
            "document_id": doc_id,
            "new_status": "approved",
            "notes": "Approved by manager"
        })
        update_data = json.loads(update_result)
        
        assert update_data["success"] == True
        assert update_data["new_status"] == "approved"
        
    def test_natural_language_to_document(self):
        """Test end-to-end natural language to document conversion"""
        result = natural_language_to_document.invoke({
            "text": "삼성전자 김부장님께 AI 솔루션 제안서를 작성해주세요. 월 500만원, 연간 계약 조건입니다."
        })
        data = json.loads(result)
        
        assert "document_type" in data
        assert data["document_type"] == "business_proposal"
        assert "document_id" in data
        assert data["saved"] == True


class TestDocumentAgent:
    """Test suite for the enhanced document agent"""
    
    def test_document_agent_natural_language(self):
        """Test document agent with natural language input"""
        state = {
            "messages": [HumanMessage(content="오늘 삼성전자 방문 보고서 작성해줘. 김부장님과 AI 솔루션 논의했고 다음주 계약 예정")],
            "current_agent": "document",
            "task_type": "document",
            "task_description": "오늘 삼성전자 방문 보고서 작성해줘. 김부장님과 AI 솔루션 논의했고 다음주 계약 예정",
            "progress": [],
            "context": {},
            "metadata": {},
            "results": {},
            "errors": [],
            "is_complete": False
        }
        
        result = document_agent(state)
        
        # Check result structure
        assert result is not None
        assert "messages" in result
        assert len(result["messages"]) > 0
        assert "results" in result
        assert "document" in result["results"]
        
        # Check document was created
        doc_result = result["results"]["document"]
        assert doc_result["type"] in ["visit_report", "product_demo_report"]
        assert doc_result["status"] == "generated"
        assert "document_id" in doc_result
        
        # Check auto-routing signal
        assert "next_agent" in result
        if doc_result["type"] in ["visit_report", "product_demo_report"]:
            assert result["next_agent"] == "compliance"
    
    def test_document_agent_proposal_generation(self):
        """Test document agent for proposal generation"""
        state = {
            "messages": [HumanMessage(content="Generate a business proposal for LG Electronics")],
            "current_agent": "document",
            "task_type": "document",
            "task_description": "Generate a business proposal for LG Electronics",
            "progress": [],
            "context": {
                "client_name": "LG Electronics",
                "product_info": "AI Analytics Platform",
                "pricing": "$10,000/month",
                "terms": "2-year contract"
            },
            "metadata": {},
            "results": {},
            "errors": [],
            "is_complete": False
        }
        
        result = document_agent(state)
        
        # Check proposal was generated
        assert "document" in result["results"]
        doc_result = result["results"]["document"]
        assert doc_result["type"] == "proposal"
        assert doc_result["data"]["document_type"] == "business_proposal"
        
        # Check compliance routing
        assert result["context"]["requires_compliance_check"] == True
        assert result["next_agent"] == "compliance"
    
    def test_document_agent_meeting_notes(self):
        """Test document agent for meeting notes"""
        state = {
            "messages": [HumanMessage(content="Create meeting notes for today's sales meeting")],
            "current_agent": "document",
            "task_type": "document",
            "task_description": "Create meeting notes for today's sales meeting",
            "progress": [],
            "context": {
                "meeting_title": "Q1 Sales Review",
                "participants": ["Sales Team", "Management"],
                "agenda": "Review Q1 performance",
                "decisions": ["Increase marketing budget", "Hire 2 new sales reps"],
                "action_items": ["Update forecasts", "Post job listings"]
            },
            "metadata": {},
            "results": {},
            "errors": [],
            "is_complete": False
        }
        
        result = document_agent(state)
        
        # Check meeting notes were created
        assert "document" in result["results"]
        doc_result = result["results"]["document"]
        assert doc_result["type"] == "meeting_notes"
        
        # Meeting notes don't require compliance
        assert result["context"]["requires_compliance_check"] == False
        assert result.get("next_agent") is None
    
    def test_document_agent_compliance_report(self):
        """Test document agent for compliance report"""
        state = {
            "messages": [HumanMessage(content="Generate compliance report for document DOC-001")],
            "current_agent": "document",
            "task_type": "document",
            "task_description": "Generate compliance report for document DOC-001",
            "progress": [],
            "context": {
                "document_id": "DOC-001",
                "checks": ["GDPR compliance", "Contract terms", "Pricing guidelines"],
                "violations": [],
                "recommendations": ["Update privacy policy section"]
            },
            "metadata": {},
            "results": {},
            "errors": [],
            "is_complete": False
        }
        
        result = document_agent(state)
        
        # Check compliance report was created
        assert "document" in result["results"]
        doc_result = result["results"]["document"]
        assert doc_result["type"] == "compliance"
        
        # Compliance reports trigger compliance check
        assert result["context"]["requires_compliance_check"] == True
    
    def test_document_agent_error_handling(self):
        """Test document agent error handling"""
        state = {
            "messages": [],  # Empty messages might cause issues
            "current_agent": "document",
            "task_type": "document",
            "task_description": "",  # Empty task
            "progress": [],
            "context": {},
            "metadata": {},
            "results": {},
            "errors": [],
            "is_complete": False
        }
        
        result = document_agent(state)
        
        # Should still return a valid result
        assert result is not None
        assert "messages" in result
        assert "current_agent" in result
    
    def test_document_agent_context_preservation(self):
        """Test that document agent preserves and updates context"""
        state = {
            "messages": [HumanMessage(content="Create a visit report")],
            "current_agent": "document",
            "task_type": "document",
            "task_description": "Create a visit report",
            "progress": [
                {"agent": "supervisor", "timestamp": "2024-01-01T00:00:00", "action": "routing"}
            ],
            "context": {
                "client_name": "Test Corp",
                "priority": "high",
                "existing_data": "preserve"
            },
            "metadata": {"thread_id": "test_thread"},
            "results": {},
            "errors": [],
            "is_complete": False
        }
        
        result = document_agent(state)
        
        # Check context preservation
        assert "context" in result
        assert result["context"]["client_name"] == "Test Corp"
        assert result["context"]["priority"] == "high"
        assert result["context"]["existing_data"] == "preserve"
        
        # Check context updates
        assert result["context"]["document_generated"] == True
        assert "document_type" in result["context"]
        assert "document_id" in result["context"]


class TestDocumentDB:
    """Test DocumentDB storage functionality"""
    
    def test_structured_vs_unstructured_storage(self):
        """Test that documents are stored correctly based on structure"""
        db = DocumentDB()
        
        # Structured document (visit report)
        structured_doc = {
            "document_type": "visit_report",
            "is_structured": True,
            "content": {
                "client_name": "Structured Corp",
                "visit_date": "2024-01-15"
            }
        }
        
        doc_id_1 = db.save_document(structured_doc, {"test": "structured"})
        assert doc_id_1.startswith("DOC-")
        
        # Unstructured document (proposal)
        unstructured_doc = {
            "document_type": "business_proposal",
            "is_structured": False,
            "proposal_sections": {
                "executive_summary": "Test proposal"
            }
        }
        
        doc_id_2 = db.save_document(unstructured_doc, {"test": "unstructured"})
        assert doc_id_2.startswith("DOC-")
        assert doc_id_1 != doc_id_2
    
    def test_document_retrieval(self):
        """Test document retrieval from database"""
        db = DocumentDB()
        
        # Save test document
        test_doc = {
            "document_type": "sample_request",
            "is_structured": True,
            "content": {
                "client_name": "Retrieval Test Corp",
                "product_name": "Test Product"
            }
        }
        
        doc_id = db.save_document(test_doc, {})
        
        # Retrieve by ID
        retrieved = db.get_document(doc_id)
        assert retrieved is not None
        assert retrieved["document_type"] == "sample_request"
        
    def test_document_search(self):
        """Test document search functionality"""
        db = DocumentDB()
        
        # Save multiple documents
        for i in range(3):
            doc = {
                "document_type": "visit_report",
                "is_structured": True,
                "content": {
                    "client_name": f"Search Test Corp {i}",
                    "visit_date": f"2024-01-{10+i}"
                }
            }
            db.save_document(doc, {})
        
        # Search documents
        results = db.search_documents("Search Test Corp", "visit_report")
        assert len(results) >= 3


@pytest.mark.asyncio
class TestDocumentIntegration:
    """Integration tests for document with StateGraph"""
    
    async def test_document_in_graph_flow(self):
        """Test document agent within the graph flow"""
        from src.core.graph import SalesSupportApp
        
        app = SalesSupportApp(use_sqlite=False)
        
        # Request document generation
        result = await app.aprocess_request(
            user_input="Create a visit report for Samsung Electronics meeting today",
            thread_id="test_doc_1"
        )
        
        # Check that document was involved
        progress = result.get("progress", [])
        agents = [p.get("agent") for p in progress]
        
        assert "supervisor" in agents or "document" in agents
        
        # Check results if document was executed
        if "document" in result.get("results", {}):
            doc_results = result["results"]["document"]
            assert doc_results["status"] == "generated"
            assert "document_id" in doc_results
    
    async def test_document_to_compliance_routing(self):
        """Test auto-routing from document to compliance"""
        from src.core.graph import SalesSupportApp
        
        app = SalesSupportApp(use_sqlite=False)
        
        # Request that should trigger compliance
        result = await app.aprocess_request(
            user_input="Generate a business proposal for LG Electronics with pricing",
            thread_id="test_doc_compliance"
        )
        
        # Check routing path
        progress = result.get("progress", [])
        agents = [p.get("agent") for p in progress]
        
        # Should have document followed by compliance
        if "document" in agents:
            doc_index = agents.index("document")
            # Check if compliance comes after document
            if doc_index < len(agents) - 1:
                assert "compliance" in agents[doc_index:]