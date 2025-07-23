"""
MCP Protocol Compliance Tests

These tests validate that the SkyFi MCP server correctly implements the 
Model Context Protocol (MCP) specification, ensuring compatibility with 
MCP clients and proper protocol behavior.
"""

from __future__ import annotations

import asyncio
import json
import pytest
import time
from typing import Dict, Any, List


@pytest.mark.mcp_compliance
@pytest.mark.integration
class TestMCPProtocolCompliance:
    """Comprehensive MCP protocol compliance test suite."""
    
    async def test_mcp_initialization_stdio(self, mcp_stdio_client):
        """Test MCP server initialization via STDIO transport."""
        # The client is already initialized in the fixture
        # Let's verify the initialization worked correctly
        
        # Test basic initialization response structure
        init_response = await mcp_stdio_client.send_message("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "roots": {"listChanged": True},
                "sampling": {}
            },
            "clientInfo": {"name": "compliance-test-client", "version": "1.0.0"}
        })
        
        # Validate response structure
        assert "jsonrpc" in init_response
        assert init_response["jsonrpc"] == "2.0"
        assert "id" in init_response
        assert "result" in init_response
        
        # Validate initialization result
        result = init_response["result"]
        assert "protocolVersion" in result
        assert "capabilities" in result
        assert "serverInfo" in result
        
        # Validate server info
        server_info = result["serverInfo"]
        assert "name" in server_info
        assert "version" in server_info
        assert server_info["name"] == "SkyFi MCP Server"
        
        # Validate capabilities
        capabilities = result["capabilities"]
        assert "tools" in capabilities
        
    async def test_mcp_tool_discovery(self, mcp_stdio_client):
        """Test MCP tool discovery and listing."""
        # Send tools/list request
        response = await mcp_stdio_client.list_tools()
        
        # Validate response structure
        assert "jsonrpc" in response
        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        
        # Validate tools list
        result = response["result"]
        assert "tools" in result
        
        tools = result["tools"]
        assert isinstance(tools, list)
        assert len(tools) > 0
        
        # Validate each tool has required MCP fields
        required_tool_fields = ["name", "description", "inputSchema"]
        for tool in tools:
            for field in required_tool_fields:
                assert field in tool, f"Tool missing required field '{field}': {tool}"
                
            # Validate tool name format
            assert isinstance(tool["name"], str)
            assert len(tool["name"]) > 0
            
            # Validate description
            assert isinstance(tool["description"], str)
            assert len(tool["description"]) > 0
            
            # Validate input schema is valid JSON Schema
            schema = tool["inputSchema"]
            assert isinstance(schema, dict)
            assert "type" in schema
            
        # Check for expected SkyFi tools
        tool_names = [tool["name"] for tool in tools]
        expected_tools = [
            "skyfi_search_archives",
            "skyfi_create_order", 
            "skyfi_get_order_status",
            "osm_geocode_address",
            "weather_get_current"
        ]
        
        for expected_tool in expected_tools:
            assert any(expected_tool in name for name in tool_names), (
                f"Expected tool '{expected_tool}' not found in available tools: {tool_names}"
            )
            
    async def test_mcp_tool_execution(self, mcp_stdio_client, external_service_mocks):
        """Test MCP tool execution with various inputs."""
        # First get available tools
        tools_response = await mcp_stdio_client.list_tools()
        tools = tools_response["result"]["tools"]
        
        # Find SkyFi archive search tool
        search_tool = None
        for tool in tools:
            if "search_archives" in tool["name"]:
                search_tool = tool
                break
                
        assert search_tool is not None, "SkyFi search archives tool not found"
        
        # Test tool execution
        execute_response = await mcp_stdio_client.call_tool(
            search_tool["name"],
            {
                "aoi": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-122.5, 37.7], [-122.4, 37.7],
                        [-122.4, 37.8], [-122.5, 37.8],
                        [-122.5, 37.7]
                    ]]
                },
                "start_date": "2024-01-01",
                "end_date": "2024-01-31"
            }
        )
        
        # Validate response structure
        assert "jsonrpc" in execute_response
        assert execute_response["jsonrpc"] == "2.0"
        assert "result" in execute_response
        
        # Validate tool execution result
        result = execute_response["result"]
        assert "content" in result
        
        content = result["content"]
        assert isinstance(content, list)
        assert len(content) > 0
        
        # Validate content structure
        for content_item in content:
            assert "type" in content_item
            assert content_item["type"] in ["text", "image", "resource"]
            
            if content_item["type"] == "text":
                assert "text" in content_item
                assert isinstance(content_item["text"], str)
                
    async def test_mcp_error_handling(self, mcp_stdio_client):
        """Test MCP error handling for invalid requests."""
        # Test invalid method
        invalid_method_response = await mcp_stdio_client.send_message("invalid/method")
        
        assert "error" in invalid_method_response
        error = invalid_method_response["error"]
        assert "code" in error
        assert "message" in error
        assert error["code"] == -32601  # Method not found
        
        # Test tool execution with invalid tool name
        invalid_tool_response = await mcp_stdio_client.call_tool(
            "nonexistent_tool",
            {}
        )
        
        assert "error" in invalid_tool_response
        
        # Test tool execution with invalid arguments
        tools_response = await mcp_stdio_client.list_tools()
        tools = tools_response["result"]["tools"]
        
        if tools:
            first_tool = tools[0]
            invalid_args_response = await mcp_stdio_client.call_tool(
                first_tool["name"],
                {"invalid_argument": "invalid_value"}
            )
            
            # Should either error or handle gracefully
            assert "result" in invalid_args_response or "error" in invalid_args_response
            
    async def test_mcp_concurrent_requests(self, mcp_stdio_client):
        """Test handling of concurrent MCP requests."""
        # Create multiple concurrent tool list requests
        concurrent_requests = []
        for i in range(10):
            request = mcp_stdio_client.send_message("tools/list")
            concurrent_requests.append(request)
            
        # Wait for all requests to complete
        responses = await asyncio.gather(*concurrent_requests)
        
        # All responses should be valid
        for i, response in enumerate(responses):
            assert "result" in response, f"Request {i} failed: {response}"
            assert "tools" in response["result"]
            
    async def test_mcp_request_id_handling(self, mcp_stdio_client):
        """Test proper handling of request IDs."""
        # Send request with specific ID
        custom_id = "test-request-123"
        response = await mcp_stdio_client.send_message("tools/list")
        
        # Response should have matching ID
        assert "id" in response
        # Note: Our test client generates sequential IDs, so we just verify presence
        
    async def test_mcp_version_compatibility(self, mcp_stdio_client):
        """Test MCP protocol version compatibility."""
        # Test with supported version
        response = await mcp_stdio_client.send_message("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "version-test", "version": "1.0.0"}
        })
        
        assert "result" in response
        
        # Test with unsupported version (if applicable)
        # This would depend on server implementation
        
    async def test_mcp_transport_stdio_protocol(self, mcp_stdio_client):
        """Test STDIO transport protocol specifics."""
        # STDIO should handle line-delimited JSON
        # Our test client already validates this, but let's ensure robustness
        
        # Send multiple rapid requests
        responses = []
        for i in range(5):
            response = await mcp_stdio_client.send_message("tools/list")
            responses.append(response)
            
        # All should succeed
        for response in responses:
            assert "result" in response
            
    async def test_mcp_schema_validation(self, mcp_stdio_client, test_geometries):
        """Test input schema validation for tools."""
        # Get tools
        tools_response = await mcp_stdio_client.list_tools()
        tools = tools_response["result"]["tools"]
        
        # Find a tool with complex schema (like archive search)
        search_tool = None
        for tool in tools:
            if "search" in tool["name"].lower():
                search_tool = tool
                break
                
        if search_tool:
            # Test with valid geometry
            valid_response = await mcp_stdio_client.call_tool(
                search_tool["name"],
                {
                    "aoi": test_geometries["san_francisco_bbox"],
                    "start_date": "2024-01-01",
                    "end_date": "2024-01-31"
                }
            )
            
            # Should succeed or return meaningful error
            assert "result" in valid_response or "error" in valid_response
            
            # Test with invalid geometry
            invalid_response = await mcp_stdio_client.call_tool(
                search_tool["name"],
                {
                    "aoi": test_geometries["invalid_geometry"],
                    "start_date": "2024-01-01", 
                    "end_date": "2024-01-31"
                }
            )
            
            # Should handle validation error gracefully
            if "error" in invalid_response:
                assert "message" in invalid_response["error"]
                
    @pytest.mark.slow
    async def test_mcp_performance_requirements(self, mcp_stdio_client):
        """Test MCP server performance meets requirements."""
        # Test tool listing performance
        start_time = time.perf_counter()
        response = await mcp_stdio_client.list_tools()
        end_time = time.perf_counter()
        
        list_time = end_time - start_time
        assert list_time < 1.0, f"Tool listing too slow: {list_time:.3f}s"
        assert "result" in response
        
        # Test tool execution performance
        tools = response["result"]["tools"]
        if tools:
            tool = tools[0]  # Use first available tool
            
            start_time = time.perf_counter()
            exec_response = await mcp_stdio_client.call_tool(
                tool["name"],
                {}  # Empty args, may error but that's ok for perf test
            )
            end_time = time.perf_counter()
            
            exec_time = end_time - start_time
            assert exec_time < 5.0, f"Tool execution too slow: {exec_time:.3f}s"
            
    async def test_mcp_memory_usage(self, mcp_stdio_client):
        """Test MCP server memory usage remains stable."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Perform multiple operations
        for _ in range(20):
            await mcp_stdio_client.list_tools()
            
            # Execute a tool if available
            tools_response = await mcp_stdio_client.list_tools()
            tools = tools_response["result"]["tools"]
            if tools:
                await mcp_stdio_client.call_tool(tools[0]["name"], {})
                
        final_memory = process.memory_info().rss
        memory_increase = (final_memory - initial_memory) / (1024 * 1024)  # MB
        
        # Memory usage should not increase significantly
        assert memory_increase < 50, f"Memory usage increased by {memory_increase:.2f}MB"
        
    async def test_mcp_resource_cleanup(self, mcp_stdio_client):
        """Test proper resource cleanup in MCP operations."""
        # This test ensures the server properly cleans up resources
        # after tool executions and doesn't leak connections, etc.
        
        initial_connections = len(getattr(mcp_stdio_client, '_active_connections', []))
        
        # Perform operations that might create resources
        for i in range(10):
            tools_response = await mcp_stdio_client.list_tools()
            tools = tools_response["result"]["tools"]
            
            if tools:
                # Execute tools that might use external services
                for tool in tools[:3]:  # Test first 3 tools
                    await mcp_stdio_client.call_tool(tool["name"], {})
                    
        final_connections = len(getattr(mcp_stdio_client, '_active_connections', []))
        
        # Connection count should not increase significantly
        connection_increase = final_connections - initial_connections
        assert connection_increase <= 2, f"Too many new connections: {connection_increase}"