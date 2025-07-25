#!/usr/bin/env python3
"""
Test script to verify SkyFi MCP server works correctly with Cursor configuration.
"""
import json
import subprocess
import sys
import os

def test_cursor_mcp_config():
    """Test that Cursor MCP configuration is valid and server works."""
    
    print("🔧 Testing SkyFi MCP Server for Cursor IDE")
    print("=" * 50)
    
    # Test 1: Check if Cursor config file exists and is valid
    cursor_config_path = os.path.expanduser("~/.cursor/mcp.json")
    print(f"📂 Checking Cursor configuration: {cursor_config_path}")
    
    try:
        with open(cursor_config_path, 'r') as f:
            config = json.load(f)
        
        if "skyfi" in config.get("mcpServers", {}):
            skyfi_config = config["mcpServers"]["skyfi"]
            print("✅ SkyFi server found in Cursor configuration")
            print(f"   Command: {skyfi_config.get('command')}")
            print(f"   Args: {skyfi_config.get('args')}")
            print(f"   Working Directory: {skyfi_config.get('cwd')}")
            
            # Check environment variables
            env_vars = skyfi_config.get("env", {})
            api_key = env_vars.get("SKYFI_API_KEY")
            if api_key and ":" in api_key:
                print("✅ API key format is correct (email:token)")
            else:
                print("❌ API key format issue")
                return False
                
        else:
            print("❌ SkyFi server not found in Cursor configuration")
            return False
            
    except Exception as e:
        print(f"❌ Error reading Cursor configuration: {e}")
        return False
    
    # Test 2: Verify the MCP server can be started with Cursor's configuration
    print("\n🚀 Testing MCP server startup with Cursor config...")
    
    try:
        # Extract configuration details
        skyfi_config = config["mcpServers"]["skyfi"]
        command = skyfi_config["command"]
        args = skyfi_config["args"]
        env_vars = skyfi_config.get("env", {})
        cwd = skyfi_config.get("cwd")
        
        # Set up environment
        test_env = os.environ.copy()
        test_env.update(env_vars)
        
        # Create initialization request
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize", 
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "cursor-test", "version": "1.0.0"}
            },
            "id": 1
        }
        
        # Start server process
        proc = subprocess.Popen(
            [command] + args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=test_env,
            cwd=cwd
        )
        
        # Send initialization and get response
        stdout, stderr = proc.communicate(
            input=json.dumps(init_request) + "\n",
            timeout=15
        )
        
        # Parse response
        lines = stdout.strip().split('\n')
        for line in lines:
            if line.startswith('{"jsonrpc":'):
                response = json.loads(line)
                if response.get("id") == 1 and "result" in response:
                    server_info = response["result"]["serverInfo"]
                    capabilities = response["result"]["capabilities"]
                    
                    print("✅ MCP server initialized successfully")
                    print(f"   Server: {server_info['name']} v{server_info['version']}")
                    print(f"   Tools: {'✅' if capabilities.get('tools') else '❌'}")
                    print(f"   Resources: {'✅' if capabilities.get('resources') else '❌'}")
                    return True
        
        print("❌ Invalid response from MCP server")
        if stderr:
            print(f"   Error output: {stderr[:200]}...")
        return False
        
    except subprocess.TimeoutExpired:
        print("❌ MCP server startup timed out")
        proc.kill()
        return False
    except Exception as e:
        print(f"❌ Error testing MCP server: {e}")
        return False

def show_cursor_instructions():
    """Show instructions for using SkyFi MCP in Cursor."""
    print("\n📖 How to Use SkyFi MCP in Cursor IDE:")
    print("=" * 50)
    print()
    print("1. **Enable MCP in Cursor Settings:**")
    print("   • Open Cursor settings (Cmd/Ctrl + ,)")
    print("   • Search for 'MCP' or go to Features > Model Context Protocol")
    print("   • Enable 'Model Context Protocol'")
    print()
    print("2. **Restart Cursor:**")
    print("   • Close and reopen Cursor IDE")
    print("   • The SkyFi server will automatically load")
    print()
    print("3. **Verify MCP Tools are Available:**")
    print("   • Open Cursor's AI chat/composer")
    print("   • You should see SkyFi tools in the available tools list")
    print("   • Look for tools like 'skyfi_search_archives', 'skyfi_get_pricing', etc.")
    print()
    print("4. **Use SkyFi Tools:**")
    print("   • Ask Cursor to search for satellite imagery")
    print("   • Example: 'Find satellite images of San Francisco from last month'")
    print("   • Cursor will automatically use SkyFi tools when relevant")
    print()
    print("5. **Available SkyFi Capabilities:**")
    print("   • 🛰️  Search satellite archive imagery")
    print("   • 💰 Get pricing for satellite orders")
    print("   • 📍 Geocoding with OpenStreetMap")
    print("   • 🌤️  Weather data integration")
    print("   • 📋 Order management and tracking")
    print()

def main():
    """Main test function."""
    success = test_cursor_mcp_config()
    
    print("\n📊 Test Results:")
    if success:
        print("✅ PASS - SkyFi MCP server is ready for Cursor!")
        show_cursor_instructions()
        return 0
    else:
        print("❌ FAIL - Configuration needs fixing")
        print("\n💡 Troubleshooting:")
        print("1. Check that the MCP server path is correct")
        print("2. Verify API key format (should be email:token)")
        print("3. Ensure Python can find the mcp_skyfi module")
        print("4. Check that all dependencies are installed")
        return 1

if __name__ == "__main__":
    sys.exit(main())