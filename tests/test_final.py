#!/usr/bin/env python3
"""
Final test of the fixed MCP server.
"""

import json
import subprocess
import sys
import os
import time
from pathlib import Path

def test_final_mcp():
    """Test the fixed MCP server with proper initialization."""
    
    print("🧪 Testing FIXED MCP Server...")
    
    # Set up environment exactly like Claude/Cursor
    env = os.environ.copy()
    env.update({
        "SKYFI_API_KEY": os.environ.get("SKYFI_API_KEY", "your_test_api_key_here"),
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing"
    })
    
    cmd = ["python", "-m", "mcp_skyfi"]
    
    print(f"🚀 Starting server: {' '.join(cmd)}")
    
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        cwd="/Users/pskinnertech/Dev/gai/skyfi/mcp"
    )
    
    # Give server time to start
    time.sleep(3)
    
    try:
        # Proper MCP handshake
        messages = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "test-client",
                        "version": "1.0.0"
                    }
                }
            },
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {}
            },
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }
        ]
        
        for i, msg in enumerate(messages):
            print(f"📤 Sending: {msg['method']}")
            process.stdin.write(json.dumps(msg) + "\n")
            process.stdin.flush()
            
            if msg.get("method") == "notifications/initialized":
                time.sleep(0.5)
                continue
            
            # Read response
            try:
                response_line = process.stdout.readline().strip()
                if response_line:
                    response = json.loads(response_line)
                    
                    if msg["method"] == "tools/list":
                        if "result" in response and "tools" in response["result"]:
                            tools = response["result"]["tools"]
                            print(f"🎉 SUCCESS! Found {len(tools)} tools:")
                            
                            # Group tools by service
                            skyfi_tools = [t for t in tools if t["name"].startswith("skyfi_")]
                            osm_tools = [t for t in tools if t["name"].startswith("osm_")]
                            weather_tools = [t for t in tools if t["name"].startswith("weather_")]
                            
                            print(f"  🛰️ SkyFi: {len(skyfi_tools)} tools")
                            for tool in skyfi_tools:
                                print(f"    - {tool['name']}")
                            
                            print(f"  🗺️ OSM: {len(osm_tools)} tools")
                            for tool in osm_tools:
                                print(f"    - {tool['name']}")
                            
                            print(f"  🌤️ Weather: {len(weather_tools)} tools")
                            for tool in weather_tools:
                                print(f"    - {tool['name']}")
                                
                            return True
                        else:
                            print("❌ No tools found in response")
                    else:
                        print(f"✅ Response: {response.get('result', 'OK')}")
                        
            except Exception as e:
                print(f"❌ Error reading response: {e}")
                
    except Exception as e:
        print(f"💥 Test failed: {e}")
        return False
        
    finally:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()

if __name__ == "__main__":
    success = test_final_mcp()
    sys.exit(0 if success else 1)