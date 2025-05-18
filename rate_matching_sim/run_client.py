#!/usr/bin/env python3
import os
import sys
import argparse
import http.server
import socketserver
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

def main():
    parser = argparse.ArgumentParser(description='Run Rate Matching Simulation Client Server')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=12001, help='Port to bind to')
    args = parser.parse_args()
    
    # Get the directory of this script
    script_dir = Path(__file__).parent.absolute()
    client_dir = script_dir / 'client'
    
    # Change to the client directory
    os.chdir(client_dir)
    
    # Run the server
    handler = CORSHTTPRequestHandler
    httpd = socketserver.TCPServer((args.host, args.port), handler)
    
    logger.info(f"Starting client server on {args.host}:{args.port}")
    logger.info(f"Open http://localhost:{args.port} in your browser")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped")
    finally:
        httpd.server_close()

if __name__ == "__main__":
    main()