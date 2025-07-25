import subprocess
import json
import sys
import time

def test_stdio():
    # Start server with error output
    proc = subprocess.Popen(
        [sys.executable, "-m", "mcp_skyfi", "--transport", "stdio"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    # Give server time to start
    time.sleep(2)
    
    # Check if process is still running
    if proc.poll() is not None:
        print("❌ Server failed to start")
        print("STDERR:", proc.stderr.read())
        return
    
    try:
        # Send initialize
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "1.0",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"}
            },
            "id": 1
        }
        
        print("🚀 Sending initialize request...")
        proc.stdin.write(json.dumps(request) + "\n")
        proc.stdin.flush()
        
        # Read response with timeout
        response_line = proc.stdout.readline()
        if response_line:
            print("✅ Got response:", response_line[:100] + "..." if len(response_line) > 100 else response_line)
            response = json.loads(response_line)
            print(f"📋 Server: {response['result']['serverInfo']['name']}")
        else:
            print("❌ No response from server")
            print("STDERR:", proc.stderr.read())
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("STDERR:", proc.stderr.read())
    finally:
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    test_stdio()