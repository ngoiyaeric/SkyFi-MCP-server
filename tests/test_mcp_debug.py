import json
import subprocess
import sys
import time

# Start MCP server
proc = subprocess.Popen(
    [sys.executable, "-m", "mcp_skyfi", "--transport", "stdio"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

try:
    # Wait for server to fully start
    time.sleep(2)
    
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
    
    print("Sending:", json.dumps(init_request))
    proc.stdin.write(json.dumps(init_request) + '\n')
    proc.stdin.flush()
    
    # Read multiple lines to see what's coming back
    print("\nReading responses...")
    for i in range(5):
        line = proc.stdout.readline()
        if line:
            print(f"Line {i}: {line.strip()}")
            try:
                data = json.loads(line)
                print(f"Parsed: {json.dumps(data, indent=2)}")
            except:
                print(f"Not JSON: {line}")
        else:
            print(f"Line {i}: (empty)")
    
    # Also check stderr
    print("\nStderr output:")
    stderr = proc.stderr.read()
    if stderr:
        print(stderr)
    
finally:
    proc.terminate()
