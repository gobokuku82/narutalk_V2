"""
Enhanced FastAPI main application with full LangGraph 0.6.6 integration
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import os
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from loguru import logger
import traceback

# Load environment variables
load_dotenv()

# Import our enhanced graph components
from ..graph.enhanced_graph import create_enhanced_graph, execute_enhanced_query
from ..state.enhanced_state import create_initial_state
# mock_db_router removed - moved to tests/mock_db.py (only used for testing)

# Global enhanced graph instance
enhanced_graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI
    """
    global enhanced_graph
    
    # Startup
    logger.info("🚀 Starting Enhanced Sales Support AI Application with Query Analyzer...")
    
    # Initialize the Enhanced LangGraph (async)
    enhanced_graph = await create_enhanced_graph()
    
    logger.info("✅ Enhanced LangGraph 0.6.6 initialized with AsyncSqliteSaver and Dynamic Router")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Sales Support AI Application...")


# Create FastAPI app
app = FastAPI(
    title="Sales Support AI API - Enhanced",
    description="LangGraph 0.6.6 based Sales Support AI System with full integration",
    version="2.0.0",
    lifespan=lifespan
)

# Configure CORS
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Include routers
# router removed - moved to tests/test_routes.py (only used for testing)
# mock_db_router removed - moved to tests/mock_db.py (only used for testing)


# Request/Response Models
class GraphInvokeRequest(BaseModel):
    """Request model for graph invocation"""
    input: Dict[str, Any] = Field(description="Input to the graph")
    config: Optional[Dict[str, Any]] = Field(default=None, description="Configuration for the graph")
    thread_id: Optional[str] = Field(default=None, description="Thread ID for conversation continuity")
    stream: Optional[bool] = Field(default=False, description="Whether to stream the response")


class GraphInvokeResponse(BaseModel):
    """Response model for graph invocation"""
    output: Dict[str, Any]
    thread_id: str
    execution_time: float
    agent_path: List[str]
    status: str


class StreamEvent(BaseModel):
    """Model for streaming events"""
    type: str
    node: Optional[str] = None
    data: Dict[str, Any]
    timestamp: str


# WebSocket Manager
class EnhancedConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_metadata: Dict[str, Dict] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.connection_metadata[client_id] = {
            "connected_at": datetime.now().isoformat(),
            "message_count": 0
        }
        logger.info(f"WebSocket connected: {client_id}")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            del self.connection_metadata[client_id]
            logger.info(f"WebSocket disconnected: {client_id}")

    async def send_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_text(message)
                self.connection_metadata[client_id]["message_count"] += 1
            except Exception as e:
                logger.warning(f"Failed to send message to {client_id}: {e}")
                # Remove disconnected client
                self.disconnect(client_id)
                return False
        return True

    async def send_json(self, data: dict, client_id: str):
        return await self.send_message(json.dumps(data, ensure_ascii=False), client_id)

    async def broadcast(self, message: str):
        for client_id, connection in self.active_connections.items():
            await connection.send_text(message)

    def get_connection_info(self, client_id: str) -> Optional[Dict]:
        return self.connection_metadata.get(client_id)


manager = EnhancedConnectionManager()


# Main API Endpoints
@app.get("/")
async def root():
    """Enhanced root endpoint with system info"""
    import langgraph
    return {
        "message": "Sales Support AI API - Enhanced Version",
        "version": "2.0.0",
        "langgraph_version": langgraph.__version__,
        "status": "running",
        "features": {
            "graph_invoke": True,
            "websocket_streaming": True,
            "error_handling": "comprehensive"
        },
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/graph/invoke", response_model=GraphInvokeResponse)
async def invoke_graph(request: GraphInvokeRequest):
    """
    Main endpoint to invoke the LangGraph StateGraph
    Following LangGraph 0.6.6 patterns
    """
    start_time = datetime.now()
    
    try:
        if not enhanced_graph:
            raise HTTPException(status_code=503, detail="Enhanced graph not initialized")
        
        # Prepare input
        if "messages" in request.input:
            # Direct message input
            user_input = request.input["messages"][-1].get("content", "") if request.input["messages"] else ""
        else:
            # Extract from input dict
            user_input = request.input.get("message", "") or request.input.get("input", "")
        
        if not user_input:
            raise HTTPException(status_code=400, detail="No input message provided")
        
        # Process through graph
        if request.stream:
            # Return streaming response
            return StreamingResponse(
                stream_graph_execution(user_input, request.thread_id),
                media_type="text/event-stream"
            )
        else:
            # Regular invocation with enhanced graph
            config = {"configurable": {"thread_id": request.thread_id or "default"}}
            result = await execute_enhanced_query(
                enhanced_graph,
                query=user_input,
                config=config
            )
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Extract agent path
            progress = result.get("progress", [])
            agent_path = [p.get("agent", "unknown") for p in progress]
            
            return GraphInvokeResponse(
                output=result,
                thread_id=result.get("metadata", {}).get("thread_id", ""),
                execution_time=execution_time,
                agent_path=agent_path,
                status="success"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in graph invocation: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Graph invocation failed: {str(e)}")


async def stream_graph_execution(user_input: str, thread_id: Optional[str] = None):
    """
    Stream graph execution as Server-Sent Events
    """
    try:
        # Stream with enhanced graph
        config = {"configurable": {"thread_id": thread_id or "default"}}
        initial_state = create_initial_state()
        from langchain_core.messages import HumanMessage
        initial_state["messages"] = [HumanMessage(content=user_input)]
        initial_state["raw_query"] = user_input
        
        async for output in enhanced_graph.astream(initial_state, config):
            for node_name, node_output in output.items():
                event = {
                    "type": "node_output",
                    "node": node_name,
                    "data": {
                        "current_agent": node_output.get("current_agent"),
                        "progress": node_output.get("progress"),
                        "message": str(node_output.get("messages", [])[-1].content) if node_output.get("messages") else None
                    },
                    "timestamp": datetime.now().isoformat()
                }
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        
        # Send completion event
        yield f"data: {json.dumps({'type': 'complete', 'timestamp': datetime.now().isoformat()})}\n\n"
        
    except Exception as e:
        error_event = {
            "type": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }
        yield f"data: {json.dumps(error_event)}\n\n"


@app.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket, client_id: Optional[str] = None):
    """
    Enhanced WebSocket endpoint for real-time streaming with progress updates
    """
    if not client_id:
        client_id = f"client_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    await manager.connect(websocket, client_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Log received message
            logger.info(f"WebSocket received from {client_id}: {message.get('type', 'unknown')}")
            
            # Handle different message types
            if message.get("type") == "invoke":
                await handle_websocket_invoke(websocket, client_id, message)
                
            elif message.get("type") == "stream_events":
                await handle_websocket_stream_events(websocket, client_id, message)
                
            elif message.get("type") == "ping":
                await manager.send_json({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }, client_id)
                
            elif message.get("type") == "get_status":
                connection_info = manager.get_connection_info(client_id)
                await manager.send_json({
                    "type": "status",
                    "client_id": client_id,
                    "connection_info": connection_info,
                    "timestamp": datetime.now().isoformat()
                }, client_id)
                
            else:
                await manager.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {message.get('type')}",
                    "timestamp": datetime.now().isoformat()
                }, client_id)
                
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        logger.info(f"WebSocket {client_id} disconnected normally")
        
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {str(e)}")
        await manager.send_json({
            "type": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }, client_id)
        manager.disconnect(client_id)


async def handle_websocket_invoke(websocket: WebSocket, client_id: str, message: dict):
    """
    Handle graph invocation through WebSocket
    """
    user_input = message.get("input", "")
    thread_id = message.get("thread_id")
    
    # Send acknowledgment
    await manager.send_json({
        "type": "acknowledgment",
        "message": "Processing your request...",
        "thread_id": thread_id,
        "timestamp": datetime.now().isoformat()
    }, client_id)
    
    try:
        # Stream the enhanced graph execution with progress updates
        node_count = 0
        config = {"configurable": {"thread_id": thread_id or "default"}}
        initial_state = create_initial_state()
        from langchain_core.messages import HumanMessage
        initial_state["messages"] = [HumanMessage(content=user_input)]
        initial_state["raw_query"] = user_input
        
        async for output in enhanced_graph.astream(initial_state, config):
            for node_name, node_output in output.items():
                node_count += 1
                
                # Check if client is still connected before sending
                if client_id not in manager.active_connections:
                    logger.info(f"Client {client_id} disconnected, stopping stream")
                    return
                
                # Check for execution plan from query_analyzer or execution_planner
                if node_name in ["query_analyzer", "execution_planner"] and node_output.get("execution_plan"):
                    # Send execution plan to frontend
                    plan = node_output.get("execution_plan", {})
                    agents = plan.get("sequential_tasks", []) + plan.get("parallel_tasks", [])
                    await manager.send_json({
                        "type": "execution_plan",
                        "agents": agents,
                        "total_steps": len(agents),
                        "reason": plan.get("reasoning", ""),
                        "timestamp": datetime.now().isoformat()
                    }, client_id)
                
                # Send progress update
                context = node_output.get("context", {})
                execution_plan = context.get("execution_plan", [])
                current_step = context.get("current_step", 0)
                
                success = await manager.send_json({
                    "type": "progress",
                    "node": node_name,
                    "node_count": node_count,
                    "current_agent": node_output.get("current_agent"),
                    "progress": node_output.get("progress"),
                    "execution_plan": execution_plan,
                    "current_step": current_step,
                    "total_steps": len(execution_plan) if execution_plan else 1,
                    "timestamp": datetime.now().isoformat()
                }, client_id)
                
                if not success:
                    logger.info(f"Failed to send to {client_id}, stopping stream")
                    return
                
                # Send node output
                if node_output.get("messages"):
                    success = await manager.send_json({
                        "type": "node_output",
                        "node": node_name,
                        "message": str(node_output.get("messages", [])[-1].content),
                        "metadata": {
                            "agent": node_output.get("current_agent"),
                            "task_type": node_output.get("task_type")
                        },
                        "timestamp": datetime.now().isoformat()
                    }, client_id)
                
                # Small delay for better streaming experience
                await asyncio.sleep(0.1)
        
        # Send completion message if client is still connected
        if client_id in manager.active_connections:
            await manager.send_json({
                "type": "complete",
                "message": "Request processed successfully",
                "total_nodes": node_count,
                "timestamp": datetime.now().isoformat()
            }, client_id)
        
    except Exception as e:
        logger.error(f"Error in WebSocket invocation: {str(e)}")
        # Only send error if client is still connected
        if client_id in manager.active_connections:
            await manager.send_json({
            "type": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }, client_id)


async def handle_websocket_stream_events(websocket: WebSocket, client_id: str, message: dict):
    """
    Handle LangGraph 0.6.6 event streaming through WebSocket
    """
    user_input = message.get("input", "")
    thread_id = message.get("thread_id")
    
    try:
        event_count = 0
        config = {"configurable": {"thread_id": thread_id or "default"}}
        initial_state = create_initial_state()
        from langchain_core.messages import HumanMessage
        initial_state["messages"] = [HumanMessage(content=user_input)]
        initial_state["raw_query"] = user_input
        
        async for event in enhanced_graph.astream_events(initial_state, version="v2", config=config):
            event_count += 1
            
            # Send each event with enhanced metadata
            await manager.send_json({
                "type": "langgraph_event",
                "event_number": event_count,
                "event_data": event,
                "timestamp": datetime.now().isoformat()
            }, client_id)
            
            # Rate limiting for events
            if event_count % 10 == 0:
                await asyncio.sleep(0.05)
        
        # Send completion
        await manager.send_json({
            "type": "events_complete",
            "total_events": event_count,
            "timestamp": datetime.now().isoformat()
        }, client_id)
        
    except Exception as e:
        logger.error(f"Error in event streaming: {str(e)}")
        await manager.send_json({
            "type": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }, client_id)


# Error Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    logger.error(f"Validation error: {exc}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "details": exc.errors(),
            "body": exc.body if hasattr(exc, 'body') else None,
            "timestamp": datetime.now().isoformat()
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    logger.error(f"HTTP exception: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Error",
            "message": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now().isoformat()
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "type": type(exc).__name__,
            "timestamp": datetime.now().isoformat()
        }
    )


# Health and Monitoring Endpoints
@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    health_status = {
        "status": "healthy",
        "langgraph": "0.6.6",
        "services": {
            "graph": "operational" if sales_app else "not_initialized",
            "websocket": f"{len(manager.active_connections)} active connections"
        },
        "agents": ["supervisor", "analytics", "search", "document", "compliance"],
        "timestamp": datetime.now().isoformat()
    }
    
    # Check if any service is not operational
    if not sales_app:
        health_status["status"] = "degraded"
        
    return health_status


@app.get("/metrics")
async def get_metrics():
    """Get application metrics"""
    return {
        "websocket_connections": len(manager.active_connections),
        "connection_details": [
            {
                "client_id": client_id,
                "metadata": manager.connection_metadata.get(client_id, {})
            }
            for client_id in manager.active_connections.keys()
        ],
        "timestamp": datetime.now().isoformat()
    }