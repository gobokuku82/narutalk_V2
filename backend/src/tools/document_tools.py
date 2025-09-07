"""
Document Tools for LangGraph 0.6.6
Natural language to structured document conversion with templates
"""
from typing import Dict, Any, List, Optional, Literal, Tuple
import json
import sqlite3
from datetime import datetime, date
from pathlib import Path
import uuid
import re
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from loguru import logger
from pydantic import BaseModel, Field
from enum import Enum

# Document types
class DocumentType(str, Enum):
    VISIT_REPORT = "visit_report"  # 방문결과 보고서
    PRODUCT_DEMO_REQUEST = "product_demo_request"  # 제품설명회 신청서
    PRODUCT_DEMO_REPORT = "product_demo_report"  # 제품설명회 결과보고서
    SAMPLE_REQUEST = "sample_request"  # 샘플신청서
    GENERAL = "general"  # 일반 문서

# Document templates as Pydantic models for validation
class VisitReport(BaseModel):
    """방문결과 보고서 템플릿"""
    document_id: str = Field(default_factory=lambda: f"VR_{uuid.uuid4().hex[:8]}")
    document_type: Literal["visit_report"] = "visit_report"
    visit_date: str = Field(description="방문 날짜")
    company_name: str = Field(description="방문 회사명")
    visitor_name: str = Field(description="방문자 이름")
    contact_person: str = Field(description="담당자 이름")
    contact_position: str = Field(description="담당자 직책")
    visit_purpose: str = Field(description="방문 목적")
    discussion_content: str = Field(description="논의 내용")
    key_requirements: List[str] = Field(description="주요 요구사항")
    action_items: List[str] = Field(description="액션 아이템")
    next_steps: str = Field(description="향후 계획")
    attachments: List[str] = Field(default_factory=list, description="첨부 파일")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    is_structured: bool = True

class ProductDemoRequest(BaseModel):
    """제품설명회 신청서 템플릿"""
    document_id: str = Field(default_factory=lambda: f"PDR_{uuid.uuid4().hex[:8]}")
    document_type: Literal["product_demo_request"] = "product_demo_request"
    company_name: str = Field(description="신청 회사명")
    requester_name: str = Field(description="신청자 이름")
    requester_email: str = Field(description="신청자 이메일")
    requester_phone: str = Field(description="신청자 연락처")
    preferred_date: str = Field(description="희망 날짜")
    preferred_time: str = Field(description="희망 시간")
    product_interest: List[str] = Field(description="관심 제품")
    attendee_count: int = Field(description="예상 참석 인원")
    specific_requirements: str = Field(description="특별 요구사항")
    demo_location: str = Field(description="설명회 장소")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    status: str = Field(default="pending", description="신청 상태")
    is_structured: bool = True

class ProductDemoReport(BaseModel):
    """제품설명회 결과보고서 템플릿"""
    document_id: str = Field(default_factory=lambda: f"PDT_{uuid.uuid4().hex[:8]}")
    document_type: Literal["product_demo_report"] = "product_demo_report"
    demo_date: str = Field(description="설명회 날짜")
    company_name: str = Field(description="참석 회사명")
    presenter_name: str = Field(description="발표자 이름")
    attendee_list: List[Dict[str, str]] = Field(description="참석자 명단")
    products_presented: List[str] = Field(description="발표 제품")
    demo_duration: str = Field(description="설명회 시간")
    key_questions: List[str] = Field(description="주요 질문사항")
    feedback_summary: str = Field(description="피드백 요약")
    interest_level: str = Field(description="관심도 (high/medium/low)")
    follow_up_actions: List[str] = Field(description="후속 조치")
    potential_opportunity: str = Field(description="잠재 기회")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    is_structured: bool = True

class SampleRequest(BaseModel):
    """샘플신청서 템플릿"""
    document_id: str = Field(default_factory=lambda: f"SR_{uuid.uuid4().hex[:8]}")
    document_type: Literal["sample_request"] = "sample_request"
    company_name: str = Field(description="신청 회사명")
    requester_name: str = Field(description="신청자 이름")
    requester_department: str = Field(description="신청자 부서")
    requester_email: str = Field(description="신청자 이메일")
    requester_phone: str = Field(description="신청자 연락처")
    product_name: str = Field(description="샘플 제품명")
    quantity: int = Field(description="수량")
    purpose: str = Field(description="사용 목적")
    evaluation_period: str = Field(description="평가 기간")
    delivery_address: str = Field(description="배송 주소")
    special_notes: str = Field(default="", description="특별 사항")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    status: str = Field(default="pending", description="신청 상태")
    is_structured: bool = True

class GeneralDocument(BaseModel):
    """일반 문서 템플릿 (비정형)"""
    document_id: str = Field(default_factory=lambda: f"GD_{uuid.uuid4().hex[:8]}")
    document_type: Literal["general"] = "general"
    title: str = Field(description="문서 제목")
    content: str = Field(description="문서 내용")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="메타데이터")
    tags: List[str] = Field(default_factory=list, description="태그")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    is_structured: bool = False


# Database manager for documents
class DocumentDB:
    """Document database manager with dynamic storage"""
    
    def __init__(self):
        """Initialize document database"""
        db_path = Path(__file__).parent.parent.parent / "data" / "documents.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        
        logger.info(f"Document database initialized at {db_path}")
    
    def _create_tables(self):
        """Create document tables for structured and unstructured data"""
        cursor = self.conn.cursor()
        
        # Structured documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS structured_documents (
                document_id TEXT PRIMARY KEY,
                document_type TEXT NOT NULL,
                data JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Unstructured documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS unstructured_documents (
                document_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata JSON,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Document index for search
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_structured_type 
            ON structured_documents(document_type)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_unstructured_title 
            ON unstructured_documents(title)
        """)
        
        self.conn.commit()
    
    def save_document(self, document: Dict[str, Any], is_structured: bool) -> str:
        """Save document to appropriate table based on structure"""
        cursor = self.conn.cursor()
        
        try:
            if is_structured:
                # Save to structured table
                cursor.execute("""
                    INSERT OR REPLACE INTO structured_documents 
                    (document_id, document_type, data, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    document["document_id"],
                    document["document_type"],
                    json.dumps(document, ensure_ascii=False),
                    document.get("created_at", datetime.now().isoformat()),
                    datetime.now().isoformat()
                ))
            else:
                # Save to unstructured table
                cursor.execute("""
                    INSERT OR REPLACE INTO unstructured_documents 
                    (document_id, title, content, metadata, tags, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    document["document_id"],
                    document.get("title", "Untitled"),
                    document.get("content", ""),
                    json.dumps(document.get("metadata", {}), ensure_ascii=False),
                    json.dumps(document.get("tags", []), ensure_ascii=False),
                    document.get("created_at", datetime.now().isoformat()),
                    datetime.now().isoformat()
                ))
            
            self.conn.commit()
            logger.info(f"Document saved: {document['document_id']} (structured={is_structured})")
            return document["document_id"]
            
        except Exception as e:
            logger.error(f"Error saving document: {e}")
            self.conn.rollback()
            raise
    
    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve document by ID"""
        cursor = self.conn.cursor()
        
        # Try structured documents first
        cursor.execute("""
            SELECT * FROM structured_documents WHERE document_id = ?
        """, (document_id,))
        
        row = cursor.fetchone()
        if row:
            return json.loads(row["data"])
        
        # Try unstructured documents
        cursor.execute("""
            SELECT * FROM unstructured_documents WHERE document_id = ?
        """, (document_id,))
        
        row = cursor.fetchone()
        if row:
            return {
                "document_id": row["document_id"],
                "title": row["title"],
                "content": row["content"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                "tags": json.loads(row["tags"]) if row["tags"] else [],
                "created_at": row["created_at"],
                "is_structured": False
            }
        
        return None


# Initialize database
doc_db = DocumentDB()


@tool
def parse_natural_language(text: str) -> str:
    """
    Parse natural language input to identify document type and extract information
    
    Args:
        text: Natural language description of document
    
    Returns:
        JSON string with parsed information
    """
    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
        parse_prompt = f"""
        Analyze this natural language text and extract document information:
        
        "{text}"
        
        Identify:
        1. Document type (visit_report, product_demo_request, product_demo_report, sample_request, or general)
        2. Key entities (company names, people, dates, products)
        3. Main purpose or action
        4. Any specific requirements or details
        
        Return as JSON with:
        - document_type: identified type
        - entities: extracted entities
        - purpose: main purpose
        - details: other relevant details
        """
        
        response = llm.invoke([
            SystemMessage(content="You are a document parsing expert. Extract structured information from natural language."),
            HumanMessage(content=parse_prompt)
        ])
        
        # Simple parsing of response
        parsed = {
            "document_type": "general",
            "entities": {},
            "purpose": "",
            "details": {}
        }
        
        # Keyword-based document type detection
        text_lower = text.lower()
        if "방문" in text_lower or "visit" in text_lower:
            parsed["document_type"] = "visit_report"
        elif "제품설명회 신청" in text_lower or "데모 신청" in text_lower:
            parsed["document_type"] = "product_demo_request"
        elif "제품설명회 결과" in text_lower or "데모 결과" in text_lower:
            parsed["document_type"] = "product_demo_report"
        elif "샘플" in text_lower or "sample" in text_lower:
            parsed["document_type"] = "sample_request"
        
        # Extract entities using regex patterns
        # Company names (한글 회사명 패턴)
        company_pattern = r'([가-힣]+(?:전자|화학|중공업|건설|물산|상사|엔지니어링|테크|소프트|시스템|네트웍스|텔레콤|모바일|반도체|디스플레이|바이오|제약|화장품|식품|유통|백화점|마트|은행|증권|보험|카드|캐피탈|자산운용|투자|종합금융|저축은행|새마을금고|신협|농협|수협|산림조합|신용협동조합))'
        companies = re.findall(company_pattern, text)
        if companies:
            parsed["entities"]["companies"] = companies
        
        # Dates (YYYY-MM-DD, YYYY년 MM월 DD일, MM/DD)
        date_pattern = r'(\d{4}[-년]\d{1,2}[-월]\d{1,2}일?|\d{1,2}/\d{1,2})'
        dates = re.findall(date_pattern, text)
        if dates:
            parsed["entities"]["dates"] = dates
        
        # Extract names (한글 이름 패턴)
        name_pattern = r'([가-힣]{2,4}(?:님|씨|과장|대리|부장|이사|상무|전무|사장|대표))'
        names = re.findall(name_pattern, text)
        if names:
            parsed["entities"]["names"] = names
        
        # Extract the purpose (first sentence or main verb)
        sentences = text.split('.')
        if sentences:
            parsed["purpose"] = sentences[0].strip()
        
        # Store full text as details
        parsed["details"]["full_text"] = text
        parsed["raw_content"] = response.content
        
        logger.info(f"Parsed document type: {parsed['document_type']}")
        
        return json.dumps(parsed, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Error parsing natural language: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool
def create_visit_report(data: Dict[str, Any]) -> str:
    """
    Create a visit report document
    
    Args:
        data: Dictionary containing visit report information
    
    Returns:
        JSON string with created document
    """
    try:
        # Create VisitReport model
        report = VisitReport(
            visit_date=data.get("visit_date", datetime.now().strftime("%Y-%m-%d")),
            company_name=data.get("company_name", "Unknown Company"),
            visitor_name=data.get("visitor_name", "Unknown Visitor"),
            contact_person=data.get("contact_person", "Unknown Contact"),
            contact_position=data.get("contact_position", "Unknown Position"),
            visit_purpose=data.get("visit_purpose", "Business meeting"),
            discussion_content=data.get("discussion_content", ""),
            key_requirements=data.get("key_requirements", []),
            action_items=data.get("action_items", []),
            next_steps=data.get("next_steps", "To be determined"),
            attachments=data.get("attachments", [])
        )
        
        # Save to database
        doc_dict = report.dict()
        doc_id = doc_db.save_document(doc_dict, is_structured=True)
        
        logger.info(f"Created visit report: {doc_id}")
        
        return json.dumps({
            "status": "success",
            "document_id": doc_id,
            "document_type": "visit_report",
            "document": doc_dict
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Error creating visit report: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool
def create_product_demo_request(data: Dict[str, Any]) -> str:
    """
    Create a product demo request document
    
    Args:
        data: Dictionary containing demo request information
    
    Returns:
        JSON string with created document
    """
    try:
        # Create ProductDemoRequest model
        request = ProductDemoRequest(
            company_name=data.get("company_name", "Unknown Company"),
            requester_name=data.get("requester_name", "Unknown Requester"),
            requester_email=data.get("requester_email", "unknown@example.com"),
            requester_phone=data.get("requester_phone", "000-0000-0000"),
            preferred_date=data.get("preferred_date", "To be scheduled"),
            preferred_time=data.get("preferred_time", "To be scheduled"),
            product_interest=data.get("product_interest", []),
            attendee_count=data.get("attendee_count", 1),
            specific_requirements=data.get("specific_requirements", "None"),
            demo_location=data.get("demo_location", "To be determined")
        )
        
        # Save to database
        doc_dict = request.dict()
        doc_id = doc_db.save_document(doc_dict, is_structured=True)
        
        logger.info(f"Created product demo request: {doc_id}")
        
        return json.dumps({
            "status": "success",
            "document_id": doc_id,
            "document_type": "product_demo_request",
            "document": doc_dict
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Error creating demo request: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool
def create_sample_request(data: Dict[str, Any]) -> str:
    """
    Create a sample request document
    
    Args:
        data: Dictionary containing sample request information
    
    Returns:
        JSON string with created document
    """
    try:
        # Create SampleRequest model
        request = SampleRequest(
            company_name=data.get("company_name", "Unknown Company"),
            requester_name=data.get("requester_name", "Unknown Requester"),
            requester_department=data.get("requester_department", "Unknown Department"),
            requester_email=data.get("requester_email", "unknown@example.com"),
            requester_phone=data.get("requester_phone", "000-0000-0000"),
            product_name=data.get("product_name", "Unknown Product"),
            quantity=data.get("quantity", 1),
            purpose=data.get("purpose", "Evaluation"),
            evaluation_period=data.get("evaluation_period", "30 days"),
            delivery_address=data.get("delivery_address", "To be provided"),
            special_notes=data.get("special_notes", "")
        )
        
        # Save to database
        doc_dict = request.dict()
        doc_id = doc_db.save_document(doc_dict, is_structured=True)
        
        logger.info(f"Created sample request: {doc_id}")
        
        return json.dumps({
            "status": "success",
            "document_id": doc_id,
            "document_type": "sample_request",
            "document": doc_dict
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Error creating sample request: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool
def create_general_document(title: str, content: str, metadata: Dict[str, Any] = None) -> str:
    """
    Create a general unstructured document
    
    Args:
        title: Document title
        content: Document content
        metadata: Additional metadata
    
    Returns:
        JSON string with created document
    """
    try:
        # Create GeneralDocument model
        document = GeneralDocument(
            title=title,
            content=content,
            metadata=metadata or {},
            tags=metadata.get("tags", []) if metadata else []
        )
        
        # Save to database
        doc_dict = document.dict()
        doc_id = doc_db.save_document(doc_dict, is_structured=False)
        
        logger.info(f"Created general document: {doc_id}")
        
        return json.dumps({
            "status": "success",
            "document_id": doc_id,
            "document_type": "general",
            "document": doc_dict
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Error creating general document: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool
def natural_language_to_document(text: str) -> str:
    """
    Convert natural language input to structured document
    
    Args:
        text: Natural language description
    
    Returns:
        JSON string with created document
    """
    try:
        # Parse natural language
        parsed_result = parse_natural_language.invoke({"text": text})
        parsed = json.loads(parsed_result)
        
        if "error" in parsed:
            return json.dumps(parsed, ensure_ascii=False)
        
        document_type = parsed.get("document_type", "general")
        entities = parsed.get("entities", {})
        
        # Use LLM to extract structured data
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
        extraction_prompt = f"""
        Convert this natural language text into a structured document:
        
        Text: "{text}"
        
        Document Type: {document_type}
        Extracted Entities: {json.dumps(entities, ensure_ascii=False)}
        
        Based on the document type, extract all relevant fields.
        For missing information, use reasonable defaults.
        Return as JSON matching the document template.
        """
        
        response = llm.invoke([
            SystemMessage(content=f"You are a document creation expert. Create a {document_type} document from the given information."),
            HumanMessage(content=extraction_prompt)
        ])
        
        # Parse response and create appropriate document
        try:
            # Extract JSON from response
            response_text = response.content
            # Find JSON in response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                extracted_data = json.loads(response_text[json_start:json_end])
            else:
                extracted_data = {}
        except:
            extracted_data = {}
        
        # Add entities to extracted data
        if entities.get("companies"):
            extracted_data["company_name"] = entities["companies"][0]
        if entities.get("dates"):
            extracted_data["visit_date"] = entities["dates"][0]
            extracted_data["preferred_date"] = entities["dates"][0]
        if entities.get("names"):
            extracted_data["contact_person"] = entities["names"][0]
            extracted_data["requester_name"] = entities["names"][0]
        
        # Create document based on type
        if document_type == "visit_report":
            result = create_visit_report.invoke(extracted_data)
        elif document_type == "product_demo_request":
            result = create_product_demo_request.invoke(extracted_data)
        elif document_type == "sample_request":
            result = create_sample_request.invoke(extracted_data)
        else:
            # Create general document
            result = create_general_document.invoke({
                "title": parsed.get("purpose", "General Document"),
                "content": text,
                "metadata": {
                    "parsed_entities": entities,
                    "original_text": text
                }
            })
        
        # Add parsing info to result
        result_data = json.loads(result)
        result_data["parsing_info"] = {
            "detected_type": document_type,
            "extracted_entities": entities,
            "purpose": parsed.get("purpose", "")
        }
        
        logger.info(f"Converted natural language to {document_type} document")
        
        return json.dumps(result_data, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Error converting natural language to document: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool
def determine_document_structure(document: Dict[str, Any]) -> str:
    """
    Determine if a document is structured or unstructured
    
    Args:
        document: Document dictionary
    
    Returns:
        JSON string with structure determination
    """
    try:
        # Check for structured document indicators
        structured_types = ["visit_report", "product_demo_request", "product_demo_report", "sample_request"]
        document_type = document.get("document_type", "")
        
        is_structured = False
        confidence = 0.0
        reasons = []
        
        # Check document type
        if document_type in structured_types:
            is_structured = True
            confidence += 0.5
            reasons.append(f"Document type '{document_type}' is a structured template")
        
        # Check for required fields based on type
        required_fields = {
            "visit_report": ["visit_date", "company_name", "visitor_name", "discussion_content"],
            "product_demo_request": ["company_name", "requester_name", "product_interest"],
            "product_demo_report": ["demo_date", "company_name", "products_presented"],
            "sample_request": ["company_name", "product_name", "quantity"]
        }
        
        if document_type in required_fields:
            fields = required_fields[document_type]
            present_fields = sum(1 for field in fields if field in document)
            field_ratio = present_fields / len(fields)
            confidence += field_ratio * 0.5
            
            if field_ratio >= 0.7:
                is_structured = True
                reasons.append(f"Has {present_fields}/{len(fields)} required fields")
            else:
                is_structured = False
                reasons.append(f"Missing required fields ({present_fields}/{len(fields)})")
        
        # Check for explicit structure flag
        if "is_structured" in document:
            is_structured = document["is_structured"]
            confidence = 1.0
            reasons.append("Explicit structure flag present")
        
        result = {
            "is_structured": is_structured,
            "confidence": confidence,
            "reasons": reasons,
            "recommended_storage": "structured_documents" if is_structured else "unstructured_documents",
            "document_type": document_type
        }
        
        logger.info(f"Document structure determination: {is_structured} (confidence: {confidence})")
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Error determining document structure: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool
def retrieve_document(document_id: str) -> str:
    """
    Retrieve a document from the database
    
    Args:
        document_id: Document ID
    
    Returns:
        JSON string with document data
    """
    try:
        document = doc_db.get_document(document_id)
        
        if document:
            return json.dumps({
                "status": "success",
                "document": document
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "status": "not_found",
                "error": f"Document {document_id} not found"
            }, ensure_ascii=False)
            
    except Exception as e:
        logger.error(f"Error retrieving document: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool
def prepare_compliance_check(document: Dict[str, Any]) -> str:
    """
    Prepare document for compliance check
    
    Args:
        document: Document to prepare for compliance
    
    Returns:
        JSON string with compliance preparation
    """
    try:
        compliance_data = {
            "document_id": document.get("document_id", ""),
            "document_type": document.get("document_type", ""),
            "requires_compliance": False,
            "compliance_checks": [],
            "sensitive_data": [],
            "recommended_actions": []
        }
        
        # Determine compliance requirements based on document type
        doc_type = document.get("document_type", "")
        
        # All structured documents should go through compliance
        if doc_type in ["visit_report", "product_demo_request", "product_demo_report", "sample_request"]:
            compliance_data["requires_compliance"] = True
            compliance_data["compliance_checks"].append("document_completeness")
            compliance_data["compliance_checks"].append("data_privacy")
        
        # Check for sensitive data patterns
        doc_str = json.dumps(document, ensure_ascii=False)
        
        # Phone numbers
        if re.search(r'\d{3}-\d{4}-\d{4}', doc_str):
            compliance_data["sensitive_data"].append("phone_numbers")
            compliance_data["compliance_checks"].append("personal_data_protection")
        
        # Email addresses
        if re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', doc_str):
            compliance_data["sensitive_data"].append("email_addresses")
            compliance_data["compliance_checks"].append("personal_data_protection")
        
        # Company confidential information
        if any(keyword in doc_str.lower() for keyword in ["confidential", "기밀", "secret", "내부용"]):
            compliance_data["sensitive_data"].append("confidential_information")
            compliance_data["compliance_checks"].append("confidentiality_agreement")
        
        # Add recommendations
        if compliance_data["sensitive_data"]:
            compliance_data["recommended_actions"].append("Review and redact sensitive information")
            compliance_data["recommended_actions"].append("Ensure proper data handling procedures")
        
        if doc_type == "sample_request":
            compliance_data["recommended_actions"].append("Verify product availability")
            compliance_data["recommended_actions"].append("Check export regulations if applicable")
        
        compliance_data["auto_route_to_compliance"] = compliance_data["requires_compliance"]
        
        logger.info(f"Prepared document for compliance: requires={compliance_data['requires_compliance']}")
        
        return json.dumps(compliance_data, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Error preparing compliance check: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)