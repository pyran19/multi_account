#!/usr/bin/env python3
import os
import sys
import argparse
import uvicorn
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='Run Rate Matching Simulation MCP Server')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=12000, help='Port to bind to')
    parser.add_argument('--reload', action='store_true', help='Enable auto-reload')
    args = parser.parse_args()
    
    # Get the directory of this script
    script_dir = Path(__file__).parent.absolute()
    
    # Add the parent directory to the Python path
    sys.path.append(str(script_dir))
    
    # Run the server
    logger.info(f"Starting server on {args.host}:{args.port}")
    uvicorn.run(
        "server.mcp_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )

if __name__ == "__main__":
    main()