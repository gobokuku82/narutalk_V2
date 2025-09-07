"""
API routes for Sales Support AI
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
from loguru import logger

# Import the global app instance
from .app import sales_app

router = APIRouter()

# Request/Response models
class ProcessRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class ProcessResponse(BaseModel):
    response: str
    thread_id: str
    agent_path: List[str]
    results: Dict[str, Any]
    timestamp: str
    status: str

class AgentRequest(BaseModel):
    task: str
    context: Optional[Dict[str, Any]] = None
    thread_id: Optional[str] = None

# Dependency to get sales_app
async def get_sales_app():
    from .app import sales_app
    if sales_app is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return sales_app

@router.post("/process", response_model=ProcessResponse)
async def process_request(
    request: ProcessRequest,
    app = Depends(get_sales_app)
):
    """
    Process a user request through the LangGraph StateGraph
    Routes through supervisor to appropriate agents
    """
    try:
        logger.info(f"Processing request: {request.message[:100]}...")
        
        # Process through the graph
        result = await app.aprocess_request(
            user_input=request.message,
            thread_id=request.thread_id
        )
        
        # Extract the last message as response
        messages = result.get("messages", [])
        last_message = messages[-1] if messages else None
        response_text = last_message.content if last_message else "No response generated"
        
        # Extract agent path from progress
        progress = result.get("progress", [])
        agent_path = [p.get("agent", "unknown") for p in progress]
        
        # Get thread_id
        thread_id = result.get("metadata", {}).get("thread_id", "")
        
        return ProcessResponse(
            response=response_text,
            thread_id=thread_id,
            agent_path=agent_path,
            results=result.get("results", {}),
            timestamp=datetime.now().isoformat(),
            status="success"
        )
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze")
async def analyze_request(
    request: AgentRequest,
    app = Depends(get_sales_app)
):
    """
    Direct route to analytics agent
    """
    try:
        # Format request for analytics
        formatted_input = f"analyze the following: {request.task}"
        
        result = await app.aprocess_request(
            user_input=formatted_input,
            thread_id=request.thread_id
        )
        
        return {
            "status": "success",
            "analysis": result.get("results", {}).get("analytics", {}),
            "messages": [msg.content for msg in result.get("messages", [])],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search")
async def search_request(
    request: AgentRequest,
    app = Depends(get_sales_app)
):
    """
    Direct route to search agent
    """
    try:
        # Format request for search
        formatted_input = f"search for information about: {request.task}"
        
        result = await app.aprocess_request(
            user_input=formatted_input,
            thread_id=request.thread_id
        )
        
        return {
            "status": "success",
            "search_results": result.get("results", {}).get("search", {}),
            "messages": [msg.content for msg in result.get("messages", [])],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/document")
async def document_request(
    request: AgentRequest,
    app = Depends(get_sales_app)
):
    """
    Direct route to document generation agent
    """
    try:
        # Format request for document generation
        formatted_input = f"create a document for: {request.task}"
        
        result = await app.aprocess_request(
            user_input=formatted_input,
            thread_id=request.thread_id
        )
        
        return {
            "status": "success",
            "documents": result.get("results", {}).get("document", {}),
            "messages": [msg.content for msg in result.get("messages", [])],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in document generation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/compliance")
async def compliance_request(
    request: AgentRequest,
    app = Depends(get_sales_app)
):
    """
    Direct route to compliance agent
    """
    try:
        # Format request for compliance check
        formatted_input = f"check compliance for: {request.task}"
        
        result = await app.aprocess_request(
            user_input=formatted_input,
            thread_id=request.thread_id
        )
        
        return {
            "status": "success",
            "compliance": result.get("results", {}).get("compliance", {}),
            "messages": [msg.content for msg in result.get("messages", [])],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in compliance check: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/graph/visualization")
async def get_graph_visualization(app = Depends(get_sales_app)):
    """
    Get graph structure for visualization
    """
    try:
        structure = app.get_graph_visualization()
        return {
            "status": "success",
            "graph": structure,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting graph visualization: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents")
async def list_agents():
    """
    List all available agents
    """
    return {
        "agents": [
            {
                "name": "supervisor",
                "description": "Routes tasks to appropriate agents",
                "capabilities": ["task routing", "coordination", "progress tracking"]
            },
            {
                "name": "analytics",
                "description": "Performs data analysis and generates insights",
                "capabilities": ["data analysis", "metrics calculation", "trend analysis"]
            },
            {
                "name": "search",
                "description": "Searches for information and retrieves data",
                "capabilities": ["knowledge base search", "customer data", "market intelligence"]
            },
            {
                "name": "document",
                "description": "Generates documents and reports",
                "capabilities": ["proposals", "reports", "emails", "meeting minutes"]
            },
            {
                "name": "compliance",
                "description": "Validates compliance and regulatory requirements",
                "capabilities": ["data privacy", "regulatory compliance", "contract validation"]
            }
        ],
        "total": 5,
        "timestamp": datetime.now().isoformat()
    }

@router.get("/status/{thread_id}")
async def get_thread_status(
    thread_id: str,
    app = Depends(get_sales_app)
):
    """
    Get status of a specific thread
    """
    try:
        # This would typically query the checkpointer
        # For now, return a mock status
        return {
            "thread_id": thread_id,
            "status": "active",
            "last_updated": datetime.now().isoformat(),
            "message_count": 0
        }
    except Exception as e:
        logger.error(f"Error getting thread status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))