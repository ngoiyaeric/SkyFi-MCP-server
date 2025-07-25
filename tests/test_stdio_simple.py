import subprocess
import json
import sys

def send_request(proc, request):
    """Send request and get response"""
    proc.stdin.write(json.dumps(request) + "\n")
    proc.stdin.flush()
    response_line = proc.stdout.readline()
    return json.loads(response_line)

# Start server
proc = subprocess.Popen(
    [sys.executable, "-m", "mcp_skyfi", "--transport", "stdio"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

try:
    # Initialize
    print("🚀 Initializing...")
    init_response = send_request(proc, {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "1.0",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1.0"}
        },
        "id": 1
    })
    print(f"✅ Server: {init_response['result']['serverInfo']['name']}")
    
    # List tools
    print("\n📋 Available Tools:")
    tools_response = send_request(proc, {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": 2
    })
    
    for tool in tools_response['result']['tools']:
        print(f"  • {tool['name']}")
    
    # Test whoami
    print("\n🔍 Testing whoami...")
    whoami_response = send_request(proc, {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "skyfi_user_whoami",
            "arguments": {}
        },
        "id": 3
    })
    print(whoami_response['result'])
    
finally:
    proc.terminate()