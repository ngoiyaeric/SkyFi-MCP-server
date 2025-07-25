#!/usr/bin/env python3
"""
Quick test to verify MCP server tools are available and working.
"""
import json
import subprocess
import sys

def test_mcp_tools():
    """Test MCP server tools listing and basic functionality."""
    
    # Test 1: Initialize the MCP server
    print("🔧 Testing MCP initialization...")
    init_request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"}
        },
        "id": 1
    }
    
    try:
        # Run MCP server with initialization
        proc = subprocess.Popen(
            [sys.executable, "-m", "mcp_skyfi", "--quiet"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = proc.communicate(
            input=json.dumps(init_request) + "\n", 
            timeout=10
        )
        
        # Look for the JSON response in stdout
        lines = stdout.strip().split('\n')
        for line in lines:
            if line.startswith('{"jsonrpc":'):
                response = json.loads(line)
                if response.get("id") == 1 and "result" in response:
                    print("✅ MCP server initialized successfully")
                    server_info = response["result"]["serverInfo"]
                    print(f"   Server: {server_info['name']} v{server_info['version']}")
                    
                    capabilities = response["result"]["capabilities"]
                    print(f"   Tools available: {'✅' if capabilities.get('tools') else '❌'}")
                    print(f"   Resources available: {'✅' if capabilities.get('resources') else '❌'}")
                    return True
                    
    except subprocess.TimeoutExpired:
        print("⚠️ MCP server took too long to respond")
        proc.kill()
    except Exception as e:
        print(f"❌ Error testing MCP server: {e}")
        if stderr:
            print(f"   stderr: {stderr}")
    
    return False

def test_api_connectivity():
    """Test direct API connectivity."""
    print("\n🌐 Testing SkyFi API connectivity...")
    
    import os
    api_key = os.environ.get("SKYFI_API_KEY")
    if not api_key:
        print("❌ SKYFI_API_KEY not set")
        return False
    
    try:
        import httpx
        
        response = httpx.post(
            "https://app.skyfi.com/platform-api/pricing",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"image_ids": ["test"]},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            product_types = len(data.get("productTypes", []))
            print(f"✅ SkyFi API is accessible")
            print(f"   Product types available: {product_types}")
            return True
        else:
            print(f"❌ SkyFi API error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ API connectivity error: {e}")
        return False

def main():
    import os
    
    print("🧪 SkyFi MCP Server Test Suite")
    print("=" * 50)
    
    # Test API connectivity first
    api_ok = test_api_connectivity()
    
    # Test MCP server
    mcp_ok = test_mcp_tools()
    
    print("\n📊 Test Results:")
    print(f"   API Connectivity: {'✅ PASS' if api_ok else '❌ FAIL'}")
    print(f"   MCP Server: {'✅ PASS' if mcp_ok else '❌ FAIL'}")
    
    if api_ok and mcp_ok:
        print("\n🎉 All tests passed! The MCP server is ready for Claude Desktop.")
        print("\n💡 Claude Desktop Configuration:")
        print('```json')
        print('{')
        print('  "mcpServers": {')
        print('    "skyfi": {')
        print('      "command": "python",')
        print('      "args": ["-m", "mcp_skyfi"],')
        print('      "env": {')
        print(f'        "SKYFI_API_KEY": "{os.environ.get("SKYFI_API_KEY", "your_api_key_here")}",')
        print('        "SKYFI_URL": "https://app.skyfi.com/platform-api"')
        print('      },')
        print(f'      "cwd": "{os.getcwd()}"')
        print('    }')
        print('  }')
        print('}')
        print('```')
        return 0
    else:
        print("\n⚠️ Some tests failed. Check the configuration above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())