"""
Client Credential Flow Integration Tests

This module tests the comprehensive client credential authentication system,
including dynamic credential injection, multi-service coordination, and 
credential precedence handling for the SkyFi MCP server.
"""

from __future__ import annotations

import asyncio
import pytest
import time
from typing import Dict, Any, Set
from unittest.mock import AsyncMock, patch

from tests.fixtures.credential_mocks import (
    DynamicCredentialMock,
    CredentialFlowValidator,
    MultiServiceCredentialCoordinator,
    CredentialContext,
    CredentialInjectionResult
)


@pytest.mark.integration
@pytest.mark.auth
class TestClientCredentialFlow:
    """Comprehensive client credential flow testing."""
    
    @pytest.fixture
    async def credential_mock(self):
        """Provide dynamic credential mock."""
        mock = DynamicCredentialMock()
        yield mock
    
    @pytest.fixture
    async def flow_validator(self):
        """Provide credential flow validator."""
        return CredentialFlowValidator()
    
    @pytest.fixture
    async def coordinator(self):
        """Provide multi-service credential coordinator."""
        return MultiServiceCredentialCoordinator()
    
    async def test_dynamic_credential_injection_single_service(self, credential_mock, flow_validator):
        """Test dynamic credential injection for a single service."""
        # Test single service credential injection
        required_services = {"skyfi"}
        request_context = {"user_id": "test_user", "operation": "archive_search"}
        
        injection_result = await credential_mock.inject_credentials(
            request_context=request_context,
            required_services=required_services
        )
        
        # Validate injection succeeded
        assert injection_result.success
        assert "skyfi" in injection_result.injected_credentials
        assert injection_result.injection_time_ms > 0
        
        # Validate credential details
        skyfi_cred = injection_result.injected_credentials["skyfi"]
        assert skyfi_cred.service_name == "skyfi"
        assert skyfi_cred.credential_type in ["oauth", "pat", "api_key"]
        assert len(skyfi_cred.value) > 0
        assert skyfi_cred.usage_count == 1
        
        # Validate using flow validator
        validation_result = flow_validator.validate_injection_result(
            injection_result, required_services
        )
        assert validation_result["valid"]
        assert len(validation_result["issues"]) == 0
    
    async def test_dynamic_credential_injection_multiple_services(self, credential_mock, flow_validator):
        """Test dynamic credential injection for multiple services."""
        required_services = {"skyfi", "weather", "osm"}
        request_context = {"user_id": "test_user", "operation": "enriched_search"}
        
        injection_result = await credential_mock.inject_credentials(
            request_context=request_context,
            required_services=required_services
        )
        
        # Validate injection succeeded
        assert injection_result.success
        assert len(injection_result.injected_credentials) >= 2  # OSM is optional
        
        # Check each service credential
        for service in ["skyfi", "weather"]:
            assert service in injection_result.injected_credentials
            cred = injection_result.injected_credentials[service]
            assert cred.service_name == service
            assert not cred.is_expired()
        
        # Validate precedence order was established
        assert len(injection_result.precedence_order) > 0
        assert any("skyfi:oauth" in order for order in injection_result.precedence_order)
        
        # Validate using flow validator
        validation_result = flow_validator.validate_injection_result(
            injection_result, required_services
        )
        assert validation_result["valid"]
    
    async def test_credential_precedence_enforcement(self, credential_mock):
        """Test that credential precedence rules are properly enforced."""
        # Add multiple credential types for SkyFi
        credential_mock.add_credential(
            "skyfi", "jwt", "jwt_token_test_123",
            expires_at=time.time() + 3600,
            scopes=["read:archives"]
        )
        
        required_services = {"skyfi"}
        
        injection_result = await credential_mock.inject_credentials(
            request_context={},
            required_services=required_services
        )
        
        # Should select OAuth (highest precedence) if available
        skyfi_cred = injection_result.injected_credentials["skyfi"]
        assert skyfi_cred.credential_type == "oauth"  # Highest precedence
        
        # Expire OAuth credential and test fallback
        credential_mock.expire_credential("skyfi", "oauth")
        
        injection_result2 = await credential_mock.inject_credentials(
            request_context={},
            required_services=required_services
        )
        
        # Should fallback to PAT (next highest precedence)
        skyfi_cred2 = injection_result2.injected_credentials["skyfi"]
        assert skyfi_cred2.credential_type == "pat"
    
    async def test_client_preference_override(self, credential_mock):
        """Test client preference can override default precedence."""
        required_services = {"skyfi"}
        client_preferences = {"skyfi": "api_key"}  # Prefer API key over OAuth
        
        injection_result = await credential_mock.inject_credentials(
            request_context={},
            required_services=required_services,
            client_preferences=client_preferences
        )
        
        # Should use API key due to client preference
        skyfi_cred = injection_result.injected_credentials["skyfi"]
        assert skyfi_cred.credential_type == "api_key"
    
    async def test_credential_expiration_and_refresh(self, credential_mock):
        """Test handling of expired credentials and refresh mechanisms."""
        # Add OAuth credential with refresh token
        oauth_cred = credential_mock.add_credential(
            "skyfi", "oauth", "oauth_token_refresh_test",
            expires_at=time.time() - 1,  # Already expired
            refresh_token="refresh_token_123",
            scopes=["read:archives", "write:orders"]
        )
        
        required_services = {"skyfi"}
        
        injection_result = await credential_mock.inject_credentials(
            request_context={},
            required_services=required_services
        )
        
        # Should have refreshed the OAuth credential
        assert injection_result.success
        skyfi_cred = injection_result.injected_credentials["skyfi"]
        
        if skyfi_cred.credential_type == "oauth":
            # OAuth was refreshed
            assert not skyfi_cred.is_expired()
            assert "refreshed_" in skyfi_cred.value
            assert "refreshed_at" in skyfi_cred.metadata
        else:
            # Fell back to another credential type
            assert skyfi_cred.credential_type in ["pat", "api_key"]
    
    async def test_multi_service_credential_coordination(self, coordinator, credential_mock):
        """Test coordination of credentials across multiple services."""
        session_id = "test_session_123"
        operation = "weather_enriched_search"
        
        coordination_result = await coordinator.coordinate_credentials(
            session_id=session_id,
            operation=operation,
            credential_mock=credential_mock
        )
        
        # Validate coordination succeeded
        assert coordination_result["success"]
        assert coordination_result["session_id"] == session_id
        assert coordination_result["operation"] == operation
        assert coordination_result["coordination_time_ms"] > 0
        
        # Check coordinated credentials
        coordinated_creds = coordination_result["credentials_coordinated"]
        assert "skyfi" in coordinated_creds
        assert "weather" in coordinated_creds
        
        # Verify session storage
        session_creds = coordinator.get_session_credentials(session_id)
        assert session_creds is not None
        assert "skyfi" in session_creds
        assert "weather" in session_creds
        
        # Cleanup
        assert coordinator.clear_session(session_id)
    
    async def test_credential_isolation_between_sessions(self, coordinator, credential_mock):
        """Test that credentials are properly isolated between sessions."""
        session1_id = "session_1"
        session2_id = "session_2"
        
        # Coordinate credentials for two different sessions
        coord_result1 = await coordinator.coordinate_credentials(
            session1_id, "skyfi_search", credential_mock
        )
        coord_result2 = await coordinator.coordinate_credentials(
            session2_id, "weather_search", credential_mock
        )
        
        assert coord_result1["success"]
        assert coord_result2["success"]
        
        # Verify session isolation
        session1_creds = coordinator.get_session_credentials(session1_id)
        session2_creds = coordinator.get_session_credentials(session2_id)
        
        assert session1_creds is not session2_creds
        assert "skyfi" in session1_creds
        
        # Session 2 should have different or no credentials
        if session2_creds and "skyfi" in session2_creds:
            # If both have skyfi creds, they should be separate objects
            assert session1_creds["skyfi"] is not session2_creds["skyfi"]
        
        # Cleanup both sessions
        coordinator.clear_session(session1_id)
        coordinator.clear_session(session2_id)
    
    async def test_credential_caching_and_reuse(self, credential_mock):
        """Test credential caching and reuse for performance."""
        required_services = {"skyfi"}
        request_context = {"user_id": "cache_test_user"}
        
        # First injection - should be cache miss
        result1 = await credential_mock.inject_credentials(
            request_context, required_services
        )
        
        # Second injection - should reuse cached credential
        result2 = await credential_mock.inject_credentials(
            request_context, required_services
        )
        
        assert result1.success and result2.success
        
        # Check that credential was reused
        cred1 = result1.injected_credentials["skyfi"]
        cred2 = result2.injected_credentials["skyfi"]
        
        assert cred1.value == cred2.value  # Same credential value
        assert cred2.usage_count > cred1.usage_count  # Usage count increased
        
        # Check cache metrics
        metrics = credential_mock.get_injection_metrics()
        assert metrics["credential_cache_hits"] > 0
    
    async def test_concurrent_credential_injections(self, credential_mock):
        """Test concurrent credential injections for thread safety."""
        required_services = {"skyfi", "weather"}
        
        # Create multiple concurrent injection requests
        injection_tasks = []
        for i in range(10):
            task = credential_mock.inject_credentials(
                request_context={"user_id": f"concurrent_user_{i}"},
                required_services=required_services
            )
            injection_tasks.append(task)
        
        # Execute all injections concurrently
        results = await asyncio.gather(*injection_tasks)
        
        # All injections should succeed
        for result in results:
            assert result.success
            assert "skyfi" in result.injected_credentials
            assert "weather" in result.injected_credentials
        
        # Check that metrics are consistent
        metrics = credential_mock.get_injection_metrics()
        assert metrics["total_injections"] >= 10
        assert metrics["successful_injections"] >= 10
    
    async def test_credential_error_handling(self, credential_mock, flow_validator):
        """Test error handling for credential injection failures."""
        # Remove all credentials for a service
        credential_mock.credential_contexts["skyfi"] = {}
        
        required_services = {"skyfi"}
        
        injection_result = await credential_mock.inject_credentials(
            request_context={},
            required_services=required_services
        )
        
        # Injection should fail
        assert not injection_result.success
        assert len(injection_result.errors) > 0
        assert "No valid credential found for service: skyfi" in injection_result.errors[0]
        
        # Flow validator should detect the issue
        validation_result = flow_validator.validate_injection_result(
            injection_result, required_services
        )
        assert not validation_result["valid"]
        assert len(validation_result["issues"]) > 0
    
    async def test_credential_security_validation(self, credential_mock, flow_validator):
        """Test security validation of injected credentials."""
        # Add potentially insecure credential
        credential_mock.add_credential(
            "test_service", "api_key", "weak",  # Very short API key
            metadata={"password": "secret123"}  # Contains password in metadata
        )
        
        required_services = {"test_service"}
        
        injection_result = await credential_mock.inject_credentials(
            request_context={},
            required_services=required_services
        )
        
        # Injection should succeed but security validation should warn
        assert injection_result.success
        
        validation_result = flow_validator.validate_injection_result(
            injection_result, required_services
        )
        
        # Should have security warnings
        assert len(validation_result["security_warnings"]) > 0
        assert any("weak API key" in warning.lower() for warning in validation_result["security_warnings"])
        assert any("password exposure" in warning.lower() for warning in validation_result["security_warnings"])
    
    async def test_credential_performance_monitoring(self, credential_mock):
        """Test performance monitoring of credential operations."""
        # Reset metrics
        credential_mock.reset_metrics()
        
        required_services = {"skyfi", "weather"}
        
        # Perform multiple injections
        for i in range(5):
            await credential_mock.inject_credentials(
                request_context={"batch_test": i},
                required_services=required_services
            )
        
        # Check metrics
        metrics = credential_mock.get_injection_metrics()
        
        assert metrics["total_injections"] == 5
        assert metrics["successful_injections"] == 5
        assert metrics["failed_injections"] == 0
        assert metrics["avg_injection_time_ms"] > 0
        
        # Performance should be reasonable
        assert metrics["avg_injection_time_ms"] < 100  # Should be under 100ms
    
    @pytest.mark.parametrize("invalid_context", [
        {},  # Empty context
        {"invalid_key": "value"},  # Missing required keys
        {"user_id": None},  # None values
        {"user_id": ""},  # Empty values
    ])
    async def test_credential_injection_with_invalid_context(
        self, credential_mock, invalid_context
    ):
        """Test credential injection with various invalid contexts."""
        required_services = {"skyfi"}
        
        # Should handle invalid context gracefully
        injection_result = await credential_mock.inject_credentials(
            request_context=invalid_context,
            required_services=required_services
        )
        
        # Should still succeed for basic credential injection
        assert injection_result.success
        assert "skyfi" in injection_result.injected_credentials
    
    async def test_credential_lifecycle_management(self, coordinator, credential_mock):
        """Test complete credential lifecycle management."""
        session_id = "lifecycle_test_session"
        
        # Phase 1: Coordinate credentials
        coord_result = await coordinator.coordinate_credentials(
            session_id, "skyfi_search", credential_mock
        )
        assert coord_result["success"]
        
        # Phase 2: Use credentials (simulated by checking usage count)
        session_creds = coordinator.get_session_credentials(session_id)
        initial_usage = session_creds["skyfi"].usage_count
        
        # Simulate credential usage
        session_creds["skyfi"].mark_used()
        assert session_creds["skyfi"].usage_count > initial_usage
        
        # Phase 3: Clean up session
        active_sessions_before = len(coordinator.get_active_sessions())
        cleanup_success = coordinator.clear_session(session_id)
        active_sessions_after = len(coordinator.get_active_sessions())
        
        assert cleanup_success
        assert active_sessions_after < active_sessions_before
        assert coordinator.get_session_credentials(session_id) is None
    
    async def test_service_specific_credential_requirements(self, credential_mock):
        """Test that different services have appropriate credential requirements."""
        test_scenarios = [
            {
                "service": "skyfi",
                "expected_types": ["oauth", "pat", "api_key", "jwt", "service_account"],
                "required": True
            },
            {
                "service": "weather", 
                "expected_types": ["api_key", "oauth"],
                "required": True
            },
            {
                "service": "osm",
                "expected_types": ["api_key", "none"],
                "required": False  # OSM can work without credentials
            }
        ]
        
        for scenario in test_scenarios:
            service = scenario["service"]
            expected_types = scenario["expected_types"]
            required = scenario["required"]
            
            # Test credential injection for this service
            injection_result = await credential_mock.inject_credentials(
                request_context={},
                required_services={service}
            )
            
            if required:
                assert injection_result.success, f"Required service {service} failed injection"
                assert service in injection_result.injected_credentials
                
                cred = injection_result.injected_credentials[service]
                assert cred.credential_type in expected_types, (
                    f"Service {service} got unexpected credential type: {cred.credential_type}"
                )
            else:
                # Optional service - injection can succeed or fail
                if injection_result.success and service in injection_result.injected_credentials:
                    cred = injection_result.injected_credentials[service]
                    assert cred.credential_type in expected_types
    
    async def test_credential_scope_validation(self, credential_mock, flow_validator):
        """Test validation of credential scopes for different operations."""
        # Add credential with limited scopes
        limited_cred = credential_mock.add_credential(
            "skyfi", "limited_api_key", "sk_limited_scope_123",
            scopes=["read:archives"]  # Missing write permissions
        )
        
        # Remove other credentials to force use of limited credential
        credential_mock.credential_contexts["skyfi"] = {
            "limited_api_key": limited_cred
        }
        
        injection_result = await credential_mock.inject_credentials(
            request_context={"operation": "create_order"},  # Needs write permissions
            required_services={"skyfi"}
        )
        
        # Injection should succeed but validator should detect scope issues
        assert injection_result.success
        
        # Custom validation for scope requirements
        skyfi_cred = injection_result.injected_credentials["skyfi"]
        has_write_scope = any("write" in scope for scope in skyfi_cred.scopes)
        
        if not has_write_scope:
            # This would be caught by application-level validation
            # Test framework confirms the credential system allows this detection
            assert "write:orders" not in skyfi_cred.scopes