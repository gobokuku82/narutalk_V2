"""
API routes for Sales Support AI
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
from loguru import logger

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

# AgentRequest model removed - was only used by unused endpoints

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

# Unused endpoints removed - only keeping /process which is actually used by the frontend via WebSocket