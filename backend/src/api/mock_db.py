"""
Mock Database API for development and testing
Simulates database operations without actual DB connection
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json
import uuid
from loguru import logger
import random

router = APIRouter()

# In-memory mock database
mock_database = {
    "customers": {},
    "products": {},
    "sales": {},
    "analytics": {},
    "documents": {},
    "compliance_records": {}
}

# Models
class Customer(BaseModel):
    id: Optional[str] = None
    name: str
    company: str
    industry: str
    email: str
    phone: Optional[str] = None
    annual_revenue: Optional[str] = None
    employee_count: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    tags: List[str] = []
    metadata: Dict[str, Any] = {}


class Product(BaseModel):
    id: Optional[str] = None
    name: str
    category: str
    price: float
    currency: str = "KRW"
    description: Optional[str] = None
    features: List[str] = []
    stock: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Sale(BaseModel):
    id: Optional[str] = None
    customer_id: str
    product_id: str
    quantity: int
    total_amount: float
    currency: str = "KRW"
    status: str = "pending"  # pending, completed, cancelled
    sale_date: Optional[datetime] = None
    notes: Optional[str] = None


class Analytics(BaseModel):
    id: Optional[str] = None
    type: str  # revenue, growth, conversion, etc.
    period: str  # daily, weekly, monthly, quarterly
    metrics: Dict[str, Any]
    generated_at: Optional[datetime] = None


class Document(BaseModel):
    id: Optional[str] = None
    type: str  # proposal, report, contract, etc.
    title: str
    content: str
    customer_id: Optional[str] = None
    created_by: str = "AI Assistant"
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = {}


class ComplianceRecord(BaseModel):
    id: Optional[str] = None
    type: str  # privacy, regulatory, contract, etc.
    status: str  # compliant, non_compliant, review_required
    details: Dict[str, Any]
    checked_at: Optional[datetime] = None
    recommendations: List[str] = []


# Initialize with seed data
def initialize_mock_data():
    """Initialize mock database with sample data"""
    if mock_database["customers"]:
        return  # Already initialized
    
    # Sample customers
    sample_customers = [
        {
            "id": "cust_001",
            "name": "김철수",
            "company": "Samsung Electronics",
            "industry": "Technology",
            "email": "kim.cs@samsung.com",
            "phone": "010-1234-5678",
            "annual_revenue": "₩300 trillion",
            "employee_count": 280000,
            "tags": ["enterprise", "vip", "technology"],
            "metadata": {"region": "Korea", "tier": "platinum"}
        },
        {
            "id": "cust_002",
            "name": "이영희",
            "company": "LG Chem",
            "industry": "Chemical",
            "email": "lee.yh@lgchem.com",
            "phone": "010-2345-6789",
            "annual_revenue": "₩50 trillion",
            "employee_count": 45000,
            "tags": ["enterprise", "chemical"],
            "metadata": {"region": "Korea", "tier": "gold"}
        },
        {
            "id": "cust_003",
            "name": "박민수",
            "company": "Hyundai Motor",
            "industry": "Automotive",
            "email": "park.ms@hyundai.com",
            "phone": "010-3456-7890",
            "annual_revenue": "₩120 trillion",
            "employee_count": 75000,
            "tags": ["enterprise", "automotive"],
            "metadata": {"region": "Korea", "tier": "platinum"}
        }
    ]
    
    for customer_data in sample_customers:
        customer = Customer(**customer_data)
        customer.created_at = datetime.now() - timedelta(days=random.randint(30, 365))
        customer.updated_at = datetime.now()
        mock_database["customers"][customer.id] = customer.dict()
    
    # Sample products
    sample_products = [
        {
            "id": "prod_001",
            "name": "AI Sales Assistant Pro",
            "category": "Software",
            "price": 5000000,
            "description": "Advanced AI-powered sales automation platform",
            "features": ["AI Analytics", "Automated Reports", "CRM Integration"],
            "stock": 100
        },
        {
            "id": "prod_002",
            "name": "Data Analytics Suite",
            "category": "Software",
            "price": 3000000,
            "description": "Comprehensive business intelligence solution",
            "features": ["Real-time Dashboard", "Predictive Analytics", "Custom Reports"],
            "stock": 50
        },
        {
            "id": "prod_003",
            "name": "Compliance Manager",
            "category": "Software",
            "price": 2000000,
            "description": "Automated compliance and regulatory management",
            "features": ["Regulatory Tracking", "Audit Trail", "Risk Assessment"],
            "stock": 75
        }
    ]
    
    for product_data in sample_products:
        product = Product(**product_data)
        product.created_at = datetime.now() - timedelta(days=random.randint(60, 180))
        product.updated_at = datetime.now()
        mock_database["products"][product.id] = product.dict()
    
    # Sample sales
    for i in range(10):
        sale = Sale(
            id=f"sale_{str(i+1).zfill(3)}",
            customer_id=random.choice(list(mock_database["customers"].keys())),
            product_id=random.choice(list(mock_database["products"].keys())),
            quantity=random.randint(1, 10),
            total_amount=random.randint(1000000, 50000000),
            status=random.choice(["completed", "pending", "completed"]),
            sale_date=datetime.now() - timedelta(days=random.randint(1, 90)),
            notes=f"Sale transaction {i+1}"
        )
        mock_database["sales"][sale.id] = sale.dict()
    
    # Sample analytics
    analytics_data = Analytics(
        id="analytics_001",
        type="revenue",
        period="monthly",
        metrics={
            "total_revenue": 150000000,
            "growth_rate": 15.3,
            "top_products": ["prod_001", "prod_002"],
            "conversion_rate": 3.5
        },
        generated_at=datetime.now()
    )
    mock_database["analytics"][analytics_data.id] = analytics_data.dict()
    
    logger.info("Mock database initialized with sample data")


# Initialize on module load
initialize_mock_data()


# Customer endpoints
@router.get("/customers", response_model=List[Customer])
async def get_customers(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    industry: Optional[str] = None
):
    """Get list of customers with pagination"""
    customers = list(mock_database["customers"].values())
    
    # Filter by industry if provided
    if industry:
        customers = [c for c in customers if c.get("industry", "").lower() == industry.lower()]
    
    # Apply pagination
    paginated = customers[offset:offset + limit]
    
    return paginated


@router.get("/customers/{customer_id}", response_model=Customer)
async def get_customer(customer_id: str):
    """Get specific customer by ID"""
    if customer_id not in mock_database["customers"]:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return mock_database["customers"][customer_id]


@router.post("/customers", response_model=Customer)
async def create_customer(customer: Customer):
    """Create new customer"""
    if not customer.id:
        customer.id = f"cust_{uuid.uuid4().hex[:8]}"
    
    customer.created_at = datetime.now()
    customer.updated_at = datetime.now()
    
    mock_database["customers"][customer.id] = customer.dict()
    logger.info(f"Created customer: {customer.id}")
    
    return customer


@router.put("/customers/{customer_id}", response_model=Customer)
async def update_customer(customer_id: str, customer: Customer):
    """Update existing customer"""
    if customer_id not in mock_database["customers"]:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    customer.id = customer_id
    customer.updated_at = datetime.now()
    
    # Preserve created_at
    customer.created_at = mock_database["customers"][customer_id].get("created_at")
    
    mock_database["customers"][customer_id] = customer.dict()
    logger.info(f"Updated customer: {customer_id}")
    
    return customer


@router.delete("/customers/{customer_id}")
async def delete_customer(customer_id: str):
    """Delete customer"""
    if customer_id not in mock_database["customers"]:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    del mock_database["customers"][customer_id]
    logger.info(f"Deleted customer: {customer_id}")
    
    return {"message": "Customer deleted successfully"}


# Product endpoints
@router.get("/products", response_model=List[Product])
async def get_products(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    category: Optional[str] = None
):
    """Get list of products with pagination"""
    products = list(mock_database["products"].values())
    
    # Filter by category if provided
    if category:
        products = [p for p in products if p.get("category", "").lower() == category.lower()]
    
    # Apply pagination
    paginated = products[offset:offset + limit]
    
    return paginated


@router.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: str):
    """Get specific product by ID"""
    if product_id not in mock_database["products"]:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return mock_database["products"][product_id]


@router.post("/products", response_model=Product)
async def create_product(product: Product):
    """Create new product"""
    if not product.id:
        product.id = f"prod_{uuid.uuid4().hex[:8]}"
    
    product.created_at = datetime.now()
    product.updated_at = datetime.now()
    
    mock_database["products"][product.id] = product.dict()
    logger.info(f"Created product: {product.id}")
    
    return product


# Sales endpoints
@router.get("/sales", response_model=List[Sale])
async def get_sales(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
    customer_id: Optional[str] = None
):
    """Get list of sales with filters"""
    sales = list(mock_database["sales"].values())
    
    # Apply filters
    if status:
        sales = [s for s in sales if s.get("status") == status]
    if customer_id:
        sales = [s for s in sales if s.get("customer_id") == customer_id]
    
    # Apply pagination
    paginated = sales[offset:offset + limit]
    
    return paginated


@router.get("/sales/{sale_id}", response_model=Sale)
async def get_sale(sale_id: str):
    """Get specific sale by ID"""
    if sale_id not in mock_database["sales"]:
        raise HTTPException(status_code=404, detail="Sale not found")
    
    return mock_database["sales"][sale_id]


@router.post("/sales", response_model=Sale)
async def create_sale(sale: Sale):
    """Create new sale"""
    if not sale.id:
        sale.id = f"sale_{uuid.uuid4().hex[:8]}"
    
    if not sale.sale_date:
        sale.sale_date = datetime.now()
    
    mock_database["sales"][sale.id] = sale.dict()
    logger.info(f"Created sale: {sale.id}")
    
    return sale


# Analytics endpoints
@router.get("/analytics")
async def get_analytics(
    type: Optional[str] = None,
    period: Optional[str] = None
):
    """Get analytics data"""
    analytics = list(mock_database["analytics"].values())
    
    # Apply filters
    if type:
        analytics = [a for a in analytics if a.get("type") == type]
    if period:
        analytics = [a for a in analytics if a.get("period") == period]
    
    return analytics


@router.post("/analytics/generate")
async def generate_analytics(type: str = "revenue", period: str = "monthly"):
    """Generate new analytics report"""
    analytics = Analytics(
        id=f"analytics_{uuid.uuid4().hex[:8]}",
        type=type,
        period=period,
        metrics={
            "total_revenue": random.randint(100000000, 500000000),
            "growth_rate": round(random.uniform(5, 25), 1),
            "conversion_rate": round(random.uniform(2, 5), 1),
            "top_customers": random.sample(list(mock_database["customers"].keys()), 
                                         min(3, len(mock_database["customers"]))),
            "trend": random.choice(["increasing", "stable", "decreasing"])
        },
        generated_at=datetime.now()
    )
    
    mock_database["analytics"][analytics.id] = analytics.dict()
    logger.info(f"Generated analytics: {analytics.id}")
    
    return analytics


# Document endpoints
@router.get("/documents", response_model=List[Document])
async def get_documents(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    type: Optional[str] = None
):
    """Get list of documents"""
    documents = list(mock_database["documents"].values())
    
    # Filter by type if provided
    if type:
        documents = [d for d in documents if d.get("type") == type]
    
    # Apply pagination
    paginated = documents[offset:offset + limit]
    
    return paginated


@router.post("/documents", response_model=Document)
async def create_document(document: Document):
    """Create new document"""
    if not document.id:
        document.id = f"doc_{uuid.uuid4().hex[:8]}"
    
    document.created_at = datetime.now()
    
    mock_database["documents"][document.id] = document.dict()
    logger.info(f"Created document: {document.id}")
    
    return document


# Compliance endpoints
@router.get("/compliance", response_model=List[ComplianceRecord])
async def get_compliance_records(
    status: Optional[str] = None
):
    """Get compliance records"""
    records = list(mock_database["compliance_records"].values())
    
    # Filter by status if provided
    if status:
        records = [r for r in records if r.get("status") == status]
    
    return records


@router.post("/compliance/check")
async def check_compliance(type: str = "privacy", data: Dict[str, Any] = {}):
    """Perform compliance check"""
    # Simulate compliance check
    is_compliant = random.choice([True, True, False])  # 66% compliant
    
    record = ComplianceRecord(
        id=f"comp_{uuid.uuid4().hex[:8]}",
        type=type,
        status="compliant" if is_compliant else "non_compliant",
        details={
            "checked_data": data,
            "rules_applied": ["PIPA", "GDPR", "Industry Standards"],
            "score": random.randint(60, 100) if is_compliant else random.randint(30, 59)
        },
        checked_at=datetime.now(),
        recommendations=[] if is_compliant else [
            "Review data encryption policies",
            "Update privacy notice",
            "Implement additional access controls"
        ]
    )
    
    mock_database["compliance_records"][record.id] = record.dict()
    logger.info(f"Compliance check performed: {record.id}")
    
    return record


# Database management endpoints
@router.get("/stats")
async def get_database_stats():
    """Get mock database statistics"""
    return {
        "customers": len(mock_database["customers"]),
        "products": len(mock_database["products"]),
        "sales": len(mock_database["sales"]),
        "analytics": len(mock_database["analytics"]),
        "documents": len(mock_database["documents"]),
        "compliance_records": len(mock_database["compliance_records"]),
        "total_records": sum(len(table) for table in mock_database.values())
    }


@router.post("/reset")
async def reset_database():
    """Reset mock database to initial state"""
    global mock_database
    mock_database = {
        "customers": {},
        "products": {},
        "sales": {},
        "analytics": {},
        "documents": {},
        "compliance_records": {}
    }
    initialize_mock_data()
    
    logger.info("Mock database reset to initial state")
    
    return {"message": "Database reset successfully", "stats": await get_database_stats()}


@router.post("/seed")
async def seed_additional_data(count: int = Query(5, ge=1, le=50)):
    """Seed additional random data"""
    # Add random customers
    for i in range(count):
        customer = Customer(
            name=f"Customer {uuid.uuid4().hex[:6]}",
            company=f"Company {uuid.uuid4().hex[:6]}",
            industry=random.choice(["Technology", "Healthcare", "Finance", "Manufacturing"]),
            email=f"user_{uuid.uuid4().hex[:6]}@example.com",
            tags=random.sample(["vip", "new", "enterprise", "sme"], random.randint(1, 3))
        )
        await create_customer(customer)
    
    # Add random sales
    for i in range(count * 2):
        if mock_database["customers"] and mock_database["products"]:
            sale = Sale(
                customer_id=random.choice(list(mock_database["customers"].keys())),
                product_id=random.choice(list(mock_database["products"].keys())),
                quantity=random.randint(1, 20),
                total_amount=random.randint(500000, 10000000),
                status=random.choice(["pending", "completed", "cancelled"])
            )
            await create_sale(sale)
    
    stats = await get_database_stats()
    logger.info(f"Seeded additional data: {count} customers, {count*2} sales")
    
    return {"message": f"Seeded {count} customers and {count*2} sales", "stats": stats}