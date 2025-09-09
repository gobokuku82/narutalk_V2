"""
Main entry point for Sales Support AI Backend
LangGraph 0.6.6 implementation with enhanced features
"""
import os
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))

import uvicorn
from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()

# Configure enhanced logging
logger.add(
    "logs/app.log",
    rotation="10 MB",
    retention="7 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {module}:{function}:{line} - {message}"
)

def main():
    """Main function to run the enhanced application"""
    # Get configuration from environment
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("API_RELOAD", "true").lower() == "true"
    
    logger.info("=" * 50)
    logger.info("🚀 Starting Sales Support AI API (LangGraph 0.6.6)")
    logger.info(f"📍 Host: {host}:{port}")
    logger.info(f"🔧 LangGraph version: 0.6.6")
    logger.info(f"🔄 Reload: {reload}")
    logger.info("=" * 50)
    
    # Run the FastAPI application
    uvicorn.run(
        "src.api.app:app",  # Changed from main:app to app:app
        host=host,
        port=port,
        reload=reload,
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    main()