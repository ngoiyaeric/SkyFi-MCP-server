"""
Security Vulnerability Tests

This module provides comprehensive security testing for the SkyFi MCP server,
including penetration testing, input validation, and protection against
common web application vulnerabilities.
"""

from __future__ import annotations

import asyncio
import pytest
import time
from typing import List, Dict, Any


@pytest.mark.security
@pytest.mark.integration
class TestSecurityVulnerabilities:
    """Comprehensive security vulnerability testing suite."""
    
    async def test_sql_injection_prevention(self, test_client, security_test_payloads):
        """Test SQL injection attack prevention across all endpoints."""
        sql_payloads = security_test_payloads["sql_injection"]
        
        # Test endpoints that might be vulnerable to SQL injection
        vulnerable_endpoints = [
            ("/skyfi/search-archives", "POST"),
            ("/skyfi/create-order", "POST"),
            ("/osm/geocode-address", "GET"),
            ("/weather/current", "GET")
        ]
        
        for endpoint, method in vulnerable_endpoints:
            for payload in sql_payloads:
                if method == "GET":
                    # Test query parameters
                    response = await test_client.get(
                        f"{endpoint}?query={payload}",
                        headers={"X-Skyfi-Api-Key": "test_security_key"}
                    )
                else:
                    # Test JSON body
                    response = await test_client.post(
                        endpoint,
                        json={"query": payload, "description": payload},
                        headers={"X-Skyfi-Api-Key": "test_security_key"}
                    )
                
                # Should not return SQL errors or unauthorized data
                assert response.status_code != 500, f"SQL injection caused server error: {payload}"
                
                response_text = response.text.lower()
                sql_error_indicators = [
                    "sql", "mysql", "postgresql", "sqlite", "syntax error",
                    "table", "column", "database", "constraint", "foreign key"
                ]
                
                for indicator in sql_error_indicators:
                    assert indicator not in response_text, (
                        f"SQL injection payload '{payload}' revealed database information"
                    )
                    
    async def test_xss_prevention(self, test_client, security_test_payloads):
        """Test Cross-Site Scripting (XSS) attack prevention."""
        xss_payloads = security_test_payloads["xss_payloads"]
        
        # Test endpoints that return user-supplied data
        test_endpoints = [
            "/skyfi/search-archives",
            "/skyfi/create-order",
            "/osm/geocode-address"
        ]
        
        for endpoint in test_endpoints:
            for payload in xss_payloads:
                # Test XSS in different data fields
                test_data = {
                    "description": payload,
                    "name": payload,
                    "query": payload,
                    "address": payload
                }
                
                response = await test_client.post(
                    endpoint,
                    json=test_data,
                    headers={"X-Skyfi-Api-Key": "test_security_key"}
                )
                
                # Response should not contain unescaped payload
                response_text = response.text
                
                # Check for unescaped script tags and event handlers
                dangerous_patterns = [
                    "<script", "</script>", "javascript:", "onerror=", 
                    "onload=", "onclick=", "onmouseover=", "alert(", "eval("
                ]
                
                for pattern in dangerous_patterns:
                    assert pattern.lower() not in response_text.lower(), (
                        f"XSS payload '{payload}' not properly escaped in response"
                    )
                    
    async def test_command_injection_prevention(self, test_client, security_test_payloads):
        """Test command injection attack prevention."""
        command_payloads = security_test_payloads["command_injection"]
        
        # Test endpoints that might execute system commands
        test_endpoints = [
            "/skyfi/search-archives",
            "/osm/geocode-address",
            "/weather/current"
        ]
        
        for endpoint in test_endpoints:
            for payload in command_payloads:
                # Test in various parameters
                test_params = {"query": payload, "address": payload, "location": payload}
                
                response = await test_client.get(
                    endpoint,
                    params=test_params,
                    headers={"X-Skyfi-Api-Key": "test_security_key"}
                )
                
                # Should not execute commands or reveal system information
                response_text = response.text.lower()
                
                # Check for command execution indicators
                command_indicators = [
                    "/etc/passwd", "/etc/hosts", "root:", "bin/sh", 
                    "uid=", "gid=", "groups=", "whoami", "ls -la"
                ]
                
                for indicator in command_indicators:
                    assert indicator not in response_text, (
                        f"Command injection payload '{payload}' may have executed"
                    )
                    
    async def test_path_traversal_prevention(self, test_client, security_test_payloads):
        """Test path traversal attack prevention."""
        path_payloads = security_test_payloads["path_traversal"]
        
        # Test endpoints that might access files
        test_scenarios = [
            {"endpoint": "/skyfi/archives/{archive_id}", "method": "GET"},
            {"endpoint": "/skyfi/orders/{order_id}", "method": "GET"},
        ]
        
        for scenario in test_scenarios:
            for payload in path_payloads:
                # Replace path parameter with payload
                endpoint = scenario["endpoint"].replace("{archive_id}", payload).replace("{order_id}", payload)
                
                response = await test_client.get(
                    endpoint,
                    headers={"X-Skyfi-Api-Key": "test_security_key"}
                )
                
                # Should not access unauthorized files
                response_text = response.text.lower()
                
                # Check for file content indicators
                file_indicators = [
                    "root:x:0:0", "daemon:x:1:1", "[boot loader]",
                    "# /etc/passwd", "# /etc/shadow", "windows registry"
                ]
                
                for indicator in file_indicators:
                    assert indicator not in response_text, (
                        f"Path traversal payload '{payload}' accessed unauthorized file"
                    )
                    
    async def test_authentication_bypass_attempts(self, test_client):
        """Test authentication bypass prevention."""
        bypass_attempts = [
            # Missing authentication
            {},
            # Malformed headers
            {"Authorization": "Bearer "},
            {"X-Skyfi-Api-Key": ""},
            # Header injection attempts
            {"X-Skyfi-Api-Key": "valid_key\nX-Admin: true"},
            {"Authorization": "Bearer token\nX-Admin: true"},
            # Case sensitivity bypass attempts
            {"x-skyfi-api-key": "admin"},
            {"AUTHORIZATION": "Bearer admin"},
            # Unicode bypass attempts
            {"X-Skyfi-Api-Key": "admin\u0000"},
            # Length bypass attempts
            {"X-Skyfi-Api-Key": "a" * 10000},
            # Special character bypass
            {"X-Skyfi-Api-Key": "'; DROP TABLE users; --"},
            {"Authorization": "Bearer ../../../admin"},
        ]
        
        # Test protected endpoints
        protected_endpoints = [
            "/skyfi/search-archives",
            "/skyfi/create-order",
            "/skyfi/orders/12345"
        ]
        
        for endpoint in protected_endpoints:
            for headers in bypass_attempts:
                response = await test_client.get(endpoint, headers=headers)
                
                # Should return 401 Unauthorized
                assert response.status_code == 401, (
                    f"Auth bypass succeeded for endpoint {endpoint} with headers: {headers}"
                )
                
                # Should not reveal sensitive information
                response_text = response.text.lower()
                sensitive_info = ["admin", "root", "password", "secret", "token"]
                
                for info in sensitive_info:
                    assert info not in response_text or "authentication" in response_text, (
                        f"Authentication bypass revealed sensitive info: {info}"
                    )
                    
    async def test_rate_limiting_bypass_prevention(self, test_client):
        """Test rate limiting bypass prevention."""
        api_key = "test_rate_limit_bypass_key"
        
        # First, exhaust the rate limit
        for i in range(100):  # Assuming 100 req/min limit
            response = await test_client.get(
                "/skyfi/search-archives",
                headers={"X-Skyfi-Api-Key": api_key}
            )
            if response.status_code == 429:
                break
                
        # Now test various bypass techniques
        bypass_techniques = [
            # IP header manipulation
            {"X-Skyfi-Api-Key": api_key, "X-Forwarded-For": "1.2.3.4"},
            {"X-Skyfi-Api-Key": api_key, "X-Real-IP": "5.6.7.8"},
            {"X-Skyfi-Api-Key": api_key, "X-Client-IP": "9.10.11.12"},
            
            # User agent variation
            {"X-Skyfi-Api-Key": api_key, "User-Agent": "BypassBot/1.0"},
            
            # Case variation
            {"X-SKYFI-API-KEY": api_key},
            {"x-skyfi-api-key": api_key},
            
            # Multiple API key headers
            {"X-Skyfi-Api-Key": api_key, "X-API-Key": api_key},
            
            # Session manipulation
            {"X-Skyfi-Api-Key": api_key, "Cookie": "session=new_session"},
        ]
        
        for headers in bypass_techniques:
            response = await test_client.get("/skyfi/search-archives", headers=headers)
            
            # Should still be rate limited
            assert response.status_code == 429, (
                f"Rate limit bypass succeeded with headers: {headers}"
            )
            
            # Should include rate limit headers
            assert "X-RateLimit-Limit" in response.headers or "Retry-After" in response.headers
            
    async def test_dos_protection(self, test_client):
        """Test Denial of Service (DoS) attack protection."""
        # Test large payload DoS
        large_payload = {"data": "x" * (10 * 1024 * 1024)}  # 10MB payload
        
        response = await test_client.post(
            "/skyfi/search-archives",
            json=large_payload,
            headers={"X-Skyfi-Api-Key": "test_security_key"}
        )
        
        # Should reject large payloads
        assert response.status_code in [413, 400, 422], "Large payload not rejected"
        
        # Test concurrent connection DoS
        async def make_request():
            return await test_client.get(
                "/skyfi/search-archives",
                headers={"X-Skyfi-Api-Key": "test_security_key"}
            )
            
        # Create many concurrent requests
        concurrent_requests = [make_request() for _ in range(100)]
        
        start_time = time.perf_counter()
        responses = await asyncio.gather(*concurrent_requests, return_exceptions=True)
        end_time = time.perf_counter()
        
        # Server should handle concurrent requests without crashing
        successful_responses = [r for r in responses if not isinstance(r, Exception)]
        assert len(successful_responses) > 0, "Server crashed under concurrent load"
        
        # Response time should be reasonable even under load
        avg_response_time = (end_time - start_time) / len(responses)
        assert avg_response_time < 10.0, f"Server too slow under load: {avg_response_time:.2f}s"
        
    async def test_information_disclosure_prevention(self, test_client):
        """Test information disclosure prevention."""
        # Test error message information disclosure
        error_inducing_requests = [
            # Invalid JSON
            {"invalid": "json}"},
            # Missing required fields
            {},
            # Invalid data types
            {"aoi": "invalid_geometry", "start_date": 12345},
        ]
        
        for bad_request in error_inducing_requests:
            response = await test_client.post(
                "/skyfi/search-archives",
                json=bad_request,
                headers={"X-Skyfi-Api-Key": "test_security_key"}
            )
            
            # Error responses should not reveal internal details
            response_text = response.text.lower()
            
            sensitive_patterns = [
                "/home/", "/usr/", "/var/", "c:\\", "traceback",
                "file \"", "line ", "function ", "module ",
                "database", "connection", "password", "secret"
            ]
            
            for pattern in sensitive_patterns:
                assert pattern not in response_text, (
                    f"Error response disclosed sensitive information: {pattern}"
                )
                
        # Test debug mode information disclosure
        response = await test_client.get(
            "/debug",
            headers={"X-Skyfi-Api-Key": "test_security_key"}
        )
        
        # Debug endpoint should not exist in production
        assert response.status_code == 404, "Debug endpoint accessible in production"
        
    async def test_session_management_security(self, test_client):
        """Test session management security."""
        # Test session fixation
        session_headers = {"Cookie": "session=fixed_session_id"}
        
        response = await test_client.post(
            "/auth/login", 
            json={"username": "test", "password": "test"},
            headers=session_headers
        )
        
        # Should create new session, not use fixed one
        if "Set-Cookie" in response.headers:
            set_cookie = response.headers["Set-Cookie"]
            assert "fixed_session_id" not in set_cookie, "Session fixation vulnerability"
            
        # Test session hijacking protection
        # (This would typically involve testing secure flags, httpOnly, etc.)
        
    async def test_crypto_implementation_security(self, test_client):
        """Test cryptographic implementation security."""
        # Test weak encryption detection
        # Note: This would typically involve testing actual crypto operations
        
        # Test for weak random number generation
        # Generate multiple "random" tokens and check for patterns
        random_responses = []
        
        for _ in range(10):
            response = await test_client.post(
                "/auth/request-token",
                headers={"X-Skyfi-Api-Key": "test_security_key"}
            )
            
            if response.status_code == 200:
                random_responses.append(response.json())
                
        # Check that generated values are sufficiently random
        if len(random_responses) > 1:
            # Tokens should not be predictable
            tokens = [r.get("token", "") for r in random_responses]
            unique_tokens = set(tokens)
            assert len(unique_tokens) == len(tokens), "Generated tokens are not unique"
            
    async def test_input_validation_edge_cases(self, test_client):
        """Test input validation with edge cases."""
        edge_case_inputs = [
            # Null bytes
            {"query": "test\x00malicious"},
            
            # Unicode edge cases
            {"query": "\ufeff\u200b\u200c\u200d"},
            
            # Large numbers
            {"limit": 2**63, "offset": 2**63},
            
            # Negative numbers where positive expected
            {"limit": -1, "page_size": -100},
            
            # Empty strings vs None
            {"query": "", "filter": None},
            
            # Deeply nested structures
            {"nested": {"level1": {"level2": {"level3": {"level4": {"data": "deep"}}}}}},
            
            # Array edge cases  
            {"array": [], "items": [""] * 10000},
            
            # Boolean confusion
            {"enabled": "true", "active": 1, "valid": "yes"},
        ]
        
        for edge_input in edge_case_inputs:
            response = await test_client.post(
                "/skyfi/search-archives",
                json=edge_input,
                headers={"X-Skyfi-Api-Key": "test_security_key"}
            )
            
            # Should handle edge cases gracefully
            assert response.status_code != 500, f"Edge case caused server error: {edge_input}"
            
            # Should not reveal internal errors
            if response.status_code >= 400:
                error_text = response.text.lower()
                assert "traceback" not in error_text, "Internal error details exposed"