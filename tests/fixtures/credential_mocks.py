"""
Dynamic Credential Management Mocking Framework

This module provides comprehensive mocking for dynamic credential handling,
including client credential flows, credential injection, and multi-service
credential coordination for testing the SkyFi MCP server.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Set
from unittest.mock import AsyncMock, MagicMock
import httpx
import respx


@dataclass
class CredentialContext:
    """Context for dynamic credential management."""
    service_name: str
    credential_type: str  # 'api_key', 'oauth', 'pat', 'jwt', 'service_account'
    value: str
    expires_at: Optional[float] = None
    scopes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_used: Optional[float] = None
    usage_count: int = 0
    is_dynamic: bool = True
    refresh_token: Optional[str] = None
    
    def is_expired(self) -> bool:
        """Check if credential is expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at
    
    def mark_used(self) -> None:
        """Mark credential as used."""
        self.last_used = time.time()
        self.usage_count += 1


@dataclass
class CredentialInjectionResult:
    """Result of credential injection operation."""
    success: bool
    injected_credentials: Dict[str, CredentialContext] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    injection_time_ms: float = 0.0
    precedence_order: List[str] = field(default_factory=list)


class DynamicCredentialMock:
    """Mock for dynamic credential management and injection."""
    
    def __init__(self):
        # Active credential contexts by service
        self.credential_contexts: Dict[str, Dict[str, CredentialContext]] = {}
        
        # Credential precedence rules
        self.precedence_rules = {
            "skyfi": ["oauth", "pat", "api_key", "jwt", "service_account"],
            "weather": ["api_key", "oauth"],
            "osm": ["api_key", "none"]  # OSM doesn't require auth but supports API keys
        }
        
        # Performance tracking
        self.injection_metrics = {
            "total_injections": 0,
            "successful_injections": 0,
            "failed_injections": 0,
            "avg_injection_time_ms": 0.0,
            "credential_cache_hits": 0,
            "credential_cache_misses": 0
        }
        
        # Setup default credentials
        self._setup_default_credentials()
    
    def _setup_default_credentials(self):
        """Setup default credentials for testing."""
        # SkyFi credentials
        self.credential_contexts["skyfi"] = {
            "oauth": CredentialContext(
                service_name="skyfi",
                credential_type="oauth",
                value="oauth_token_skyfi_valid_12345",
                expires_at=time.time() + 3600,
                scopes=["read:archives", "write:orders", "read:account"],
                metadata={"user_id": "user_123", "org_id": "org_456"}
            ),
            "pat": CredentialContext(
                service_name="skyfi",
                credential_type="pat",
                value="skyfi_pat_dynamic_token_67890",
                expires_at=time.time() + (365 * 24 * 3600),
                scopes=["read:archives", "write:orders"],
                metadata={"user_id": "user_789", "created_by": "test_system"}
            ),
            "api_key": CredentialContext(
                service_name="skyfi",
                credential_type="api_key",
                value="sk_test_dynamic_api_key_abc123",
                scopes=["read:archives"],
                metadata={"rate_limit": {"rpm": 100, "rph": 1000}}
            )
        }
        
        # Weather service credentials
        self.credential_contexts["weather"] = {
            "api_key": CredentialContext(
                service_name="weather",
                credential_type="api_key",
                value="weather_api_key_xyz789",
                scopes=["read:current", "read:forecast"],
                metadata={"provider": "openweathermap"}
            )
        }
        
        # OSM credentials (optional)
        self.credential_contexts["osm"] = {
            "api_key": CredentialContext(
                service_name="osm",
                credential_type="api_key", 
                value="osm_api_key_optional_456",
                scopes=["read:geocoding"],
                metadata={"provider": "nominatim", "rate_limit": {"rpm": 60}}
            )
        }
    
    async def inject_credentials(
        self,
        request_context: Dict[str, Any],
        required_services: Set[str],
        client_preferences: Optional[Dict[str, str]] = None
    ) -> CredentialInjectionResult:
        """
        Inject credentials dynamically based on request context and service requirements.
        
        Args:
            request_context: Context of the current request
            required_services: Set of services that need credentials
            client_preferences: Client preference for credential types per service
            
        Returns:
            CredentialInjectionResult with injection details
        """
        start_time = time.perf_counter()
        result = CredentialInjectionResult(success=True)
        
        try:
            for service in required_services:
                # Get credential precedence for this service
                precedence = self.precedence_rules.get(service, ["api_key"])
                result.precedence_order.extend([f"{service}:{cred}" for cred in precedence])
                
                # Apply client preferences if provided
                if client_preferences and service in client_preferences:
                    preferred_type = client_preferences[service]
                    if preferred_type in precedence:
                        # Move preferred type to front
                        precedence = [preferred_type] + [c for c in precedence if c != preferred_type]
                
                # Find best available credential
                injected_credential = await self._find_best_credential(service, precedence)
                
                if injected_credential:
                    # Inject the credential
                    result.injected_credentials[service] = injected_credential
                    injected_credential.mark_used()
                    
                    # Update cache metrics
                    if injected_credential.usage_count > 1:
                        self.injection_metrics["credential_cache_hits"] += 1
                    else:
                        self.injection_metrics["credential_cache_misses"] += 1
                else:
                    # Handle missing credential
                    if service == "osm":
                        # OSM can work without credentials
                        continue
                    else:
                        result.errors.append(f"No valid credential found for service: {service}")
                        result.success = False
            
            # Update metrics
            self.injection_metrics["total_injections"] += 1
            if result.success:
                self.injection_metrics["successful_injections"] += 1
            else:
                self.injection_metrics["failed_injections"] += 1
                
        except Exception as e:
            result.success = False
            result.errors.append(f"Credential injection failed: {str(e)}")
            self.injection_metrics["failed_injections"] += 1
        
        # Calculate injection time
        end_time = time.perf_counter()
        result.injection_time_ms = (end_time - start_time) * 1000
        
        # Update average injection time
        total_time = (self.injection_metrics["avg_injection_time_ms"] * 
                     (self.injection_metrics["total_injections"] - 1) + 
                     result.injection_time_ms)
        self.injection_metrics["avg_injection_time_ms"] = total_time / self.injection_metrics["total_injections"]
        
        return result
    
    async def _find_best_credential(
        self, 
        service: str, 
        precedence: List[str]
    ) -> Optional[CredentialContext]:
        """Find the best available credential for a service."""
        service_credentials = self.credential_contexts.get(service, {})
        
        for cred_type in precedence:
            if cred_type in service_credentials:
                credential = service_credentials[cred_type]
                
                # Check if credential is valid
                if not credential.is_expired():
                    return credential
                else:
                    # Try to refresh if possible
                    refreshed = await self._refresh_credential(credential)
                    if refreshed:
                        return refreshed
        
        return None
    
    async def _refresh_credential(self, credential: CredentialContext) -> Optional[CredentialContext]:
        """Attempt to refresh an expired credential."""
        if not credential.refresh_token or credential.credential_type != "oauth":
            return None
        
        # Simulate OAuth refresh
        await asyncio.sleep(0.01)  # Simulate network call
        
        # Update credential with new values
        credential.value = f"refreshed_{credential.value}_{int(time.time())}"
        credential.expires_at = time.time() + 3600
        credential.metadata["refreshed_at"] = time.time()
        
        return credential
    
    def add_credential(
        self, 
        service: str, 
        credential_type: str, 
        value: str,
        **kwargs
    ) -> CredentialContext:
        """Add a new credential to the mock."""
        if service not in self.credential_contexts:
            self.credential_contexts[service] = {}
            
        credential = CredentialContext(
            service_name=service,
            credential_type=credential_type,
            value=value,
            **kwargs
        )
        
        self.credential_contexts[service][credential_type] = credential
        return credential
    
    def remove_credential(self, service: str, credential_type: str) -> bool:
        """Remove a credential from the mock."""
        if (service in self.credential_contexts and 
            credential_type in self.credential_contexts[service]):
            del self.credential_contexts[service][credential_type]
            return True
        return False
    
    def expire_credential(self, service: str, credential_type: str) -> bool:
        """Mark a credential as expired."""
        if (service in self.credential_contexts and 
            credential_type in self.credential_contexts[service]):
            self.credential_contexts[service][credential_type].expires_at = time.time() - 1
            return True
        return False
    
    def get_injection_metrics(self) -> Dict[str, Any]:
        """Get credential injection performance metrics."""
        return self.injection_metrics.copy()
    
    def reset_metrics(self):
        """Reset all performance metrics."""
        self.injection_metrics = {
            "total_injections": 0,
            "successful_injections": 0,
            "failed_injections": 0,
            "avg_injection_time_ms": 0.0,
            "credential_cache_hits": 0,
            "credential_cache_misses": 0
        }


class CredentialFlowValidator:
    """Validator for credential flow compliance and security."""
    
    def __init__(self):
        self.validation_rules = {
            "precedence_compliance": True,
            "credential_isolation": True,
            "secure_storage": True,
            "audit_logging": True,
            "refresh_handling": True
        }
        
    def validate_injection_result(
        self, 
        injection_result: CredentialInjectionResult,
        expected_services: Set[str]
    ) -> Dict[str, Any]:
        """Validate a credential injection result."""
        validation_result = {
            "valid": True,
            "issues": [],
            "security_warnings": [],
            "performance_warnings": []
        }
        
        # Check all required services have credentials
        missing_services = expected_services - set(injection_result.injected_credentials.keys())
        if missing_services and "osm" not in missing_services:  # OSM is optional
            validation_result["valid"] = False
            validation_result["issues"].append(f"Missing credentials for services: {missing_services}")
        
        # Check injection performance
        if injection_result.injection_time_ms > 50:  # 50ms threshold
            validation_result["performance_warnings"].append(
                f"Slow credential injection: {injection_result.injection_time_ms:.2f}ms"
            )
        
        # Check for expired credentials
        for service, credential in injection_result.injected_credentials.items():
            if credential.is_expired():
                validation_result["valid"] = False
                validation_result["issues"].append(f"Expired credential for service: {service}")
        
        # Security validation
        self._validate_credential_security(injection_result, validation_result)
        
        return validation_result
    
    def _validate_credential_security(
        self, 
        injection_result: CredentialInjectionResult,
        validation_result: Dict[str, Any]
    ):
        """Validate security aspects of credential injection."""
        for service, credential in injection_result.injected_credentials.items():
            # Check for credential exposure in metadata
            if "password" in str(credential.metadata).lower():
                validation_result["security_warnings"].append(
                    f"Potential password exposure in {service} credential metadata"
                )
            
            # Check credential format
            if credential.credential_type == "api_key" and len(credential.value) < 16:
                validation_result["security_warnings"].append(
                    f"Potentially weak API key for service: {service}"
                )
            
            # Check scope restrictions
            if not credential.scopes:
                validation_result["security_warnings"].append(
                    f"No scope restrictions on {service} credential"
                )


class MultiServiceCredentialCoordinator:
    """Coordinator for managing credentials across multiple services."""
    
    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, CredentialContext]] = {}
        self.credential_dependencies = {
            # Define which services need credentials from others
            "skyfi_orders": ["skyfi"],  # Orders need SkyFi auth
            "weather_enriched_search": ["skyfi", "weather"],  # Combined search
            "geocoded_archive_search": ["skyfi", "osm"]  # Geographic search
        }
        
    async def coordinate_credentials(
        self,
        session_id: str,
        operation: str,
        credential_mock: DynamicCredentialMock
    ) -> Dict[str, Any]:
        """Coordinate credentials for multi-service operations."""
        coordination_result = {
            "session_id": session_id,
            "operation": operation,
            "credentials_coordinated": {},
            "coordination_time_ms": 0.0,
            "success": True,
            "issues": []
        }
        
        start_time = time.perf_counter()
        
        try:
            # Determine required services for operation
            required_services = self._get_required_services(operation)
            
            # Inject credentials for all required services
            injection_result = await credential_mock.inject_credentials(
                request_context={"session_id": session_id, "operation": operation},
                required_services=required_services
            )
            
            if injection_result.success:
                # Store credentials in session
                self.active_sessions[session_id] = injection_result.injected_credentials
                coordination_result["credentials_coordinated"] = {
                    service: {
                        "type": cred.credential_type,
                        "scopes": cred.scopes,
                        "expires_at": cred.expires_at
                    }
                    for service, cred in injection_result.injected_credentials.items()
                }
            else:
                coordination_result["success"] = False
                coordination_result["issues"] = injection_result.errors
                
        except Exception as e:
            coordination_result["success"] = False
            coordination_result["issues"].append(f"Coordination failed: {str(e)}")
        
        # Calculate coordination time
        end_time = time.perf_counter()
        coordination_result["coordination_time_ms"] = (end_time - start_time) * 1000
        
        return coordination_result
    
    def _get_required_services(self, operation: str) -> Set[str]:
        """Get required services for an operation."""
        if operation in self.credential_dependencies:
            return set(self.credential_dependencies[operation])
        
        # Default service requirements based on operation name
        if "skyfi" in operation:
            return {"skyfi"}
        elif "weather" in operation:
            return {"weather"}
        elif "geocode" in operation or "osm" in operation:
            return {"osm"}
        else:
            return {"skyfi"}  # Default to SkyFi
    
    def get_session_credentials(self, session_id: str) -> Optional[Dict[str, CredentialContext]]:
        """Get active credentials for a session."""
        return self.active_sessions.get(session_id)
    
    def clear_session(self, session_id: str) -> bool:
        """Clear credentials for a session."""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            return True
        return False
    
    def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs."""
        return list(self.active_sessions.keys())


# Export classes for testing
__all__ = [
    "CredentialContext",
    "CredentialInjectionResult", 
    "DynamicCredentialMock",
    "CredentialFlowValidator",
    "MultiServiceCredentialCoordinator"
]