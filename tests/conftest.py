"""
Global pytest configuration and fixtures for SkyFi MCP testing.

This module provides shared fixtures, test configuration, and common utilities
for the entire test suite, supporting unit, integration, and end-to-end testing.
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import httpx
from fastapi.testclient import TestClient

from src.mcp_skyfi.servers.main import main_mcp
from tests.fixtures.external_mocks import ExternalServiceMockSuite
from tests.fixtures.auth_mock import AuthenticationMockSuite


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def test_config():
    """Provide test configuration with safe defaults."""
    return {
        "SKYFI_API_URL": "http://mock-skyfi-api.test",
        "OPENWEATHER_API_URL": "http://mock-weather-api.test", 
        "NOMINATIM_API_URL": "http://mock-osm-api.test",
        "READ_ONLY_MODE": "false",
        "LOG_LEVEL": "DEBUG",
        "ENABLED_TOOLS": "",
        "MCP_HOST": "localhost",
        "MCP_PORT": "8001"
    }


@pytest.fixture
async def test_client(test_config):
    """Create a test client for the SkyFi MCP server."""
    # Set test environment variables
    for key, value in test_config.items():
        os.environ[key] = value
    
    try:
        # Create FastAPI test client
        with TestClient(main_mcp.http_app()) as client:
            yield client
    finally:
        # Cleanup environment variables
        for key in test_config.keys():
            os.environ.pop(key, None)


@pytest.fixture
async def mcp_stdio_client():
    """Create a test client for MCP STDIO transport."""
    import subprocess
    import json
    
    # Start MCP server in STDIO mode
    process = await asyncio.create_subprocess_exec(
        "python", "-m", "mcp_skyfi", "--transport", "stdio",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    class MCPSTDIOClient:
        def __init__(self, process):
            self.process = process
            self.message_id = 0
            
        async def send_message(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
            """Send an MCP message and wait for response."""
            self.message_id += 1
            message = {
                "jsonrpc": "2.0",
                "id": self.message_id,
                "method": method,
                "params": params or {}
            }
            
            # Send message
            message_bytes = json.dumps(message).encode() + b'\n'
            self.process.stdin.write(message_bytes)
            await self.process.stdin.drain()
            
            # Read response
            response_line = await self.process.stdout.readline()
            return json.loads(response_line.decode())
            
        async def initialize(self):
            """Initialize MCP connection."""
            return await self.send_message("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {"listChanged": True},
                    "sampling": {}
                },
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            })
            
        async def list_tools(self):
            """List available MCP tools."""
            return await self.send_message("tools/list")
            
        async def call_tool(self, name: str, arguments: Dict[str, Any]):
            """Call an MCP tool."""
            return await self.send_message("tools/call", {
                "name": name,
                "arguments": arguments
            })
            
        async def close(self):
            """Close the MCP connection."""
            if self.process:
                self.process.terminate()
                await self.process.wait()
    
    client = MCPSTDIOClient(process)
    try:
        # Initialize the connection
        init_response = await client.initialize()
        assert "result" in init_response
        
        yield client
    finally:
        await client.close()


@pytest.fixture
def auth_headers():
    """Provide various authentication header combinations for testing."""
    return {
        "valid_api_key": {"X-Skyfi-Api-Key": "test_skyfi_key_valid_123"},
        "invalid_api_key": {"X-Skyfi-Api-Key": "test_skyfi_key_invalid"},
        "expired_api_key": {"X-Skyfi-Api-Key": "test_skyfi_key_expired"},
        "valid_oauth": {"Authorization": "Bearer test_oauth_token_valid"},
        "invalid_oauth": {"Authorization": "Bearer test_oauth_token_invalid"},
        "expired_oauth": {"Authorization": "Bearer test_oauth_token_expired"},
        "valid_pat": {"X-PAT-Token": "skyfi_pat_test_token_valid"},
        "invalid_pat": {"X-PAT-Token": "skyfi_pat_test_token_invalid"},
        "expired_pat": {"X-PAT-Token": "skyfi_pat_test_token_expired"},
        "valid_jwt": {"X-Session-Token": "test_jwt_token_valid"},
        "invalid_jwt": {"X-Session-Token": "test_jwt_token_invalid"},
        "service_account": {"X-Service-Account-Key": "skyfi_sa_test_key_valid"},
        "no_auth": {},
        "malformed_bearer": {"Authorization": "Bearer "},
        "malformed_api_key": {"X-Skyfi-Api-Key": ""},
        "case_insensitive": {"x-skyfi-api-key": "test_skyfi_key_valid_123"}
    }


@pytest.fixture
def test_geometries():
    """Provide test geometries for spatial operations."""
    return {
        "san_francisco_bbox": {
            "type": "Polygon",
            "coordinates": [[
                [-122.5, 37.7], [-122.4, 37.7],
                [-122.4, 37.8], [-122.5, 37.8],
                [-122.5, 37.7]
            ]]
        },
        "point_downtown_sf": {
            "type": "Point", 
            "coordinates": [-122.4194, 37.7749]
        },
        "multi_polygon": {
            "type": "MultiPolygon",
            "coordinates": [
                [[[-122.5, 37.7], [-122.4, 37.7], [-122.4, 37.8], [-122.5, 37.8], [-122.5, 37.7]]],
                [[[-122.3, 37.6], [-122.2, 37.6], [-122.2, 37.7], [-122.3, 37.7], [-122.3, 37.6]]]
            ]
        },
        "invalid_geometry": {
            "type": "Polygon", 
            "coordinates": [[-122.5, 37.7]]  # Invalid: not enough points
        },
        "large_geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-180, -90], [180, -90], [180, 90], [-180, 90], [-180, -90]
            ]]  # Covers entire world
        }
    }


@pytest.fixture
def test_date_ranges():
    """Provide test date ranges for temporal queries."""
    return {
        "recent": {"start_date": "2024-01-01", "end_date": "2024-01-31"},
        "historical": {"start_date": "2020-01-01", "end_date": "2020-12-31"},
        "future": {"start_date": "2025-01-01", "end_date": "2025-12-31"},
        "invalid_order": {"start_date": "2024-12-31", "end_date": "2024-01-01"},
        "same_day": {"start_date": "2024-01-01", "end_date": "2024-01-01"},
        "very_long": {"start_date": "2000-01-01", "end_date": "2024-12-31"}
    }


@pytest.fixture
async def external_service_mocks():
    """Set up external service mocks for testing."""
    mock_suite = ExternalServiceMockSuite()
    await mock_suite.setup()
    
    try:
        yield mock_suite
    finally:
        await mock_suite.teardown()


@pytest.fixture
async def auth_mock_suite():
    """Set up authentication mocking suite."""
    auth_suite = AuthenticationMockSuite()
    await auth_suite.setup()
    
    try:
        yield auth_suite
    finally:
        await auth_suite.teardown()


@pytest.fixture
def performance_config():
    """Configuration for performance testing."""
    return {
        "max_response_time": 2.0,  # seconds
        "max_p95_response_time": 5.0,  # seconds
        "max_memory_usage_mb": 512,
        "concurrent_users": 10,
        "requests_per_user": 20,
        "rate_limit_rpm": 100,
        "rate_limit_rph": 1000
    }


@pytest.fixture
def security_test_payloads():
    """Security testing payloads for vulnerability testing."""
    return {
        "sql_injection": [
            "'; DROP TABLE users; --",
            "' OR 1=1 --",
            "' UNION SELECT * FROM api_keys --",
            "admin'--",
            "' OR 'x'='x",
            "1' AND SUBSTRING(@@version, 1, 1) = '5"
        ],
        "xss_payloads": [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "';alert('xss');//",
            "<svg onload=alert('xss')>",
            "<%73cript>alert('xss')</script>"
        ],
        "command_injection": [
            "; ls -la",
            "| whoami",
            "&& cat /etc/passwd",
            "`rm -rf /`",
            "$(whoami)",
            "${IFS}cat${IFS}/etc/passwd"
        ],
        "path_traversal": [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd"
        ]
    }


@pytest.fixture
def benchmark_data():
    """Benchmark data for performance testing."""
    return {
        "small_request": {
            "aoi": {"type": "Point", "coordinates": [-122.4194, 37.7749]},
            "start_date": "2024-01-01",
            "end_date": "2024-01-07"
        },
        "medium_request": {
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
        },
        "large_request": {
            "aoi": {
                "type": "Polygon",
                "coordinates": [[
                    [-123.0, 37.5], [-122.0, 37.5],
                    [-122.0, 38.0], [-123.0, 38.0],
                    [-123.0, 37.5]
                ]]
            },
            "start_date": "2024-01-01",
            "end_date": "2024-12-31"
        }
    }


# Performance monitoring utilities
class PerformanceMonitor:
    """Monitor performance metrics during tests."""
    
    def __init__(self):
        self.metrics = {}
        
    def start_monitoring(self, operation_name: str):
        """Start monitoring a specific operation."""
        import time
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        self.metrics[operation_name] = {
            "start_time": time.perf_counter(),
            "start_memory": process.memory_info().rss,
            "start_cpu": process.cpu_percent()
        }
        
    def stop_monitoring(self, operation_name: str):
        """Stop monitoring and return metrics."""
        import time
        import psutil
        import os
        
        if operation_name not in self.metrics:
            return None
            
        process = psutil.Process(os.getpid())
        end_time = time.perf_counter()
        end_memory = process.memory_info().rss
        
        start_data = self.metrics[operation_name]
        
        return {
            "duration": end_time - start_data["start_time"],
            "memory_delta": (end_memory - start_data["start_memory"]) / (1024 * 1024),  # MB
            "peak_memory_mb": end_memory / (1024 * 1024)
        }


@pytest.fixture
def performance_monitor():
    """Provide performance monitoring utilities."""
    return PerformanceMonitor()


# Test markers
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "security: mark test as a security test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "external: mark test as requiring external services"
    )
    config.addinivalue_line(
        "markers", "mcp_compliance: mark test as MCP protocol compliance test"
    )


# Async test utilities
def pytest_asyncio_fixture_scope():
    """Define asyncio fixture scope."""
    return "function"