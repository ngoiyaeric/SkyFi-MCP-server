#!/usr/bin/env python3
"""
Simple MCP test to validate the actual working configuration.
"""

import json
import subprocess
import sys
import os
import time
from pathlib import Path

def run_simple_mcp_test():
    """Run a simple MCP test that works with Claude/Cursor."""
    
    print("🧪 Testing MCP Server like Claude/Cursor would...")
    
    # Set up environment exactly like the JSON config
    env = os.environ.copy()
    env.update({
        "SKYFI_API_KEY": "lucas@skyfi.com:4068b1eeebe3654ab5fba6b8d662157cad4049f7346cfce0f86901beb6084b62",
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing"
    })
    
    # Run exactly like the MCP config specifies
    cmd = ["python", "-m", "mcp_skyfi"]
    
    print(f"🚀 Command: {' '.join(cmd)}")
    print(f"📁 Working dir: {Path.cwd()}")
    
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
    time.sleep(2)
    
    try:
        # Test sequence that should work
        messages = [
            # 1. Initialize
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "claude-test",
                        "version": "1.0.0"
                    }
                }
            },
            # 2. Initialized notification
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {}
            },
            # 3. List tools
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }
        ]
        
        responses = []
        
        for i, msg in enumerate(messages):
            print(f"📤 Sending message {i+1}: {msg['method']}")
            
            # Send message
            process.stdin.write(json.dumps(msg) + "\n")
            process.stdin.flush()
            
            # For notifications, don't expect a response
            if msg.get("method") == "notifications/initialized":
                time.sleep(0.5)
                continue
            
            # Read response
            try:
                response_line = process.stdout.readline().strip()
                if response_line:
                    response = json.loads(response_line)
                    responses.append(response)
                    print(f"📥 Response {i+1}: {json.dumps(response, indent=2)}")
                else:
                    print(f"❌ No response for message {i+1}")
            except json.JSONDecodeError as e:
                print(f"❌ JSON decode error for message {i+1}: {e}")
                print(f"Raw response: {response_line}")
        
        # Check if we got tools
        if len(responses) >= 2:  # init response + tools response
            tools_response = responses[1]
            if "result" in tools_response and "tools" in tools_response["result"]:
                tools = tools_response["result"]["tools"]
                print(f"✅ Found {len(tools)} tools!")
                for tool in tools:
                    print(f"  🔧 {tool['name']}: {tool.get('description', 'No description')}")
            else:
                print("❌ No tools found in response")
        else:
            print("❌ Insufficient responses received")
            
    except Exception as e:
        print(f"💥 Test error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Check for stderr output
        stderr_output = ""
        try:
            stderr_output = process.stderr.read()
            if stderr_output:
                print(f"🚨 Server stderr:\n{stderr_output}")
        except:
            pass
        
        # Clean up
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()

if __name__ == "__main__":
    run_simple_mcp_test()