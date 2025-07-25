#!/usr/bin/env python3
"""
Test MCP initialization sequence to debug the tool discovery issue.
"""

import json
import subprocess
import sys
import os
from pathlib import Path

def test_mcp_init_sequence():
    """Test the proper MCP initialization sequence."""
    
    # Set up environment
    env = os.environ.copy()
    env.update({
        "SKYFI_API_KEY": os.environ.get("SKYFI_API_KEY", "your_test_api_key_here"),
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing"
    })
    
    # Start MCP server process
    cmd = [sys.executable, "-m", "mcp_skyfi", "--transport", "stdio"]
    
    print("🚀 Starting MCP server process...")
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        cwd=str(Path(__file__).parent)
    )
    
    try:
        # Step 1: Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {
                        "listChanged": True
                    },
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        print("📤 Sending initialize request...")
        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()
        
        # Read initialization response
        print("📥 Reading initialize response...")
        response_line = process.stdout.readline()
        if response_line:
            init_response = json.loads(response_line)
            print(f"✅ Initialize response: {json.dumps(init_response, indent=2)}")
        
        # Step 2: Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        }
        
        print("📤 Sending initialized notification...")
        process.stdin.write(json.dumps(initialized_notification) + "\n")
        process.stdin.flush()
        
        # Step 3: Now request tools list
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        print("📤 Sending tools/list request...")
        process.stdin.write(json.dumps(tools_request) + "\n")
        process.stdin.flush()
        
        # Read tools response
        print("📥 Reading tools response...")
        response_line = process.stdout.readline()
        if response_line:
            tools_response = json.loads(response_line)
            print(f"✅ Tools response: {json.dumps(tools_response, indent=2)}")
            
            # Count tools
            if "result" in tools_response and "tools" in tools_response["result"]:
                tool_count = len(tools_response["result"]["tools"])
                print(f"🔧 Found {tool_count} tools available")
                
                # List tool names
                tool_names = [tool["name"] for tool in tools_response["result"]["tools"]]
                print(f"📋 Tool names: {', '.join(tool_names)}")
            else:
                print("❌ No tools found in response")
        
    except Exception as e:
        print(f"💥 Error during test: {e}")
        
    finally:
        # Clean up process
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

if __name__ == "__main__":
    test_mcp_init_sequence()