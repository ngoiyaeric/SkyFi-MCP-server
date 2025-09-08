#!/bin/sh
set -e

# Start the python MCP server in the background on port 8000
mcp-skyfi --transport http --port 8000 &

# Start nginx in the foreground
nginx -g 'daemon off;'
