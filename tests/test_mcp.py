#!/usr/bin/env python3
import httpx
import json
from typing import Dict, Any

def extract_sse_data(response_text: str) -> Dict[str, Any]:
    """Extract JSON data from SSE response"""
    for line in response_text.strip().split('\n'):
        if line.startswith('data: '):
            return json.loads(line[6:])
    return {}

# Create client
client = httpx.Client(
    base_url="http://localhost:8000",
    headers={
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json"
    }
)

# Initialize
print("🚀 Initializing MCP Server...")
response = client.post("/mcp/v1/initialize", json={
    "jsonrpc": "2.0",
    "method": "initialize",
    "params": {
        "protocolVersion": "1.0",
        "capabilities": {},
        "clientInfo": {"name": "test-client", "version": "1.0"}
    },
    "id": 1
})
init_data = extract_sse_data(response.text)
print(f"✅ Server: {init_data['result']['serverInfo']['name']} v{init_data['result']['serverInfo']['version']}")

# List tools
print("\n📋 Available Tools:")
response = client.post("/mcp/v1/tools/list", json={
    "jsonrpc": "2.0",
    "method": "tools/list",
    "params": {},
    "id": 2
})
tools_data = extract_sse_data(response.text)
for tool in tools_data['result']['tools']:
    print(f"  • {tool['name']}: {tool['description']}")

# Test a tool (example: whoami)
print("\n🔍 Testing skyfi_user_whoami tool...")
response = client.post("/mcp/v1/tools/call", json={
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "skyfi_user_whoami",
        "arguments": {}
    },
    "id": 3
})
result_data = extract_sse_data(response.text)
if 'result' in result_data:
    print(result_data['result'])
else:
    print("Error:", result_data.get('error', 'Unknown error'))