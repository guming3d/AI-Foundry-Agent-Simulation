#!/usr/bin/env python3
"""
Start the FastAPI backend server.

Usage:
    python start_api.py [--host HOST] [--port PORT] [--reload]

Examples:
    python start_api.py                     # Default: 0.0.0.0:8000
    python start_api.py --port 8080         # Custom port
    python start_api.py --reload            # Development mode with auto-reload
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def main():
    parser = argparse.ArgumentParser(description="Start the FastAPI backend server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn not installed. Run: pip install uvicorn[standard]")
        sys.exit(1)

    print(f"Starting API server on http://{args.host}:{args.port}")
    print(f"API documentation: http://{args.host}:{args.port}/docs")
    print()

    uvicorn.run(
        "src.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
