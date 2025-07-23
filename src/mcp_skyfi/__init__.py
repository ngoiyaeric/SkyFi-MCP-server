"""
SkyFi MCP Server - Satellite as a Service for AI Agents

A Model Context Protocol (MCP) server providing AI agents with access to
satellite imagery, geospatial data, and weather information through the
SkyFi Platform API.

Features:
- Search and order satellite imagery
- OpenStreetMap geocoding and POI search
- Weather data integration
- Multi-method authentication
- Enterprise-grade security
- Developer-friendly APIs

Usage:
    # STDIO transport (default)
    python -m mcp_skyfi
    
    # HTTP transport
    python -m mcp_skyfi --transport streamable-http --port 8000
    
    # SSE transport
    python -m mcp_skyfi --transport sse --port 8000
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
from typing import Literal

from .servers.main import main_mcp
from .utils.logging import configure_logging
from .utils.environment import get_env_bool, get_env_int


def main() -> None:
    """Main entry point for the SkyFi MCP server."""
    
    parser = argparse.ArgumentParser(
        description="SkyFi MCP Server - Satellite as a Service for AI Agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--transport",
        type=str,
        choices=["stdio", "streamable-http", "sse"],
        default="stdio",
        help="MCP transport method (default: stdio)"
    )
    
    parser.add_argument(
        "--port", 
        type=int, 
        default=get_env_int("MCP_PORT", 8000),
        help="Port for HTTP/SSE transports (default: 8000)"
    )
    
    parser.add_argument(
        "--host",
        type=str,
        default=os.getenv("MCP_HOST", "localhost"),
        help="Host for HTTP/SSE transports (default: localhost)"
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=os.getenv("LOG_LEVEL", "INFO"),
        help="Logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--read-only",
        action="store_true",
        default=get_env_bool("READ_ONLY_MODE", False),
        help="Enable read-only mode (no write operations)"
    )
    
    parser.add_argument(
        "--enabled-tools",
        type=str,
        nargs="*",
        help="Comma-separated list of enabled tools (all tools enabled by default)"
    )

    args = parser.parse_args()
    
    # Configure logging
    configure_logging(level=args.log_level)
    logger = logging.getLogger("mcp-skyfi")
    
    # Set environment variables for server configuration
    if args.read_only:
        os.environ["READ_ONLY_MODE"] = "true"
    
    if args.enabled_tools:
        os.environ["ENABLED_TOOLS"] = ",".join(args.enabled_tools)
    
    logger.info(f"Starting SkyFi MCP server with transport: {args.transport}")
    
    try:
        if args.transport == "stdio":
            # STDIO transport
            asyncio.run(main_mcp.run_stdio())
            
        elif args.transport in ["streamable-http", "sse"]:
            # HTTP-based transports
            app = main_mcp.http_app(transport=args.transport)
            
            # Use uvicorn for production-ready server
            import uvicorn
            uvicorn.run(
                app,
                host=args.host,
                port=args.port,
                log_level=args.log_level.lower(),
                access_log=True,
                server_header=False,
                date_header=False
            )
            
    except KeyboardInterrupt:
        logger.info("SkyFi MCP server shutting down...")
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()