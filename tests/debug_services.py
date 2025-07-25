#!/usr/bin/env python3
"""
Debug individual service modules to understand tool registration.
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
    "SKYFI_API_KEY": os.environ.get("SKYFI_API_KEY", "your_test_api_key_here"),
    "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing",
    "OSM_URL": "https://nominatim.openstreetmap.org",
    "OSM_USER_AGENT": "SkyFi-MCP-Test/1.0",
    "LOG_LEVEL": "DEBUG"
})

async def debug_individual_services():
    """Debug each service individually."""
    
    print("🔍 Debugging individual services...")
    
    try:
        # Test SkyFi service
        print("\n🛰️ Testing SkyFi service...")
        from mcp_skyfi.skyfi import skyfi_mcp
        
        skyfi_tools = await skyfi_mcp.get_tools()
        print(f"SkyFi tools: {len(skyfi_tools)}")
        for tool_name, tool_obj in skyfi_tools.items():
            print(f"  🔧 {tool_name}: {tool_obj.description if hasattr(tool_obj, 'description') else 'No description'}")
        
        # Test OSM service
        print("\n🗺️ Testing OSM service...")
        from mcp_skyfi.osm import osm_mcp
        
        osm_tools = await osm_mcp.get_tools()
        print(f"OSM tools: {len(osm_tools)}")
        for tool_name, tool_obj in osm_tools.items():
            print(f"  🔧 {tool_name}: {tool_obj.description if hasattr(tool_obj, 'description') else 'No description'}")
        
        # Test Weather service
        print("\n🌤️ Testing Weather service...")
        from mcp_skyfi.weather import weather_mcp
        
        weather_tools = await weather_mcp.get_tools()
        print(f"Weather tools: {len(weather_tools)}")
        for tool_name, tool_obj in weather_tools.items():
            print(f"  🔧 {tool_name}: {tool_obj.description if hasattr(tool_obj, 'description') else 'No description'}")
        
        # Total count
        total_tools = len(skyfi_tools) + len(osm_tools) + len(weather_tools)
        print(f"\n📊 Total tools across all services: {total_tools}")
        
        if total_tools == 0:
            print("❌ No tools found in any service - this indicates a registration issue")
        
    except Exception as e:
        print(f"💥 Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_individual_services())