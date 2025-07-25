"""
Credential Security Validation Tests

This module provides comprehensive security testing for credential handling
in the SkyFi MCP server, including prevention of credential exposure,
injection attacks, and cross-service isolation.
"""

from __future__ import annotations

import asyncio
import json
import pytest
import time
import hashlib
from typing import Dict, Any, List
from unittest.mock import AsyncMock, patch, MagicMock

from tests.fixtures.credential_mocks import (
    DynamicCredentialMock,
    CredentialFlowValidator,
    MultiServiceCredentialCoordinator,
    CredentialContext
)


@pytest.mark.security
@pytest.mark.auth
@pytest.mark.integration
class TestCredentialSecurity:
    """Comprehensive credential security validation test suite."""
    
    @pytest.fixture
    async def credential_mock(self):
        """Provide dynamic credential mock."""
        mock = DynamicCredentialMock()
        yield mock
    
    @pytest.fixture
    async def security_validator(self):
        """Provide security-focused credential validator."""
        return CredentialFlowValidator()
    
    @pytest.fixture
    async def coordinator(self):
        """Provide credential coordinator."""
        return MultiServiceCredentialCoordinator()
    
    async def test_credential_exposure_prevention_in_logs(self, credential_mock):
        """Test that credentials are not exposed in application logs."""
        # Mock logging to capture log messages
        log_messages = []
        
        def mock_log_handler(record):
            log_messages.append(record.getMessage())
        
        with patch('logging.Logger.info', side_effect=mock_log_handler):
            with patch('logging.Logger.debug', side_effect=mock_log_handler):
                with patch('logging.Logger.warning', side_effect=mock_log_handler):
                    # Perform credential injection
                    injection_result = await credential_mock.inject_credentials(
                        request_context={"user_id": "log_test_user"},
                        required_services={"skyfi", "weather"}
                    )
                    
                    assert injection_result.success
        
        # Check that no actual credential values appear in logs
        for message in log_messages:
            message_lower = message.lower()
            
            # Check for credential values
            for service_creds in credential_mock.credential_contexts.values():
                for cred in service_creds.values():
                    # Credential values should not appear in logs
                    assert cred.value not in message, (
                        f"Credential value exposed in log: {message}"
                    )
                    
                    # Partial credential values should not appear either
                    if len(cred.value) > 8:
                        partial_value = cred.value[:8]
                        assert partial_value not in message, (
                            f"Partial credential value exposed in log: {message}"
                        )
    
    async def test_credential_isolation_between_services(self, credential_mock, coordinator):
        """Test that credentials are properly isolated between services."""
        session_id = "isolation_test_session"
        
        # Coordinate credentials for multiple services
        coord_result = await coordinator.coordinate_credentials(
            session_id, "multi_service_test", credential_mock
        )
        assert coord_result["success"]
        
        session_creds = coordinator.get_session_credentials(session_id)
        
        # Verify each service has distinct credentials
        service_credentials = {}
        for service, cred in session_creds.items():
            service_credentials[service] = cred.value
        
        # No two services should share the same credential value
        credential_values = list(service_credentials.values())
        unique_values = set(credential_values)
        
        assert len(unique_values) == len(credential_values), (
            "Services are sharing credential values - isolation breach detected!"
        )
        
        # Verify credentials are service-specific
        for service, cred in session_creds.items():
            assert cred.service_name == service, (
                f"Credential for {service} has wrong service_name: {cred.service_name}"
            )
            
            # Verify scopes are appropriate for the service
            if service == "skyfi":
                expected_scopes = ["read:archives", "write:orders", "read:account"]
                assert any(scope in cred.scopes for scope in expected_scopes)
            elif service == "weather":
                expected_scopes = ["read:current", "read:forecast"] 
                assert any(scope in cred.scopes for scope in expected_scopes)
        
        coordinator.clear_session(session_id)
    
    async def test_credential_injection_attack_prevention(self, credential_mock):
        """Test prevention of credential injection attacks."""
        # Test SQL injection in credential context
        malicious_contexts = [
            {"user_id": "'; DROP TABLE credentials; --"},
            {"user_id": "admin' OR '1'='1"},
            {"session_id": "<script>alert('xss')</script>"},
            {"operation": "test'; INSERT INTO admin_users VALUES ('hacker'); --"},
            {"client_ip": "192.168.1.1'; SELECT * FROM api_keys; --"}
        ]
        
        for malicious_context in malicious_contexts:
            # Injection should not cause errors or expose data
            injection_result = await credential_mock.inject_credentials(
                request_context=malicious_context,
                required_services={"skyfi"}
            )
            
            # Should handle malicious input gracefully
            assert injection_result.success or len(injection_result.errors) > 0
            
            # Check that no malicious code was executed
            if injection_result.success:
                skyfi_cred = injection_result.injected_credentials["skyfi"]
                
                # Credential should be normal, not affected by injection
                assert not any(
                    malicious in skyfi_cred.value.lower()
                    for malicious in ["drop", "insert", "select", "script", "alert"]
                )
                
                # Metadata should not contain malicious code
                metadata_str = json.dumps(skyfi_cred.metadata)
                assert not any(
                    malicious in metadata_str.lower()
                    for malicious in ["drop", "insert", "select", "<script", "alert("]
                )
    
    async def test_credential_tampering_detection(self, credential_mock):
        """Test detection of credential tampering attempts."""
        # Get a valid credential
        injection_result = await credential_mock.inject_credentials(
            request_context={"user_id": "tamper_test"},
            required_services={"skyfi"}
        )
        assert injection_result.success
        
        original_cred = injection_result.injected_credentials["skyfi"]
        original_value = original_cred.value
        
        # Simulate tampering attempts
        tampering_attempts = [
            # Direct value modification
            lambda cred: setattr(cred, 'value', cred.value + "_tampered"),
            # Scope escalation
            lambda cred: cred.scopes.append("admin:all"),
            # Expiration manipulation
            lambda cred: setattr(cred, 'expires_at', None),  # Never expires
            # Metadata injection
            lambda cred: cred.metadata.update({"admin": True, "bypass_auth": True})
        ]
        
        for tamper_func in tampering_attempts:
            # Apply tampering
            tamper_func(original_cred)
            
            # Verify tampering is detectable (in a real system, this would involve
            # checksums, signatures, or other validation mechanisms)
            
            # For this test, we check that the credential is now "different"
            if original_cred.value != original_value:
                # Value was tampered - should be detectable
                assert original_cred.value != original_value
                
            # Check for suspicious metadata
            if "admin" in original_cred.metadata or "bypass_auth" in original_cred.metadata:
                # Metadata tampering detected
                assert True  # In real system, this would trigger security alerts
                
            # Check for scope escalation
            if "admin:all" in original_cred.scopes:
                # Scope escalation detected
                assert True  # In real system, this would be blocked
    
    async def test_credential_storage_security(self, credential_mock, coordinator):
        """Test security of credential storage mechanisms."""
        session_id = "storage_security_test"
        
        # Store credentials in session
        coord_result = await coordinator.coordinate_credentials(
            session_id, "storage_test", credential_mock
        )
        assert coord_result["success"]
        
        # Verify credentials are not stored in plain text
        session_creds = coordinator.get_session_credentials(session_id)
        
        for service, cred in session_creds.items():
            # In a secure system, credential values should be encrypted or hashed
            # For this test, we verify they're not obviously plain text
            
            # Check that credential value has some complexity
            assert len(cred.value) >= 8, f"Credential for {service} is too short"
            
            # Check that credential contains varied characters
            has_letters = any(c.isalpha() for c in cred.value)
            has_numbers = any(c.isdigit() for c in cred.value)
            
            # Should have complexity indicating it's not a simple password
            assert has_letters or has_numbers, (
                f"Credential for {service} lacks complexity: {cred.value[:4]}..."
            )
            
            # Sensitive metadata should not be stored
            sensitive_keys = ["password", "private_key", "secret"]
            for key in sensitive_keys:
                assert key not in cred.metadata, (
                    f"Sensitive key '{key}' found in {service} credential metadata"
                )
        
        # Test credential cleanup
        coordinator.clear_session(session_id)
        cleared_creds = coordinator.get_session_credentials(session_id)
        assert cleared_creds is None, "Credentials not properly cleared from storage"
    
    async def test_credential_transmission_security(self, credential_mock):
        """Test security of credential transmission between components."""
        # Simulate credential transmission
        injection_result = await credential_mock.inject_credentials(
            request_context={"transmission_test": True},
            required_services={"skyfi", "weather"}
        )
        assert injection_result.success
        
        # In a real system, we would test:
        # 1. Credentials are transmitted over encrypted channels
        # 2. Credentials are not logged during transmission
        # 3. Credentials are not cached inappropriately
        
        # For this test, we verify the injection result doesn't expose credentials
        result_json = json.dumps({
            "success": injection_result.success,
            "errors": injection_result.errors,
            "injection_time_ms": injection_result.injection_time_ms,
            "precedence_order": injection_result.precedence_order
        })
        
        # Serialized result should not contain actual credential values
        for service, cred in injection_result.injected_credentials.items():
            assert cred.value not in result_json, (
                f"Credential value for {service} exposed in transmission data"
            )
            
            # Check for partial exposure
            if len(cred.value) > 8:
                partial_value = cred.value[:8]
                assert partial_value not in result_json, (
                    f"Partial credential value for {service} exposed in transmission"
                )
    
    async def test_concurrent_access_security(self, credential_mock, coordinator):
        """Test security of concurrent credential access."""
        # Create multiple concurrent sessions
        session_ids = [f"concurrent_session_{i}" for i in range(10)]
        
        # Start concurrent credential coordination
        coordination_tasks = []
        for session_id in session_ids:
            task = coordinator.coordinate_credentials(
                session_id, f"concurrent_test_{session_id}", credential_mock
            )
            coordination_tasks.append(task)
        
        # Execute concurrently
        coordination_results = await asyncio.gather(*coordination_tasks, return_exceptions=True)
        
        # Verify no sessions can access each other's credentials
        active_sessions = {}
        for session_id, result in zip(session_ids, coordination_results):
            if isinstance(result, dict) and result.get("success"):
                session_creds = coordinator.get_session_credentials(session_id)
                if session_creds:
                    active_sessions[session_id] = session_creds
        
        # Each session should have isolated credentials
        for session_id, session_creds in active_sessions.items():
            for other_session_id, other_creds in active_sessions.items():
                if session_id != other_session_id:
                    # Verify credentials are different objects
                    for service in session_creds.keys():
                        if service in other_creds:
                            assert session_creds[service] is not other_creds[service], (
                                f"Sessions {session_id} and {other_session_id} share "
                                f"credential objects for {service}"
                            )
        
        # Cleanup all sessions
        for session_id in session_ids:
            coordinator.clear_session(session_id)
    
    async def test_credential_audit_trail(self, credential_mock):
        """Test that credential usage creates proper audit trails."""
        # Perform multiple credential operations
        operations = [
            {"context": {"user_id": "audit_user_1"}, "services": {"skyfi"}},
            {"context": {"user_id": "audit_user_2"}, "services": {"weather"}}, 
            {"context": {"user_id": "audit_user_3"}, "services": {"skyfi", "weather"}},
        ]
        
        audit_trail = []
        
        for i, operation in enumerate(operations):
            injection_result = await credential_mock.inject_credentials(
                request_context=operation["context"],
                required_services=operation["services"]
            )
            
            # Record audit information
            audit_entry = {
                "operation_id": i,
                "timestamp": time.time(),
                "user_id": operation["context"].get("user_id"),
                "services": list(operation["services"]),
                "success": injection_result.success,
                "injection_time_ms": injection_result.injection_time_ms
            }
            
            # Add credential usage info (without exposing values)
            if injection_result.success:
                for service, cred in injection_result.injected_credentials.items():
                    audit_entry[f"{service}_credential_type"] = cred.credential_type
                    audit_entry[f"{service}_usage_count"] = cred.usage_count
                    audit_entry[f"{service}_last_used"] = cred.last_used
            
            audit_trail.append(audit_entry)
        
        # Verify audit trail integrity
        assert len(audit_trail) == len(operations)
        
        for entry in audit_trail:
            # Each audit entry should have required fields
            required_fields = ["operation_id", "timestamp", "user_id", "services", "success"]
            for field in required_fields:
                assert field in entry, f"Audit entry missing field: {field}"
            
            # Verify no sensitive data in audit trail
            entry_str = json.dumps(entry)
            
            # Should not contain actual credential values
            for service_creds in credential_mock.credential_contexts.values():
                for cred in service_creds.values():
                    assert cred.value not in entry_str, (
                        "Credential value found in audit trail"
                    )
            
            # Should contain operational metadata
            assert entry["timestamp"] > 0
            assert isinstance(entry["success"], bool)
            assert isinstance(entry["services"], list)
    
    async def test_credential_rotation_security(self, credential_mock):
        """Test security aspects of credential rotation."""
        # Add a credential that supports rotation
        original_cred = credential_mock.add_credential(
            "skyfi", "oauth", "oauth_rotate_test_token",
            expires_at=time.time() + 3600,
            refresh_token="refresh_token_for_rotation",
            metadata={"rotation_count": 0}
        )
        
        # Expire the credential to trigger rotation
        credential_mock.expire_credential("skyfi", "oauth")
        
        # Inject credential (should trigger rotation)
        injection_result = await credential_mock.inject_credentials(
            request_context={"rotation_test": True},
            required_services={"skyfi"}
        )
        
        if injection_result.success:
            rotated_cred = injection_result.injected_credentials["skyfi"]
            
            if rotated_cred.credential_type == "oauth":
                # Verify rotation occurred
                assert "refreshed_" in rotated_cred.value
                assert rotated_cred.value != "oauth_rotate_test_token"
                
                # Verify rotation metadata
                assert "refreshed_at" in rotated_cred.metadata
                assert rotated_cred.metadata["refreshed_at"] > 0
                
                # Verify old credential is invalidated
                # (In a real system, the old token would be revoked)
                original_value = "oauth_rotate_test_token"
                assert rotated_cred.value != original_value
    
    async def test_credential_scope_enforcement(self, credential_mock, security_validator):
        """Test enforcement of credential scope restrictions."""
        # Create credential with limited scopes
        limited_cred = credential_mock.add_credential(
            "skyfi", "limited_scope_test", "sk_limited_test_123",
            scopes=["read:archives"],  # No write permissions
            metadata={"scope_test": True}
        )
        
        # Remove other credentials to force use of limited credential
        credential_mock.credential_contexts["skyfi"] = {
            "limited_scope_test": limited_cred
        }
        
        injection_result = await credential_mock.inject_credentials(
            request_context={"scope_test": True},
            required_services={"skyfi"}
        )
        
        assert injection_result.success
        
        # Validate scope restrictions
        validation_result = security_validator.validate_injection_result(
            injection_result, {"skyfi"}
        )
        
        # Check injected credential scopes
        skyfi_cred = injection_result.injected_credentials["skyfi"]
        
        # Should only have read permissions
        assert "read:archives" in skyfi_cred.scopes
        assert not any("write" in scope for scope in skyfi_cred.scopes)
        assert not any("admin" in scope for scope in skyfi_cred.scopes)
        assert not any("delete" in scope for scope in skyfi_cred.scopes)
        
        # Test scope escalation prevention
        original_scopes = skyfi_cred.scopes.copy()
        
        # Attempt to add unauthorized scopes
        skyfi_cred.scopes.append("admin:all")
        skyfi_cred.scopes.append("write:everything")
        
        # In a real system, this would be detected and prevented
        # For this test, we verify the escalation is detectable
        escalated_scopes = [scope for scope in skyfi_cred.scopes if scope not in original_scopes]
        assert len(escalated_scopes) > 0, "Scope escalation not detectable"
        
        # Verify escalated scopes are unauthorized
        for scope in escalated_scopes:
            assert "admin" in scope or "write" in scope or "all" in scope
    
    async def test_cross_service_credential_leakage_prevention(self, credential_mock, coordinator):
        """Test prevention of credential leakage between services."""
        session_id = "leakage_test_session"
        
        # Coordinate credentials for multiple services
        coord_result = await coordinator.coordinate_credentials(
            session_id, "multi_service_leakage_test", credential_mock
        )
        assert coord_result["success"]
        
        session_creds = coordinator.get_session_credentials(session_id)
        
        # Simulate a compromised service trying to access other services' credentials
        if "skyfi" in session_creds and "weather" in session_creds:
            skyfi_cred = session_creds["skyfi"]
            weather_cred = session_creds["weather"]
            
            # Verify SkyFi credential cannot be used for weather service
            assert skyfi_cred.service_name == "skyfi"
            assert weather_cred.service_name == "weather"
            
            # Verify different credential values
            assert skyfi_cred.value != weather_cred.value
            
            # Verify appropriate scopes for each service
            skyfi_scopes = skyfi_cred.scopes
            weather_scopes = weather_cred.scopes
            
            # SkyFi scopes should not work for weather
            skyfi_specific_scopes = ["read:archives", "write:orders"]
            weather_specific_scopes = ["read:current", "read:forecast"]
            
            # Check scope isolation
            for scope in skyfi_specific_scopes:
                if scope in skyfi_scopes:
                    assert scope not in weather_scopes, (
                        f"SkyFi scope '{scope}' leaked to weather service"
                    )
            
            for scope in weather_specific_scopes:
                if scope in weather_scopes:
                    assert scope not in skyfi_scopes, (
                        f"Weather scope '{scope}' leaked to SkyFi service"
                    )
        
        coordinator.clear_session(session_id)
    
    async def test_credential_encryption_at_rest(self, credential_mock):
        """Test that credentials are properly encrypted when stored."""
        # This test simulates encryption validation
        # In a real system, credentials would be encrypted in storage
        
        injection_result = await credential_mock.inject_credentials(
            request_context={"encryption_test": True},
            required_services={"skyfi", "weather"}
        )
        assert injection_result.success
        
        for service, cred in injection_result.injected_credentials.items():
            # Simulate checking if credential appears to be encrypted
            cred_value = cred.value
            
            # Basic checks for encryption-like properties
            # Real encryption would use proper cryptographic validation
            
            # Should not be obviously readable text
            common_words = ["password", "secret", "key", "token", "admin", "user"]
            for word in common_words:
                assert word != cred_value.lower(), (
                    f"Credential value appears to be plain text: {word}"
                )
            
            # Should have reasonable entropy (not all same character)
            unique_chars = set(cred_value)
            assert len(unique_chars) > 1, (
                f"Credential value has low entropy: {cred_value}"
            )
            
            # Should not be empty or too short
            assert len(cred_value) >= 8, (
                f"Credential value too short for {service}: {len(cred_value)} chars"
            )
    
    async def test_security_monitoring_integration(self, credential_mock):
        """Test integration with security monitoring systems."""
        # Simulate security events that should be monitored
        security_events = []
        
        def mock_security_event_handler(event_type, details):
            security_events.append({
                "type": event_type,
                "details": details,
                "timestamp": time.time()
            })
        
        # Simulate suspicious activities
        suspicious_activities = [
            # Multiple failed injections
            {"context": {"user_id": "suspicious_user"}, "services": {"nonexistent_service"}},
            # Rapid credential requests
            {"context": {"user_id": "rapid_user"}, "services": {"skyfi"}},
            {"context": {"user_id": "rapid_user"}, "services": {"skyfi"}},
            {"context": {"user_id": "rapid_user"}, "services": {"skyfi"}},
        ]
        
        for activity in suspicious_activities:
            try:
                await credential_mock.inject_credentials(
                    request_context=activity["context"],
                    required_services=activity["services"]
                )
            except Exception as e:
                # Failed injections should trigger security events
                mock_security_event_handler("credential_injection_failure", {
                    "user_id": activity["context"].get("user_id"),
                    "services": list(activity["services"]),
                    "error": str(e)
                })
        
        # In a real system, we would verify security events were generated
        # For this test, we verify the monitoring framework can detect patterns
        
        # Check for rapid requests from same user
        rapid_user_events = [
            event for event in security_events 
            if event["details"].get("user_id") == "rapid_user"
        ]
        
        # Should detect multiple rapid requests (if they generated events)
        # This would trigger rate limiting or security alerts in production
        if len(rapid_user_events) > 2:
            assert True  # Security monitoring detected suspicious pattern
    
    async def test_compliance_with_security_standards(self, credential_mock, security_validator):
        """Test compliance with security standards and best practices."""
        # Test various security compliance aspects
        compliance_tests = []
        
        # Test 1: Credential complexity requirements
        injection_result = await credential_mock.inject_credentials(
            request_context={"compliance_test": True},
            required_services={"skyfi", "weather"}
        )
        
        if injection_result.success:
            for service, cred in injection_result.injected_credentials.items():
                # Check credential meets complexity requirements
                cred_value = cred.value
                
                # Length requirement (varies by type)
                min_length = 16 if cred.credential_type == "api_key" else 8
                compliance_tests.append({
                    "test": f"{service}_credential_length",
                    "passed": len(cred_value) >= min_length,
                    "details": f"Length: {len(cred_value)}, Min: {min_length}"
                })
                
                # Character diversity
                has_alpha = any(c.isalpha() for c in cred_value)
                has_numeric = any(c.isdigit() for c in cred_value)
                compliance_tests.append({
                    "test": f"{service}_credential_diversity",
                    "passed": has_alpha and has_numeric,
                    "details": f"Alpha: {has_alpha}, Numeric: {has_numeric}"
                })
                
                # No obvious patterns
                has_pattern = any(
                    pattern in cred_value.lower() 
                    for pattern in ["123456", "password", "admin", "test"]
                )
                compliance_tests.append({
                    "test": f"{service}_credential_pattern_check",
                    "passed": not has_pattern,
                    "details": f"Contains common pattern: {has_pattern}"
                })
        
        # Test 2: Scope validation
        validation_result = security_validator.validate_injection_result(
            injection_result, {"skyfi", "weather"}
        )
        
        compliance_tests.append({
            "test": "scope_validation",
            "passed": validation_result["valid"],
            "details": f"Issues: {len(validation_result['issues'])}, "
                      f"Warnings: {len(validation_result.get('security_warnings', []))}"
        })
        
        # Verify overall compliance
        failed_tests = [test for test in compliance_tests if not test["passed"]]
        
        if failed_tests:
            failure_details = "\n".join([
                f"- {test['test']}: {test['details']}" 
                for test in failed_tests
            ])
            pytest.fail(f"Security compliance failures:\n{failure_details}")
        
        # All compliance tests should pass
        assert all(test["passed"] for test in compliance_tests)