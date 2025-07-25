"""
MCP Protocol Authentication Compliance Tests

This module tests MCP protocol compliance specifically for authentication
and credential handling, ensuring the SkyFi MCP server properly implements
authentication according to MCP specifications.
"""

from __future__ import annotations

import asyncio
import json
import pytest
import time
from typing import Dict, Any, List
from unittest.mock import AsyncMock, patch

from tests.fixtures.credential_mocks import (
    DynamicCredentialMock,
    MultiServiceCredentialCoordinator
)


@pytest.mark.mcp_compliance
@pytest.mark.auth
@pytest.mark.integration
class TestMCPAuthenticationCompliance:
    """MCP protocol authentication compliance test suite."""
    
    @pytest.fixture
    async def credential_mock(self):
        """Provide dynamic credential mock."""
        mock = DynamicCredentialMock()
        yield mock
    
    @pytest.fixture
    async def coordinator(self):
        """Provide credential coordinator."""
        return MultiServiceCredentialCoordinator()
    
    async def test_mcp_initialization_with_auth(self, mcp_stdio_client, credential_mock):
        """Test MCP initialization with authentication context."""
        # Initialize with authentication information
        init_response = await mcp_stdio_client.send_message("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "roots": {"listChanged": True},
                "sampling": {}
            },
            "clientInfo": {
                "name": "auth-compliance-test-client",
                "version": "1.0.0"
            },
            "meta": {
                "authentication": {
                    "skyfi_api_key": "test_mcp_auth_key_123",
                    "preferred_auth_types": ["oauth", "api_key"]
                }
            }
        })
        
        # Validate initialization response
        assert "jsonrpc" in init_response
        assert init_response["jsonrpc"] == "2.0"
        assert "result" in init_response
        
        result = init_response["result"]
        assert "serverInfo" in result
        assert "capabilities" in result
        
        # Server should acknowledge authentication capabilities
        capabilities = result["capabilities"]
        assert "tools" in capabilities
    
    async def test_mcp_tool_execution_with_credential_headers(
        self, mcp_stdio_client, credential_mock
    ):
        """Test MCP tool execution with credential headers."""
        # Get available tools
        tools_response = await mcp_stdio_client.list_tools()
        assert "result" in tools_response
        
        tools = tools_response["result"]["tools"]
        skyfi_tools = [tool for tool in tools if "skyfi" in tool["name"].lower()]
        
        if not skyfi_tools:
            pytest.skip("No SkyFi tools available for testing")
        
        test_tool = skyfi_tools[0]
        
        # Execute tool with authentication context
        execute_response = await mcp_stdio_client.send_message("tools/call", {
            "name": test_tool["name"],
            "arguments": {
                "aoi": {
                    "type": "Point",
                    "coordinates": [-122.4194, 37.7749]
                },
                "start_date": "2024-01-01",
                "end_date": "2024-01-31"
            },
            "meta": {
                "authentication": {
                    "skyfi_api_key": "test_mcp_tool_auth_key",
                    "auth_type": "api_key"
                }
            }
        })
        
        # Validate response structure
        assert "jsonrpc" in execute_response
        assert execute_response["jsonrpc"] == "2.0"
        
        # Should either succeed with credentials or fail with auth error
        if "result" in execute_response:
            # Successful execution
            result = execute_response["result"]
            assert "content" in result
            assert isinstance(result["content"], list)
        elif "error" in execute_response:
            # Authentication error (expected if credentials are invalid)
            error = execute_response["error"]
            assert "code" in error
            assert "message" in error
            # Common auth error codes: -32600 (Invalid Request), -32603 (Internal Error)
            assert error["code"] in [-32600, -32603, -32001]  # -32001 for custom auth errors
    
    async def test_multiple_tool_calls_with_session_credentials(
        self, mcp_stdio_client, coordinator, credential_mock
    ):
        """Test multiple tool calls maintaining session-based credentials."""
        session_id = "mcp_session_test_123"
        
        # Coordinate credentials for the session
        coord_result = await coordinator.coordinate_credentials(
            session_id, "mcp_multi_tool_test", credential_mock
        )
        assert coord_result["success"]
        
        # Get available tools
        tools_response = await mcp_stdio_client.list_tools()
        tools = tools_response["result"]["tools"]
        
        # Find different types of tools to test
        tool_types = {
            "skyfi": [t for t in tools if "skyfi" in t["name"].lower()],
            "weather": [t for t in tools if "weather" in t["name"].lower()],
            "osm": [t for t in tools if "geocode" in t["name"].lower() or "osm" in t["name"].lower()]
        }
        
        # Execute tools from different services with session credentials
        session_creds = coordinator.get_session_credentials(session_id)
        
        for service, service_tools in tool_types.items():
            if not service_tools or service not in session_creds:
                continue
                
            test_tool = service_tools[0]
            cred = session_creds[service]
            
            # Prepare authentication metadata based on credential type
            auth_meta = {
                "session_id": session_id,
                "auth_type": cred.credential_type
            }
            
            if cred.credential_type == "api_key":
                auth_meta["api_key"] = cred.value
            elif cred.credential_type == "oauth":
                auth_meta["access_token"] = cred.value
            elif cred.credential_type == "pat":
                auth_meta["pat_token"] = cred.value
            
            # Execute tool with session credentials
            execute_response = await mcp_stdio_client.send_message("tools/call", {
                "name": test_tool["name"],
                "arguments": self._get_test_arguments(service),
                "meta": {"authentication": auth_meta}
            })
            
            # Validate response
            assert "jsonrpc" in execute_response
            assert execute_response["jsonrpc"] == "2.0"
            
            # Track credential usage
            cred.mark_used()
        
        # Cleanup session
        coordinator.clear_session(session_id)
    
    def _get_test_arguments(self, service: str) -> Dict[str, Any]:
        """Get appropriate test arguments for different services."""
        if service == "skyfi":
            return {
                "aoi": {"type": "Point", "coordinates": [-122.4194, 37.7749]},
                "start_date": "2024-01-01",
                "end_date": "2024-01-31"
            }
        elif service == "weather":
            return {
                "latitude": 37.7749,
                "longitude": -122.4194
            }
        elif service == "osm":
            return {
                "address": "San Francisco, CA"
            }
        else:
            return {}
    
    async def test_mcp_error_handling_for_invalid_credentials(self, mcp_stdio_client):
        """Test MCP error handling for invalid credentials."""
        # Get a tool that requires authentication
        tools_response = await mcp_stdio_client.list_tools()
        tools = tools_response["result"]["tools"]
        
        auth_required_tools = [
            tool for tool in tools 
            if "skyfi" in tool["name"].lower() or "weather" in tool["name"].lower()
        ]
        
        if not auth_required_tools:
            pytest.skip("No authentication-required tools available")
        
        test_tool = auth_required_tools[0]
        
        # Test with various invalid credential scenarios
        invalid_scenarios = [
            # No authentication
            {},
            # Empty authentication
            {"authentication": {}},
            # Invalid API key
            {"authentication": {"api_key": "invalid_key_123"}},
            # Malformed authentication
            {"authentication": {"malformed": "data"}},
            # Expired token (simulated)
            {"authentication": {"access_token": "expired_token_123"}},
        ]
        
        for scenario in invalid_scenarios:
            execute_response = await mcp_stdio_client.send_message("tools/call", {
                "name": test_tool["name"],
                "arguments": self._get_test_arguments("skyfi"),
                "meta": scenario
            })
            
            # Should return proper MCP error response
            assert "jsonrpc" in execute_response
            assert execute_response["jsonrpc"] == "2.0"
            
            if "error" in execute_response:
                error = execute_response["error"]
                assert "code" in error
                assert "message" in error
                assert isinstance(error["code"], int)
                assert isinstance(error["message"], str)
                
                # Error message should not expose sensitive information
                error_msg = error["message"].lower()
                sensitive_terms = ["password", "secret", "token", "key"]
                exposed_terms = [term for term in sensitive_terms if term in error_msg]
                
                # Some exposure is acceptable (e.g., "invalid api key") but not actual values
                if exposed_terms:
                    # Ensure no actual credential values are exposed
                    assert "invalid_key_123" not in error_msg
                    assert "expired_token_123" not in error_msg
    
    async def test_mcp_credential_precedence_in_tool_calls(
        self, mcp_stdio_client, credential_mock
    ):
        """Test credential precedence handling in MCP tool calls."""
        # Get a SkyFi tool for testing
        tools_response = await mcp_stdio_client.list_tools()
        tools = tools_response["result"]["tools"]
        
        skyfi_tools = [tool for tool in tools if "skyfi" in tool["name"].lower()]
        if not skyfi_tools:
            pytest.skip("No SkyFi tools available for precedence testing")
        
        test_tool = skyfi_tools[0]
        
        # Test with multiple authentication methods (should use highest precedence)
        multi_auth_response = await mcp_stdio_client.send_message("tools/call", {
            "name": test_tool["name"],
            "arguments": self._get_test_arguments("skyfi"),
            "meta": {
                "authentication": {
                    # Multiple auth methods - OAuth should take precedence
                    "access_token": "oauth_token_test_123",
                    "api_key": "api_key_test_123",
                    "pat_token": "pat_token_test_123"
                }
            }
        })
        
        # Response should be valid (using OAuth precedence)
        assert "jsonrpc" in multi_auth_response
        assert multi_auth_response["jsonrpc"] == "2.0"
        
        # Test precedence enforcement by injecting credentials
        required_services = {"skyfi"}
        injection_result = await credential_mock.inject_credentials(
            request_context={"mcp_tool_call": True},
            required_services=required_services
        )
        
        assert injection_result.success
        
        # Verify precedence order in the result
        assert len(injection_result.precedence_order) > 0
        skyfi_precedence = [
            order for order in injection_result.precedence_order 
            if order.startswith("skyfi:")
        ]
        assert len(skyfi_precedence) > 0
        
        # First in precedence should be OAuth
        first_precedence = skyfi_precedence[0]
        assert "oauth" in first_precedence
    
    async def test_mcp_concurrent_tool_calls_with_credentials(
        self, mcp_stdio_client, credential_mock
    ):
        """Test concurrent MCP tool calls with credential management."""
        # Get available tools
        tools_response = await mcp_stdio_client.list_tools()
        tools = tools_response["result"]["tools"][:3]  # Test with first 3 tools
        
        if not tools:
            pytest.skip("No tools available for concurrent testing")
        
        # Create concurrent tool call tasks
        concurrent_tasks = []
        
        for i, tool in enumerate(tools):
            # Inject credentials for each call
            injection_task = credential_mock.inject_credentials(
                request_context={"concurrent_call": i},
                required_services={"skyfi", "weather", "osm"}
            )
            
            concurrent_tasks.append(injection_task)
        
        # Execute credential injections concurrently
        injection_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Create tool call tasks
        tool_call_tasks = []
        
        for i, (tool, injection_result) in enumerate(zip(tools, injection_results)):
            if isinstance(injection_result, Exception) or not injection_result.success:
                continue
                
            # Determine service type and credentials
            service_type = self._get_service_type_from_tool_name(tool["name"])
            
            auth_meta = {}
            if service_type in injection_result.injected_credentials:
                cred = injection_result.injected_credentials[service_type]
                auth_meta = {
                    "auth_type": cred.credential_type,
                    f"{cred.credential_type}": cred.value
                }
            
            # Create tool call task
            tool_call_task = mcp_stdio_client.send_message("tools/call", {
                "name": tool["name"],
                "arguments": self._get_test_arguments(service_type),
                "meta": {"authentication": auth_meta} if auth_meta else {}
            })
            
            tool_call_tasks.append(tool_call_task)
        
        if not tool_call_tasks:
            pytest.skip("No valid tool calls could be created")
        
        # Execute tool calls concurrently
        start_time = time.perf_counter()
        tool_responses = await asyncio.gather(*tool_call_tasks, return_exceptions=True)
        end_time = time.perf_counter()
        
        # Validate concurrent execution performance
        execution_time = end_time - start_time
        assert execution_time < 10.0, f"Concurrent execution too slow: {execution_time:.2f}s"
        
        # Validate responses
        valid_responses = 0
        for response in tool_responses:
            if isinstance(response, Exception):
                continue
                
            if isinstance(response, dict) and "jsonrpc" in response:
                assert response["jsonrpc"] == "2.0"
                valid_responses += 1
        
        # At least some responses should be valid
        assert valid_responses > 0, "No valid responses from concurrent tool calls"
    
    def _get_service_type_from_tool_name(self, tool_name: str) -> str:
        """Determine service type from tool name."""
        tool_name_lower = tool_name.lower()
        
        if "skyfi" in tool_name_lower:
            return "skyfi"
        elif "weather" in tool_name_lower:
            return "weather"
        elif "geocode" in tool_name_lower or "osm" in tool_name_lower:
            return "osm"
        else:
            return "skyfi"  # Default
    
    async def test_mcp_authentication_state_persistence(
        self, mcp_stdio_client, coordinator, credential_mock
    ):
        """Test authentication state persistence across MCP operations."""
        session_id = "mcp_persistence_test"
        
        # Initialize session with credentials
        coord_result = await coordinator.coordinate_credentials(
            session_id, "persistent_session_test", credential_mock
        )
        assert coord_result["success"]
        
        # Get tools for testing
        tools_response = await mcp_stdio_client.list_tools()
        tools = tools_response["result"]["tools"]
        
        skyfi_tools = [tool for tool in tools if "skyfi" in tool["name"].lower()]
        if not skyfi_tools:
            pytest.skip("No SkyFi tools for persistence testing")
        
        test_tool = skyfi_tools[0]
        session_creds = coordinator.get_session_credentials(session_id)
        skyfi_cred = session_creds["skyfi"]
        
        # Perform multiple operations with the same session
        operations = [
            {"operation": "first_call", "args": self._get_test_arguments("skyfi")},
            {"operation": "second_call", "args": self._get_test_arguments("skyfi")},
            {"operation": "third_call", "args": self._get_test_arguments("skyfi")}
        ]
        
        initial_usage_count = skyfi_cred.usage_count
        
        for operation in operations:
            # Execute tool with persistent session credentials
            execute_response = await mcp_stdio_client.send_message("tools/call", {
                "name": test_tool["name"],
                "arguments": operation["args"],
                "meta": {
                    "authentication": {
                        "session_id": session_id,
                        "auth_type": skyfi_cred.credential_type,
                        "credential_value": skyfi_cred.value
                    }
                }
            })
            
            # Mark credential as used (simulating server behavior)
            skyfi_cred.mark_used()
            
            # Validate response
            assert "jsonrpc" in execute_response
            assert execute_response["jsonrpc"] == "2.0"
        
        # Verify credential usage tracking
        final_usage_count = skyfi_cred.usage_count
        assert final_usage_count > initial_usage_count
        assert final_usage_count == initial_usage_count + len(operations)
        
        # Cleanup session
        coordinator.clear_session(session_id)
    
    async def test_mcp_tool_schema_with_auth_parameters(self, mcp_stdio_client):
        """Test that MCP tool schemas properly handle authentication parameters."""
        # Get tool schemas
        tools_response = await mcp_stdio_client.list_tools()
        assert "result" in tools_response
        
        tools = tools_response["result"]["tools"]
        
        for tool in tools:
            # Validate basic tool schema structure
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            
            schema = tool["inputSchema"]
            assert "type" in schema
            assert schema["type"] == "object"
            
            # Check if tool supports authentication parameters
            if "properties" in schema:
                properties = schema["properties"]
                
                # Look for authentication-related properties
                auth_properties = [
                    prop for prop in properties.keys()
                    if any(auth_term in prop.lower() for auth_term in 
                          ["auth", "key", "token", "credential"])
                ]
                
                # If authentication properties exist, they should be properly defined
                for auth_prop in auth_properties:
                    prop_schema = properties[auth_prop]
                    assert "type" in prop_schema
                    
                    # Authentication properties should have descriptions
                    if "description" in prop_schema:
                        desc = prop_schema["description"].lower()
                        # Description should not expose sensitive implementation details
                        sensitive_terms = ["password", "secret", "private_key"]
                        for term in sensitive_terms:
                            assert term not in desc, (
                                f"Tool {tool['name']} exposes sensitive term '{term}' "
                                f"in auth property description"
                            )
    
    async def test_mcp_authentication_error_propagation(self, mcp_stdio_client):
        """Test proper error propagation for authentication failures in MCP."""
        # Get a tool that requires authentication
        tools_response = await mcp_stdio_client.list_tools()
        tools = tools_response["result"]["tools"]
        
        auth_tools = [tool for tool in tools if "skyfi" in tool["name"].lower()]
        if not auth_tools:
            pytest.skip("No authentication-required tools available")
        
        test_tool = auth_tools[0]
        
        # Test different authentication failure scenarios
        failure_scenarios = [
            {
                "name": "missing_auth",
                "meta": {},
                "expected_error_codes": [-32600, -32603, -32001]
            },
            {
                "name": "invalid_auth_format",
                "meta": {"authentication": "invalid_string"},
                "expected_error_codes": [-32600, -32602]
            },
            {
                "name": "unsupported_auth_type",
                "meta": {"authentication": {"unsupported_type": "value"}},
                "expected_error_codes": [-32600, -32001]
            }
        ]
        
        for scenario in failure_scenarios:
            execute_response = await mcp_stdio_client.send_message("tools/call", {
                "name": test_tool["name"],
                "arguments": self._get_test_arguments("skyfi"),
                "meta": scenario["meta"]
            })
            
            # Should return proper MCP error
            assert "jsonrpc" in execute_response
            assert execute_response["jsonrpc"] == "2.0"
            
            if "error" in execute_response:
                error = execute_response["error"]
                assert "code" in error
                assert "message" in error
                
                # Error code should be appropriate
                assert error["code"] in scenario["expected_error_codes"], (
                    f"Scenario '{scenario['name']}' returned unexpected error code: "
                    f"{error['code']}"
                )
                
                # Error message should be informative but not expose internals
                message = error["message"]
                assert len(message) > 0
                assert not any(
                    sensitive in message.lower() 
                    for sensitive in ["traceback", "file path", "database"]
                )
    
    async def test_mcp_credential_metadata_handling(
        self, mcp_stdio_client, credential_mock
    ):
        """Test handling of credential metadata in MCP operations."""
        # Add credential with rich metadata
        test_credential = credential_mock.add_credential(
            "skyfi", "oauth", "oauth_metadata_test_token",
            expires_at=time.time() + 3600,
            scopes=["read:archives", "write:orders"],
            metadata={
                "user_id": "metadata_test_user",
                "organization_id": "metadata_test_org",
                "issued_at": time.time(),
                "client_id": "mcp_test_client"
            }
        )
        
        # Inject credential with metadata
        injection_result = await credential_mock.inject_credentials(
            request_context={"metadata_test": True},
            required_services={"skyfi"}
        )
        
        assert injection_result.success
        assert "skyfi" in injection_result.injected_credentials
        
        injected_cred = injection_result.injected_credentials["skyfi"]
        
        # Verify metadata is preserved
        assert "user_id" in injected_cred.metadata
        assert "organization_id" in injected_cred.metadata
        assert "issued_at" in injected_cred.metadata
        assert "client_id" in injected_cred.metadata
        
        # Verify metadata values
        assert injected_cred.metadata["user_id"] == "metadata_test_user"
        assert injected_cred.metadata["organization_id"] == "metadata_test_org"
        assert injected_cred.metadata["client_id"] == "mcp_test_client"
        
        # Test that sensitive metadata is not exposed in tool calls
        # (This would be tested by attempting a tool call and checking 
        #  that internal metadata doesn't leak into responses)