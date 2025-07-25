#!/usr/bin/env python3
"""
SkyFi MCP Server - Enterprise Satellite Imagery Platform

A production-ready Model Context Protocol (MCP) server providing access to:
- SkyFi Platform API for satellite imagery search and ordering
- OpenStreetMap geocoding and mapping services  
- Weather data integration for mission planning

Features:
- Multi-method authentication (API keys, OAuth 2.0, Personal Access Tokens)  
- Multi-transport support (STDIO, HTTP, Server-Sent Events)
- Enterprise-grade configuration and monitoring
- Domain-driven tool organization
- Production-ready deployment options

Usage:
    python -m mcp_skyfi                    # STDIO transport (default)
    python -m mcp_skyfi --transport http   # HTTP transport
    python -m mcp_skyfi --transport sse    # Server-Sent Events transport
    python -m mcp_skyfi --log-level DEBUG  # Enable debug logging
"""


import asyncio
import logging
import signal
import sys
from typing import Any, Dict, Optional

import click
import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .servers.main import main_mcp
from .servers.dependencies import (
    get_transport_config,
    get_logging_config, 
    validate_environment,
    get_environment_summary
)
from .utils.logging import configure_logging
from .utils.environment import load_dotenv_if_exists

__version__ = "1.0.0"
__author__ = "SkyFi MCP Team"

# Rich console for beautiful CLI output
console = Console()
logger = logging.getLogger("mcp-skyfi")

def display_banner() -> None:
    """Display startup banner with server information."""
    banner_text = Text.assemble(
        ("🛰️  SkyFi MCP Server ", "bold blue"),
        ("v" + __version__, "dim"),
        ("\n\n", ""),
        ("Enterprise Satellite Imagery Platform", ""),
        ("\nPowered by Model Context Protocol", "dim")
    )
    
    panel = Panel(
        banner_text,
        title="[bold green]Starting Server[/bold green]",
        border_style="blue",
        padding=(1, 2)
    )
    console.print(panel)

def display_startup_info(transport: str, host: str, port: int, services: Dict[str, Any]) -> None:
    """Display startup configuration information."""
    # Transport info
    if transport == "stdio":
        transport_info = "STDIO (Standard Input/Output)"
        endpoint_info = "Connected via stdin/stdout"
    elif transport == "http":
        transport_info = "HTTP (Streamable HTTP)"
        endpoint_info = f"http://{host}:{port}"
    elif transport == "sse": 
        transport_info = "SSE (Server-Sent Events)"
        endpoint_info = f"http://{host}:{port}"
    else:
        transport_info = transport.upper()
        endpoint_info = f"{host}:{port}"
    
    # Service status
    available_services = [name for name, status in services.get("services", {}).items() if status]
    service_count = len(available_services)
    
    startup_info = Text.assemble(
        ("🚀 Transport: ", "bold"), (transport_info, "green"), ("\n"),
        ("🌐 Endpoint: ", "bold"), (endpoint_info, "cyan"), ("\n"),
        ("🔧 Services: ", "bold"), (f"{service_count} available", "green" if service_count > 0 else "yellow"), ("\n"),
        ("   • ", "dim"), (", ".join(available_services) if available_services else "None configured", ""),
    )
    
    if services.get("validation", {}).get("warnings"):
        warnings = services["validation"]["warnings"]
        startup_info.append(f"\n⚠️  Warnings: {len(warnings)}", style="yellow")
        for warning in warnings[:3]:  # Show first 3 warnings
            startup_info.append(f"\n   • {warning}", style="dim yellow")
    
    console.print(Panel(startup_info, title="[bold cyan]Server Configuration[/bold cyan]", border_style="cyan"))

def setup_signal_handlers(transport: str = "stdio") -> None:
    """Setup graceful shutdown signal handlers."""
    def signal_handler(signum, frame):
        # Only show shutdown message for non-STDIO transports
        if transport.lower() != "stdio":
            console.print("\n[yellow]🛑 Received shutdown signal. Gracefully shutting down...[/yellow]")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

@click.command()
@click.option(
    "--transport", 
    type=click.Choice(["stdio", "http", "sse"], case_sensitive=False),
    default="stdio",
    help="Transport protocol to use (default: stdio)"
)
@click.option(
    "--host",
    default="localhost", 
    help="Host to bind HTTP/SSE transport (default: localhost)"
)
@click.option(
    "--port",
    type=int,
    default=8000,
    help="Port to bind HTTP/SSE transport (default: 8000)"
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
    help="Logging level (default: from environment or INFO)"
)
@click.option(
    "--log-format",
    type=click.Choice(["json", "console", "simple"], case_sensitive=False),
    help="Log format (default: from environment or console for TTY, json otherwise)"
)
@click.option(
    "--config-check",
    is_flag=True,
    help="Validate configuration and exit"
)
@click.option(
    "--quiet",
    is_flag=True,
    help="Suppress startup banner and info"
)
@click.version_option(version=__version__, prog_name="SkyFi MCP Server")
def main(
    transport: str,
    host: str, 
    port: int,
    log_level: Optional[str],
    log_format: Optional[str],
    config_check: bool,
    quiet: bool
) -> None:
    """
    SkyFi MCP Server - Enterprise Satellite Imagery Platform
    
    Start the MCP server with the specified transport and configuration.
    The server will automatically discover and configure available services
    based on environment variables.
    
    Examples:
        python -m mcp_skyfi                           # STDIO transport
        python -m mcp_skyfi --transport http         # HTTP on localhost:8000  
        python -m mcp_skyfi --transport sse --port 3000  # SSE on port 3000
        python -m mcp_skyfi --log-level DEBUG        # Enable debug logging
        python -m mcp_skyfi --config-check           # Validate configuration
    """
    try:
        # Load environment variables from .env file if present
        load_dotenv_if_exists()
        
        # Get configuration from environment and CLI args
        env_logging_config = get_logging_config()
        env_transport_config = get_transport_config()
        
        # Override with CLI arguments
        final_log_level = log_level or env_logging_config["level"]
        final_log_format = log_format or env_logging_config["format"]
        
        # Auto-detect log format based on output type
        if not log_format and not env_logging_config.get("format"):
            final_log_format = "console" if sys.stdout.isatty() else "json"
        
        # Configure logging (redirect to stderr for STDIO transport)
        if transport.lower() == "stdio":
            # For STDIO transport, redirect all logging to stderr to avoid interfering with JSON-RPC
            import logging
            logging.basicConfig(
                level=getattr(logging, final_log_level.upper(), logging.INFO),
                stream=sys.stderr,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        else:
            configure_logging(
                level=final_log_level,
                format_type=final_log_format,
                include_timestamp=True,
                include_caller=(final_log_level == "DEBUG"),
                service_name="mcp-skyfi"
            )
        
        logger.info(f"🚀 SkyFi MCP Server v{__version__} starting up...")
        logger.info(f"📋 Transport: {transport}, Log Level: {final_log_level}, Format: {final_log_format}")
        
        # Validate environment configuration
        env_summary = get_environment_summary()
        validation_result = validate_environment()
        
        # Display banner (suppress for STDIO transport)
        if not quiet and transport.lower() != "stdio":
            display_banner()
        
        # Handle configuration check mode
        if config_check:
            console.print("[bold green]🔍 Configuration Validation[/bold green]")
            
            if validation_result["valid"]:
                console.print("✅ Configuration is valid", style="green")
            else:
                console.print("❌ Configuration has errors", style="red")
                for error in validation_result["errors"]:
                    console.print(f"   • {error}", style="red")
            
            if validation_result["warnings"]:
                console.print(f"\n⚠️  Warnings ({len(validation_result['warnings'])}):", style="yellow")
                for warning in validation_result["warnings"]:
                    console.print(f"   • {warning}", style="yellow")
            
            # Display service status
            console.print(f"\n🔧 Service Status:")
            for service_name, service_info in validation_result["services"].items():
                status_icon = "✅" if service_info["configured"] else ("⚠️" if service_info["available"] else "❌")
                status_text = "configured" if service_info["configured"] else ("available" if service_info["available"] else "unavailable")
                console.print(f"   {status_icon} {service_name}: {status_text}")
                
                for issue in service_info.get("issues", []):
                    console.print(f"      • {issue}", style="dim red")
            
            sys.exit(0 if validation_result["valid"] else 1)
        
        # Check for critical configuration errors
        if not validation_result["valid"]:
            console.print("[bold red]❌ Configuration Error[/bold red]")
            for error in validation_result["errors"]:
                console.print(f"   • {error}", style="red")
            console.print("\n💡 Use --config-check to see detailed validation results")
            sys.exit(1)
        
        # Display startup information (suppress for STDIO transport)
        if not quiet and transport.lower() != "stdio":
            display_startup_info(transport, host, port, env_summary)
        
        # Setup signal handlers for graceful shutdown
        setup_signal_handlers(transport)
        
        # Start the appropriate transport
        if transport.lower() == "stdio":
            logger.info("🔌 Starting STDIO transport...")
            # Skip console output for STDIO - only JSON messages allowed on stdout
            
            # Run the STDIO server
            main_mcp.run()
            
        elif transport.lower() in ["http", "sse"]:
            transport_mode = "streamable-http" if transport.lower() == "http" else "sse"
            logger.info(f"🔌 Starting {transport_mode.upper()} transport on {host}:{port}...")
            
            if not quiet:
                console.print(f"[green]✅ Server ready - HTTP endpoint: http://{host}:{port}[/green]")
                console.print("[dim]Press Ctrl+C to shutdown[/dim]")
            
            # Create HTTP application
            app = main_mcp.http_app(transport=transport_mode)
            
            # Configure uvicorn
            uvicorn_config = uvicorn.Config(
                app=app,
                host=host,
                port=port,
                log_level=final_log_level.lower(),
                access_log=(final_log_level == "DEBUG"),
                server_header=False,
                date_header=False,
            )
            
            # Run the HTTP server
            server = uvicorn.Server(uvicorn_config)
            asyncio.run(server.serve())
            
        else:
            console.print(f"[red]❌ Unknown transport: {transport}[/red]")
            sys.exit(1)
            
    except KeyboardInterrupt:
        # Only show shutdown message for non-STDIO transports
        if not quiet and transport.lower() != "stdio":
            console.print("\n[yellow]🛑 Received keyboard interrupt. Shutting down gracefully...[/yellow]")
        logger.info("📴 Server shutdown requested by user")
        sys.exit(0)
        
    except Exception as e:
        # Only show error message for non-STDIO transports
        if transport.lower() != "stdio":
            console.print(f"[red]💥 Server startup failed: {e}[/red]")
        logger.error(f"💥 Fatal error during startup: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()