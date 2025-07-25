import json
import subprocess
import sys
import time

def send_request(proc, request):
    """Send a request and get response"""
    proc.stdin.write(json.dumps(request) + '\n')
    proc.stdin.flush()
    response = proc.stdout.readline()
    return json.loads(response)

# Start MCP server
proc = subprocess.Popen(
    [sys.executable, "-m", "mcp_skyfi", "--transport", "stdio"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
    text=True,
    bufsize=1
)

try:
    time.sleep(1)
    
    # Initialize request
    init_request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        },
        "id": 1
    }
    
    print("Sending initialize request...")
    init_response = send_request(proc, init_request)
    print("Initialize response:", json.dumps(init_response, indent=2))
    
    # Initialized notification
    initialized_notif = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
        "params": {}
    }
    proc.stdin.write(json.dumps(initialized_notif) + '\n')
    proc.stdin.flush()
    time.sleep(0.5)
    
    # List tools
    tools_request = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": 2
    }
    
    print("\nSending tools/list request...")
    tools_response = send_request(proc, tools_request)
    print("Tools response:", json.dumps(tools_response, indent=2))
    
finally:
    proc.terminate()
