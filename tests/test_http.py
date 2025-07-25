#!/usr/bin/env python3
import httpx
import json

# Test basic health
print("🏥 Testing health endpoint...")
response = httpx.get("http://localhost:8000/healthz")
health = response.json()
print(f"Health: {health}")
print(f"  SkyFi: {'✅' if health['services']['skyfi'] else '❌'}")
print(f"  OSM: {'✅' if health['services']['osm'] else '❌'}")
print(f"  Weather: {'✅' if health['services']['weather'] else '❌'}")

# If healthy, test MCP
if any(health['services'].values()):
    print("\n🚀 Testing MCP initialization...")
    client = httpx.Client(
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
    )
    
    response = client.post(
        "http://localhost:8000/mcp/v1/initialize",
        json={
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "1.0",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"}
            },
            "id": 1
        }
    )
    
    # Parse SSE response
    for line in response.text.strip().split('\n'):
        if line.startswith('data: '):
            data = json.loads(line[6:])
            print(f"✅ Server: {data['result']['serverInfo']['name']} v{data['result']['serverInfo']['version']}")
else:
    print("\n❌ No services are healthy. Check your configuration!")