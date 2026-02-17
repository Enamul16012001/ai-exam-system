#!/usr/bin/env python3
"""
Main entry point for the AI-based Exam System
Handles uvicorn server startup
"""

import uvicorn
import os
from dotenv import load_dotenv


def main():
    """Start the FastAPI server"""
    load_dotenv()

    # Verify required environment variables
    required_vars = ["API_KEY", "ADMIN_SECRET_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these variables in your .env file")
        return

    # Get server configuration from environment variables with defaults
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "true").lower() == "true"
    log_level = os.getenv("LOG_LEVEL", "info")

    print("=" * 60)
    print("  AI-based Exam System with Background Evaluation")
    print("=" * 60)
    print(f"  Server:       http://{host}:{port}")
    print(f"  Admin panel:  http://{host}:{port}/admin")
    print(f"  Health check: http://{host}:{port}/health")
    print(f"  Reload mode:  {reload}")
    print("=" * 60)

    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level
    )


if __name__ == "__main__":
    main()
