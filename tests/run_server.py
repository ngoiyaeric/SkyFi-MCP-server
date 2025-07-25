#!/usr/bin/env python3
"""
Quick Server Runner for SkyFi MCP Server

This script provides a simple way to start the SkyFi MCP server for development,
testing, and demonstration purposes. It handles common configuration scenarios
and provides helpful debugging information.

Usage:
    python run_server.py                    # STDIO transport with auto-config
    python run_server.py --http             # HTTP transport on localhost:8000
    python run_server.py --sse --port 3000  # SSE transport on port 3000
    python run_server.py --debug            # Enable debug logging
    python run_server.py --check            # Validate configuration only
"""

import os
import sys
import subprocess
from pathlib import Path

# Add the src directory to Python path for development
project_root = Path(__file__).parent
src_path = project_root / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))

def setup_demo_environment():
    """Setup demo environment variables if not already configured."""
    demo_vars = {
        # Core server configuration
        "LOG_LEVEL": "INFO",
        "LOG_FORMAT": "console",
        
        # Demo SkyFi configuration (user needs to provide real API key)
        "SKYFI_URL": "https://app.skyfi.com/platform-api",
        # "SKYFI_API_KEY": "your_api_key_here",  # User must set this
        
        # OSM configuration (always available)
        "OSM_URL": "https://nominatim.openstreetmap.org",
        "OSM_USER_AGENT": "SkyFi-MCP-Demo/1.0",
        
        # Demo weather configuration (user needs API key)
        "WEATHER_URL": "https://api.openweathermap.org/data/2.5",
        # "WEATHER_API_KEY": "your_weather_api_key_here",  # User must set this
        
        # Development settings
        "DEBUG": "false",
        "READ_ONLY_MODE": "false",
    }
    
    # Only set variables that aren't already configured
    for key, value in demo_vars.items():
        if key not in os.environ:
            os.environ[key] = value

def check_requirements():
    """Check if required packages are installed."""
    required_packages = [
        "fastmcp",
        "httpx",
        "pydantic", 
        "click",
        "rich",
        "uvicorn",
        "structlog"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   • {package}")
        print("\n💡 Install with: pip install -e .")
        return False
    
    return True

def display_quick_start_info():
    """Display quick start information and configuration tips."""
    print("🛰️  SkyFi MCP Server - Quick Start")
    print("=" * 50)
    print()
    
    # Check for API key configuration
    skyfi_key = os.environ.get("SKYFI_API_KEY")
    weather_key = os.environ.get("WEATHER_API_KEY")
    
    if not skyfi_key:
        print("⚠️  SkyFi API Key not configured:")
        print("   export SKYFI_API_KEY='your_api_key_here'")
        print("   Get your key: https://app.skyfi.com/platform/settings/api-keys")
        print()
    
    if not weather_key:
        print("⚠️  Weather API Key not configured (optional):")
        print("   export WEATHER_API_KEY='your_weather_api_key_here'")
        print("   Get your key: https://openweathermap.org/api")
        print()
    
    available_services = []
    if skyfi_key:
        available_services.append("SkyFi Platform")
    available_services.append("OpenStreetMap")  # Always available
    if weather_key:
        available_services.append("Weather Data")
    
    print(f"🔧 Available services: {', '.join(available_services)}")
    print()
    
    print("🚀 Example usage:")
    print("   python run_server.py                # STDIO transport")
    print("   python run_server.py --http         # HTTP on localhost:8000")
    print("   python run_server.py --debug        # Enable debug logging")
    print("   python run_server.py --check        # Validate configuration")
    print()

def main():
    """Main entry point for the quick server runner."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Quick runner for SkyFi MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_server.py                    # STDIO transport
  python run_server.py --http             # HTTP transport  
  python run_server.py --sse --port 3000  # SSE on port 3000
  python run_server.py --debug            # Debug logging
  python run_server.py --check            # Configuration check
        """
    )
    
    # Transport options
    transport_group = parser.add_mutually_exclusive_group()
    transport_group.add_argument(
        "--stdio", action="store_true", default=True,
        help="Use STDIO transport (default)"
    )
    transport_group.add_argument(
        "--http", action="store_true",
        help="Use HTTP transport"
    )
    transport_group.add_argument(
        "--sse", action="store_true", 
        help="Use Server-Sent Events transport"
    )
    
    # Server options
    parser.add_argument(
        "--host", default="localhost",
        help="Host for HTTP/SSE transport (default: localhost)"
    )
    parser.add_argument(
        "--port", type=int, default=8000,
        help="Port for HTTP/SSE transport (default: 8000)"
    )
    
    # Logging options
    parser.add_argument(
        "--debug", action="store_true",
        help="Enable debug logging"
    )
    parser.add_argument(
        "--log-format", choices=["json", "console", "simple"],
        help="Log format (default: console)"
    )
    
    # Utility options
    parser.add_argument(
        "--check", action="store_true",
        help="Check configuration and exit"
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress startup information"
    )
    parser.add_argument(
        "--no-demo-config", action="store_true",
        help="Don't setup demo environment variables"
    )
    
    args = parser.parse_args()
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Setup demo environment if not disabled
    if not args.no_demo_config:
        setup_demo_environment()
    
    # Display quick start info unless quiet
    if not args.quiet and not args.check:
        display_quick_start_info()
    
    # Determine transport
    if args.http:
        transport = "http"
    elif args.sse:
        transport = "sse" 
    else:
        transport = "stdio"
    
    # Build command arguments
    cmd_args = [sys.executable, "-m", "mcp_skyfi"]
    
    # Add transport
    cmd_args.extend(["--transport", transport])
    
    # Add host/port for HTTP/SSE
    if transport in ["http", "sse"]:
        cmd_args.extend(["--host", args.host])
        cmd_args.extend(["--port", str(args.port)])
    
    # Add logging options
    if args.debug:
        cmd_args.extend(["--log-level", "DEBUG"])
    
    if args.log_format:
        cmd_args.extend(["--log-format", args.log_format])
    
    # Add utility options
    if args.check:
        cmd_args.append("--config-check")
    
    if args.quiet:
        cmd_args.append("--quiet")
    
    # Execute the server
    try:
        print(f"🚀 Starting server with: {' '.join(cmd_args[2:])}")
        print()
        
        # Run the actual MCP server
        result = subprocess.run(cmd_args, cwd=project_root)
        sys.exit(result.returncode)
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"💥 Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()