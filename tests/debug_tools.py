#!/usr/bin/env python3
"""
Debug tool discovery in the MCP server.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add the src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Set environment variables
os.environ.update({
    "SKYFI_API_KEY": "lucas@skyfi.com:4068b1eeebe3654ab5fba6b8d662157cad4049f7346cfce0f86901beb6084b62",
    "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing",
    "LOG_LEVEL": "DEBUG"
})

async def debug_tool_discovery():
    """Debug tool discovery without full server startup."""
    
    try:
        # Import the server
        from mcp_skyfi.servers.main import main_mcp
        
        print("🔍 Server imported successfully")
        
        # Try to get tools directly
        print("🔧 Attempting to get tools...")
        tools = await main_mcp.get_tools()
        
        print(f"✅ Found {len(tools)} tools:")
        for tool_name, tool_obj in tools.items():
            print(f"  🔧 {tool_name}: {type(tool_obj)}")
            if hasattr(tool_obj, 'description'):
                print(f"     Description: {tool_obj.description}")
            if hasattr(tool_obj, 'tags'):
                print(f"     Tags: {tool_obj.tags}")
        
        # Try the MCP tool listing method
        print("\n🔍 Testing MCP tool listing...")
        
        # Create a mock request context for testing
        class MockContext:
            lifespan_context = {"app_lifespan_context": None}
        
        class MockServer:
            request_context = MockContext()
        
        main_mcp._mcp_server = MockServer()
        
        # This will fail but show us what's happening
        try:
            mcp_tools = await main_mcp._mcp_list_tools()
            print(f"✅ MCP tool listing successful: {len(mcp_tools)} tools")
            for tool in mcp_tools:
                print(f"  📋 {tool.get('name', 'Unknown')}")
        except Exception as e:
            print(f"❌ MCP tool listing failed: {e}")
        
    except Exception as e:
        print(f"💥 Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_tool_discovery())