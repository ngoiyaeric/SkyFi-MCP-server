"""
Multi-Method Authentication Integration Tests

These tests validate the comprehensive authentication system of the SkyFi MCP server,
including all supported authentication methods and their precedence rules.
"""

from __future__ import annotations

import asyncio
import pytest
import time
from typing import Dict, Any

from tests.fixtures.auth_mock import AuthenticationMockSuite, AuthResult


@pytest.mark.integration
@pytest.mark.auth
class TestMultiMethodAuthentication:
    """Comprehensive authentication method testing with precedence validation."""
    
    @pytest.fixture
    async def auth_suite(self):
        """Provide authentication mock suite."""
        suite = AuthenticationMockSuite()
        await suite.setup()
        yield suite
        await suite.teardown()
        
    async def test_oauth_precedence_over_all_methods(self, auth_suite):
        """Test OAuth 2.0 takes precedence over all other authentication methods."""
        request_headers = {
            "Authorization": "Bearer test_oauth_token_valid",
            "X-Skyfi-Api-Key": "test_skyfi_key_valid_123",
            "X-PAT-Token": "skyfi_pat_test_token_valid",
            "X-Session-Token": "test_jwt_token_valid",
            "X-Service-Account-Key": "skyfi_sa_test_key_valid"
        }
        
        auth_result = await auth_suite.authenticate(request_headers)
        
        assert auth_result.valid
        assert auth_result.method == "oauth"
        assert auth_result.user_id == "oauth-user-123"
        assert auth_result.organization_id == "oauth-org-456"
        assert "read:archives" in auth_result.scopes
        assert "write:orders" in auth_result.scopes
        
    async def test_pat_precedence_over_lower_methods(self, auth_suite):
        """Test PAT authentication takes precedence when OAuth fails."""
        request_headers = {
            "Authorization": "Bearer invalid_oauth_token",
            "X-PAT-Token": "skyfi_pat_test_token_valid",
            "X-Skyfi-Api-Key": "test_skyfi_key_valid_123",
            "X-Session-Token": "test_jwt_token_valid"
        }
        
        auth_result = await auth_suite.authenticate(request_headers)
        
        assert auth_result.valid
        assert auth_result.method == "pat"
        assert auth_result.user_id == "pat-user-789"
        assert auth_result.organization_id == "pat-org-012"
        assert "read:archives" in auth_result.scopes
        assert "write:orders" in auth_result.scopes
        
    async def test_api_key_fallback_authentication(self, auth_suite):
        """Test API key authentication when higher precedence methods fail."""
        request_headers = {
            "Authorization": "Bearer invalid_oauth_token",
            "X-PAT-Token": "invalid_pat_token",
            "X-Skyfi-Api-Key": "test_skyfi_key_valid_123"
        }
        
        auth_result = await auth_suite.authenticate(request_headers)
        
        assert auth_result.valid
        assert auth_result.method == "api_key"
        assert auth_result.user_id == "api-user-def"
        assert auth_result.organization_id == "api-org-ghi"
        assert "read:archives" in auth_result.scopes
        
    async def test_jwt_session_authentication(self, auth_suite):
        """Test JWT session token authentication."""
        request_headers = {
            "X-Session-Token": "test_jwt_token_valid"
        }
        
        auth_result = await auth_suite.authenticate(request_headers)
        
        assert auth_result.valid
        assert auth_result.method == "jwt"
        assert auth_result.user_id == "jwt-user-123"
        assert auth_result.organization_id == "jwt-org-456"
        
    async def test_service_account_lowest_precedence(self, auth_suite):
        """Test service account key authentication (lowest precedence)."""
        request_headers = {
            "X-Service-Account-Key": "skyfi_sa_test_key_valid"
        }
        
        auth_result = await auth_suite.authenticate(request_headers)
        
        assert auth_result.valid
        assert auth_result.method == "service_account"
        assert auth_result.user_id == "service-test-service"
        assert auth_result.organization_id is None  # Service accounts don't have orgs
        assert "read:archives" in auth_result.scopes
        assert "system:monitoring" in auth_result.scopes
        
    @pytest.mark.parametrize("invalid_headers", [
        # No authentication
        {},
        # Invalid OAuth
        {"Authorization": "Bearer invalid_token"},
        # Invalid PAT
        {"X-PAT-Token": "invalid_pat_token"},
        # Invalid API key
        {"X-Skyfi-Api-Key": "invalid_api_key"},
        # Invalid JWT
        {"X-Session-Token": "invalid_jwt_token"},
        # Invalid service account
        {"X-Service-Account-Key": "invalid_service_key"},
        # Malformed headers
        {"Authorization": "Bearer "},
        {"X-PAT-Token": ""},
        {"X-Skyfi-Api-Key": ""},
        # All methods invalid
        {
            "Authorization": "Bearer invalid_oauth",
            "X-PAT-Token": "invalid_pat",
            "X-Skyfi-Api-Key": "invalid_key",
            "X-Session-Token": "invalid_jwt",
            "X-Service-Account-Key": "invalid_service"
        }
    ])
    async def test_authentication_failures(self, auth_suite, invalid_headers):
        """Test various authentication failure scenarios."""
        auth_result = await auth_suite.authenticate(invalid_headers)
        
        assert not auth_result.valid
        assert auth_result.error_message is not None
        
    async def test_expired_token_handling(self, auth_suite):
        """Test handling of expired tokens across all methods."""
        expired_scenarios = [
            {"Authorization": "Bearer test_oauth_token_expired"},
            {"X-PAT-Token": "skyfi_pat_test_token_expired"},
            {"X-Skyfi-Api-Key": "test_skyfi_key_expired"},
            {"X-Session-Token": "test_jwt_token_expired"}
        ]
        
        for headers in expired_scenarios:
            auth_result = await auth_suite.authenticate(headers)
            assert not auth_result.valid
            assert "expired" in auth_result.error_message.lower()
            
    async def test_case_insensitive_headers(self, auth_suite):
        """Test case insensitive header handling."""
        case_variants = [
            {"authorization": "Bearer test_oauth_token_valid"},
            {"x-skyfi-api-key": "test_skyfi_key_valid_123"},
            {"X-PAT-TOKEN": "skyfi_pat_test_token_valid"},
            {"x-session-token": "test_jwt_token_valid"}
        ]
        
        for headers in case_variants:
            auth_result = await auth_suite.authenticate(headers)
            assert auth_result.valid, f"Case insensitive auth failed for headers: {headers}"
            
    async def test_scope_validation(self, auth_suite):
        """Test scope extraction and validation for different auth methods."""
        auth_scenarios = [
            {
                "headers": {"Authorization": "Bearer test_oauth_token_valid"},
                "expected_scopes": ["read:archives", "write:orders", "read:account"]
            },
            {
                "headers": {"X-PAT-Token": "skyfi_pat_test_token_valid"},
                "expected_scopes": ["read:archives", "write:orders"]
            },
            {
                "headers": {"X-Skyfi-Api-Key": "test_skyfi_key_valid_123"},
                "expected_scopes": ["read:archives", "write:orders"]
            },
            {
                "headers": {"X-Service-Account-Key": "skyfi_sa_test_key_valid"},
                "expected_scopes": ["read:archives", "system:monitoring"]
            }
        ]
        
        for scenario in auth_scenarios:
            auth_result = await auth_suite.authenticate(scenario["headers"])
            assert auth_result.valid
            
            for expected_scope in scenario["expected_scopes"]:
                assert expected_scope in auth_result.scopes, (
                    f"Missing scope '{expected_scope}' for method {auth_result.method}. "
                    f"Got scopes: {auth_result.scopes}"
                )
                
    async def test_authentication_performance(self, auth_suite):
        """Test authentication performance under load."""
        auth_headers = {"X-Skyfi-Api-Key": "test_skyfi_key_valid_123"}
        
        # Measure authentication time
        iterations = 1000
        start_time = time.perf_counter()
        
        for _ in range(iterations):
            auth_result = await auth_suite.authenticate(auth_headers)
            assert auth_result.valid
            
        end_time = time.perf_counter()
        avg_time = (end_time - start_time) / iterations
        
        # Authentication should be fast (< 1ms per operation)
        assert avg_time < 0.001, f"Authentication too slow: {avg_time:.4f}s per operation"
        
    async def test_concurrent_authentication_requests(self, auth_suite):
        """Test concurrent authentication requests."""
        async def auth_request(headers):
            return await auth_suite.authenticate(headers)
            
        # Create various auth scenarios
        auth_scenarios = [
            {"Authorization": "Bearer test_oauth_token_valid"},
            {"X-PAT-Token": "skyfi_pat_test_token_valid"},
            {"X-Skyfi-Api-Key": "test_skyfi_key_valid_123"},
            {"X-Session-Token": "test_jwt_token_valid"},
            {"X-Service-Account-Key": "skyfi_sa_test_key_valid"}
        ]
        
        # Run concurrent authentications
        concurrent_requests = []
        for i in range(50):  # 50 concurrent requests
            headers = auth_scenarios[i % len(auth_scenarios)]
            concurrent_requests.append(auth_request(headers))
            
        results = await asyncio.gather(*concurrent_requests)
        
        # All should succeed
        for i, result in enumerate(results):
            assert result.valid, f"Concurrent auth request {i} failed: {result.error_message}"
            
    async def test_authentication_precedence_edge_cases(self, auth_suite):
        """Test authentication precedence with edge cases."""
        # Valid OAuth should win even with valid lower precedence methods
        headers = {
            "Authorization": "Bearer test_oauth_token_valid",
            "X-PAT-Token": "skyfi_pat_test_token_valid",
            "X-Skyfi-Api-Key": "test_skyfi_key_valid_123"
        }
        
        auth_result = await auth_suite.authenticate(headers)
        assert auth_result.method == "oauth"
        
        # With invalid OAuth, should fall back to valid PAT
        headers["Authorization"] = "Bearer invalid_oauth_token"
        auth_result = await auth_suite.authenticate(headers)
        assert auth_result.method == "pat"
        
        # With invalid OAuth and PAT, should fall back to API key
        headers["X-PAT-Token"] = "invalid_pat_token"
        auth_result = await auth_suite.authenticate(headers)
        assert auth_result.method == "api_key"
        
    async def test_user_context_extraction(self, auth_suite):
        """Test user context extraction from different auth methods."""
        test_scenarios = [
            {
                "headers": {"Authorization": "Bearer test_oauth_token_valid"},
                "expected_user": "oauth-user-123",
                "expected_org": "oauth-org-456"
            },
            {
                "headers": {"X-PAT-Token": "skyfi_pat_test_token_valid"},
                "expected_user": "pat-user-789", 
                "expected_org": "pat-org-012"
            },
            {
                "headers": {"X-Skyfi-Api-Key": "test_skyfi_key_valid_123"},
                "expected_user": "api-user-def",
                "expected_org": "api-org-ghi"
            }
        ]
        
        for scenario in test_scenarios:
            auth_result = await auth_suite.authenticate(scenario["headers"])
            assert auth_result.valid
            assert auth_result.user_id == scenario["expected_user"]
            assert auth_result.organization_id == scenario["expected_org"]
            
    async def test_authentication_with_malformed_data(self, auth_suite):
        """Test authentication handling with malformed data."""
        malformed_scenarios = [
            # Malformed Bearer token
            {"Authorization": "Bearer"},
            {"Authorization": "Bearer   "},
            {"Authorization": "Bearertoken"},
            
            # Malformed API keys
            {"X-Skyfi-Api-Key": " "},
            {"X-Skyfi-Api-Key": "\t\n"},
            
            # Malformed PAT tokens
            {"X-PAT-Token": "not_a_pat_token"},
            {"X-PAT-Token": "skyfi_pat_"},
            
            # Multiple authorization methods with malformed data
            {
                "Authorization": "Bearer   ",
                "X-Skyfi-Api-Key": "",
                "X-PAT-Token": "malformed"
            }
        ]
        
        for headers in malformed_scenarios:
            auth_result = await auth_suite.authenticate(headers)
            assert not auth_result.valid
            assert auth_result.error_message is not None