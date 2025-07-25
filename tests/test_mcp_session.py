#!/usr/bin/env python3
import httpx
import json
from typing import Dict, Any, Optional

class MCPClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.client = httpx.Client(
            base_url=base_url,
            headers={
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json"
            }
        )
        self.session_id: Optional[str] = None
    
    def extract_sse_data(self, response_text: str) -> Dict[str, Any]:
        """Extract JSON data from SSE response"""
        for line in response_text.strip().split('\n'):
            if line.startswith('data: '):
                return json.loads(line[6:])
        return {}
    
    def initialize(self) -> Dict[str, Any]:
        """Initialize the MCP session"""
        response = self.client.post("/mcp/v1/initialize", json={
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "1.0",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0"}
            },
            "id": 1
        })
        
        # Extract session ID from cookies or headers
        self.session_id = response.cookies.get('session_id')
        if not self.session_id:
            # Check for session ID in response headers
            self.session_id = response.headers.get('X-Session-ID')
        
        return self.extract_sse_data(response.text)
    
    def call_method(self, method: str, params: Dict[str, Any] = None, id: int = 1) -> Dict[str, Any]:
        """Call an MCP method with session handling"""
        request_data = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": id
        }
        
        # Add session ID if available
        headers = {}
        if self.session_id:
            headers['X-Session-ID'] = self.session_id
        
        response = self.client.post(
            f"/mcp/v1/{method}",
            json=request_data,
            headers=headers
        )
        
        # Handle both SSE and regular JSON responses
        if response.headers.get('content-type', '').startswith('text/event-stream'):
            return self.extract_sse_data(response.text)
        else:
            return response.json()

# Test the MCP server
client = MCPClient()

print("🚀 Initializing MCP Server...")
init_result = client.initialize()
print(f"✅ Server: {init_result['result']['serverInfo']['name']} v{init_result['result']['serverInfo']['version']}")
print(f"📍 Session ID: {client.session_id}")

print("\n📋 Listing Available Tools...")
tools_result = client.call_method("tools/list", {}, 2)

if 'error' in tools_result:
    print(f"❌ Error: {tools_result['error']['message']}")
    print("\nTrying alternative approach...")
    
    # Try calling with session in params
    tools_result = client.call_method("tools/list", {"sessionId": client.session_id}, 3)

if 'result' in tools_result and 'tools' in tools_result['result']:
    print(f"Found {len(tools_result['result']['tools'])} tools:\n")
    for tool in tools_result['result']['tools']:
        print(f"  • {tool['name']}: {tool['description']}")
else:
    print("Could not retrieve tools. Response:", tools_result)

# Test whoami
print("\n🔍 Testing skyfi_user_whoami tool...")
whoami_result = client.call_method("tools/call", {
    "name": "skyfi_user_whoami",
    "arguments": {}
}, 4)

if 'result' in whoami_result:
    print(whoami_result['result'])
else:
    print("Error:", whoami_result.get('error', 'Unknown error'))