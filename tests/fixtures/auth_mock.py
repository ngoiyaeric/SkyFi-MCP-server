"""
Authentication Mocking Framework

This module provides comprehensive authentication mocking for testing all
authentication methods supported by the SkyFi MCP server.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, MagicMock

import jwt
import httpx
import respx


@dataclass
class AuthResult:
    """Result of an authentication attempt."""
    valid: bool
    method: str
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    scopes: List[str] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.scopes is None:
            self.scopes = []


class AuthenticationMockSuite:
    """Comprehensive authentication mocking suite supporting all auth methods."""
    
    def __init__(self):
        self.oauth_mock = OAuth2Mock()
        self.pat_mock = PersonalAccessTokenMock()
        self.api_key_mock = APIKeyMock()
        self.jwt_mock = JWTSessionMock()
        self.service_account_mock = ServiceAccountMock()
        
        # Authentication precedence order
        self.auth_precedence = ["oauth", "pat", "api_key", "jwt", "service_account"]
        
    async def setup(self):
        """Initialize all authentication mocks."""
        await self.oauth_mock.setup()
        await self.pat_mock.setup()
        await self.api_key_mock.setup()
        await self.jwt_mock.setup()
        await self.service_account_mock.setup()
        
    async def teardown(self):
        """Cleanup all mocks."""
        await self.oauth_mock.teardown()
        await self.pat_mock.teardown()
        await self.api_key_mock.teardown()
        await self.jwt_mock.teardown()
        await self.service_account_mock.teardown()
        
    async def authenticate(self, headers: Dict[str, str]) -> AuthResult:
        """
        Authenticate using the provided headers with precedence order.
        
        Tests the full authentication hierarchy as implemented in the middleware.
        """
        auth_methods = self._extract_auth_methods(headers)
        
        # Try authentication methods in order of precedence
        for method in self.auth_precedence:
            if auth_methods.get(method):
                result = await self._validate_method(method, auth_methods[method])
                if result.valid:
                    return result
                    
        return AuthResult(
            valid=False,
            method="none",
            error_message="No valid authentication method found"
        )
        
    def _extract_auth_methods(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Extract authentication tokens from headers."""
        methods = {}
        
        # OAuth Bearer token
        auth_header = headers.get("authorization", headers.get("Authorization", ""))
        if auth_header.startswith("Bearer "):
            methods["oauth"] = auth_header[7:].strip()
            
        # Personal Access Token
        pat_token = headers.get("X-PAT-Token", headers.get("x-pat-token"))
        if pat_token:
            methods["pat"] = pat_token.strip()
            
        # API Key
        api_key = headers.get("X-Skyfi-Api-Key", headers.get("x-skyfi-api-key"))
        if api_key:
            methods["api_key"] = api_key.strip()
            
        # JWT Session Token
        jwt_token = (headers.get("X-Session-Token") or 
                    headers.get("x-session-token") or
                    auth_header.replace("Bearer ", "") if "Bearer " in auth_header else None)
        if jwt_token and jwt_token != methods.get("oauth"):
            methods["jwt"] = jwt_token.strip()
            
        # Service Account Key
        service_key = headers.get("X-Service-Account-Key", headers.get("x-service-account-key"))
        if service_key:
            methods["service_account"] = service_key.strip()
            
        return methods
        
    async def _validate_method(self, method: str, token: str) -> AuthResult:
        """Validate a specific authentication method."""
        if method == "oauth":
            return await self.oauth_mock.validate(token)
        elif method == "pat":
            return await self.pat_mock.validate(token)
        elif method == "api_key":
            return await self.api_key_mock.validate(token)
        elif method == "jwt":
            return await self.jwt_mock.validate(token)
        elif method == "service_account":
            return await self.service_account_mock.validate(token)
        else:
            return AuthResult(valid=False, method=method, error_message=f"Unknown auth method: {method}")


class OAuth2Mock:
    """OAuth 2.0 authentication mock."""
    
    def __init__(self):
        self.valid_tokens = {
            "test_oauth_token_valid": {
                "user_id": "oauth-user-123",
                "organization_id": "oauth-org-456", 
                "scopes": ["read:archives", "write:orders", "read:account"],
                "expires_at": time.time() + 3600
            },
            "test_oauth_token_expired": {
                "user_id": "oauth-user-456",
                "organization_id": "oauth-org-789",
                "scopes": ["read:archives"],
                "expires_at": time.time() - 3600  # Expired
            }
        }
        
    async def setup(self):
        """Setup OAuth mock."""
        pass
        
    async def teardown(self):
        """Teardown OAuth mock."""
        pass
        
    async def validate(self, token: str) -> AuthResult:
        """Validate OAuth token."""
        if not token:
            return AuthResult(valid=False, method="oauth", error_message="Empty OAuth token")
            
        token_data = self.valid_tokens.get(token)
        if not token_data:
            return AuthResult(valid=False, method="oauth", error_message="Invalid OAuth token")
            
        if token_data["expires_at"] <= time.time():
            return AuthResult(valid=False, method="oauth", error_message="OAuth token expired")
            
        return AuthResult(
            valid=True,
            method="oauth",
            user_id=token_data["user_id"],
            organization_id=token_data["organization_id"],
            scopes=token_data["scopes"]
        )


class PersonalAccessTokenMock:
    """Personal Access Token (PAT) authentication mock."""
    
    def __init__(self):
        self.valid_tokens = {
            "skyfi_pat_test_token_valid": {
                "user_id": "pat-user-789",
                "organization_id": "pat-org-012",
                "scopes": ["read:archives", "write:orders"],
                "expires_at": time.time() + (365 * 24 * 3600),  # 1 year
                "last_used_at": None
            },
            "skyfi_pat_test_token_expired": {
                "user_id": "pat-user-abc",
                "organization_id": "pat-org-def",
                "scopes": ["read:archives"],
                "expires_at": time.time() - 86400,  # Expired yesterday
                "last_used_at": time.time() - 172800  # Used 2 days ago
            }
        }
        
    async def setup(self):
        """Setup PAT mock."""
        pass
        
    async def teardown(self):
        """Teardown PAT mock."""
        pass
        
    async def validate(self, token: str) -> AuthResult:
        """Validate Personal Access Token."""
        if not token:
            return AuthResult(valid=False, method="pat", error_message="Empty PAT token")
            
        if not token.startswith("skyfi_pat_"):
            return AuthResult(valid=False, method="pat", error_message="Invalid PAT token format")
            
        token_data = self.valid_tokens.get(token)
        if not token_data:
            return AuthResult(valid=False, method="pat", error_message="PAT token not found")
            
        if token_data["expires_at"] <= time.time():
            return AuthResult(valid=False, method="pat", error_message="PAT token expired")
            
        # Update last used time (simulate database update)
        token_data["last_used_at"] = time.time()
        
        return AuthResult(
            valid=True,
            method="pat",
            user_id=token_data["user_id"],
            organization_id=token_data["organization_id"],
            scopes=token_data["scopes"]
        )


class APIKeyMock:
    """API Key authentication mock (enhanced legacy system)."""
    
    def __init__(self):
        self.valid_keys = {
            "test_skyfi_key_valid_123": {
                "user_id": "api-user-def",
                "organization_id": "api-org-ghi",
                "scopes": ["read:archives", "write:orders"],
                "expires_at": None,  # No expiration
                "rate_limit": {"rpm": 100, "rph": 1000, "rpd": 10000},
                "ip_whitelist": None,
                "last_used_at": None
            },
            "sk_enhanced_api_key_456": {
                "user_id": "api-user-jkl",
                "organization_id": "api-org-mno",
                "scopes": ["read:archives"],
                "expires_at": time.time() + (30 * 24 * 3600),  # 30 days
                "rate_limit": {"rpm": 50, "rph": 500, "rpd": 5000},
                "ip_whitelist": ["192.168.1.0/24", "10.0.0.0/8"],
                "last_used_at": time.time() - 3600
            },
            "test_skyfi_key_expired": {
                "user_id": "api-user-xyz",
                "organization_id": "api-org-xyz",
                "scopes": ["read:archives"],
                "expires_at": time.time() - 86400,  # Expired
                "rate_limit": {"rpm": 100, "rph": 1000, "rpd": 10000},
                "ip_whitelist": None,
                "last_used_at": time.time() - 172800
            }
        }
        
    async def setup(self):
        """Setup API Key mock."""
        pass
        
    async def teardown(self):
        """Teardown API Key mock."""
        pass
        
    async def validate(self, token: str) -> AuthResult:
        """Validate API Key."""
        if not token:
            return AuthResult(valid=False, method="api_key", error_message="Empty API key")
            
        key_data = self.valid_keys.get(token)
        if not key_data:
            return AuthResult(valid=False, method="api_key", error_message="Invalid API key")
            
        # Check expiration
        if key_data["expires_at"] and key_data["expires_at"] <= time.time():
            return AuthResult(valid=False, method="api_key", error_message="API key expired")
            
        # Update last used time
        key_data["last_used_at"] = time.time()
        
        return AuthResult(
            valid=True,
            method="api_key",
            user_id=key_data["user_id"],
            organization_id=key_data["organization_id"],
            scopes=key_data["scopes"]
        )


class JWTSessionMock:
    """JWT Session Token authentication mock."""
    
    def __init__(self):
        self.secret_key = "test_jwt_secret_key_for_testing_only"
        self.algorithm = "HS256"
        
    async def setup(self):
        """Setup JWT mock."""
        pass
        
    async def teardown(self):
        """Teardown JWT mock."""
        pass
        
    def create_test_token(self, user_id: str, scopes: List[str], expires_in_seconds: int = 3600) -> str:
        """Create a test JWT token."""
        payload = {
            "iss": "skyfi-mcp-test",
            "sub": user_id,
            "aud": "skyfi-api",
            "exp": time.time() + expires_in_seconds,
            "iat": time.time(),
            "jti": str(uuid.uuid4()),
            "user": {
                "id": user_id,
                "email": f"{user_id}@test.com",
                "organizationId": f"org-{user_id}"
            },
            "scopes": scopes,
            "session": {
                "id": str(uuid.uuid4()),
                "ip": "192.168.1.100"
            }
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
    async def validate(self, token: str) -> AuthResult:
        """Validate JWT Session Token."""
        if not token:
            return AuthResult(valid=False, method="jwt", error_message="Empty JWT token")
            
        try:
            # Handle pre-created test tokens
            if token == "test_jwt_token_valid":
                return AuthResult(
                    valid=True,
                    method="jwt",
                    user_id="jwt-user-123",
                    organization_id="jwt-org-456",
                    scopes=["read:archives", "write:orders"]
                )
            elif token == "test_jwt_token_expired":
                return AuthResult(valid=False, method="jwt", error_message="JWT token expired")
            elif token == "test_jwt_token_invalid":
                return AuthResult(valid=False, method="jwt", error_message="Invalid JWT token")
                
            # Try to decode actual JWT tokens
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Validate required claims
            required_claims = ["iss", "sub", "aud", "exp", "iat"]
            for claim in required_claims:
                if claim not in payload:
                    return AuthResult(
                        valid=False, 
                        method="jwt", 
                        error_message=f"Missing required claim: {claim}"
                    )
                    
            # Extract user information
            user_info = payload.get("user", {})
            
            return AuthResult(
                valid=True,
                method="jwt",
                user_id=payload["sub"],
                organization_id=user_info.get("organizationId"),
                scopes=payload.get("scopes", [])
            )
            
        except jwt.ExpiredSignatureError:
            return AuthResult(valid=False, method="jwt", error_message="JWT token expired")
        except jwt.InvalidTokenError as e:
            return AuthResult(valid=False, method="jwt", error_message=f"Invalid JWT token: {str(e)}")
        except Exception as e:
            return AuthResult(valid=False, method="jwt", error_message=f"JWT validation error: {str(e)}")


class ServiceAccountMock:
    """Service Account Key authentication mock."""
    
    def __init__(self):
        self.valid_keys = {
            "skyfi_sa_test_key_valid": {
                "service_name": "test-service",
                "permissions": ["read:archives", "system:monitoring"],
                "allowed_origins": ["192.168.1.0/24"],
                "expires_at": None,  # No expiration for service accounts
                "rate_limit": {"rps": 50, "burst": 100}
            },
            "skyfi_sa_analytics_key": {
                "service_name": "analytics-service",
                "permissions": ["read:archives", "read:orders", "read:account"],
                "allowed_origins": ["10.0.0.0/8"],
                "expires_at": time.time() + (90 * 24 * 3600),  # 90 days
                "rate_limit": {"rps": 100, "burst": 200}
            }
        }
        
    async def setup(self):
        """Setup Service Account mock."""
        pass
        
    async def teardown(self):
        """Teardown Service Account mock."""
        pass
        
    async def validate(self, token: str) -> AuthResult:
        """Validate Service Account Key."""
        if not token:
            return AuthResult(valid=False, method="service_account", error_message="Empty service account key")
            
        if not token.startswith("skyfi_sa_"):
            return AuthResult(
                valid=False, 
                method="service_account", 
                error_message="Invalid service account key format"
            )
            
        key_data = self.valid_keys.get(token)
        if not key_data:
            return AuthResult(
                valid=False, 
                method="service_account", 
                error_message="Service account key not found"
            )
            
        # Check expiration
        if key_data["expires_at"] and key_data["expires_at"] <= time.time():
            return AuthResult(
                valid=False, 
                method="service_account", 
                error_message="Service account key expired"
            )
            
        return AuthResult(
            valid=True,
            method="service_account",
            user_id=f"service-{key_data['service_name']}",
            organization_id=None,  # Service accounts don't belong to organizations
            scopes=key_data["permissions"]
        )


class RateLimitMock:
    """Rate limiting mock for testing rate limit scenarios."""
    
    def __init__(self):
        self.request_counts = {}
        
    def reset(self):
        """Reset all rate limit counters."""
        self.request_counts = {}
        
    def record_request(self, client_id: str, window: str = "minute"):
        """Record a request for rate limiting."""
        if client_id not in self.request_counts:
            self.request_counts[client_id] = {}
            
        if window not in self.request_counts[client_id]:
            self.request_counts[client_id][window] = {
                "count": 0,
                "reset_time": time.time() + (60 if window == "minute" else 3600 if window == "hour" else 86400)
            }
            
        # Reset counter if window expired
        current_time = time.time()
        window_data = self.request_counts[client_id][window]
        if current_time >= window_data["reset_time"]:
            window_data["count"] = 0
            window_data["reset_time"] = current_time + (60 if window == "minute" else 3600 if window == "hour" else 86400)
            
        window_data["count"] += 1
        
    def is_rate_limited(self, client_id: str, limit: int = 100, window: str = "minute") -> bool:
        """Check if client is rate limited."""
        if client_id not in self.request_counts:
            return False
            
        window_data = self.request_counts[client_id].get(window)
        if not window_data:
            return False
            
        return window_data["count"] >= limit
        
    def get_remaining_requests(self, client_id: str, limit: int = 100, window: str = "minute") -> int:
        """Get remaining requests for client."""
        if client_id not in self.request_counts:
            return limit
            
        window_data = self.request_counts[client_id].get(window)
        if not window_data:
            return limit
            
        return max(0, limit - window_data["count"])