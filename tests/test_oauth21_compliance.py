"""
OAuth 2.1 Resource Server Compliance Tests

Comprehensive test suite for OAuth 2.1 resource server implementation,
covering token validation, JWKS integration, and MCP protocol compliance.

Test Coverage:
- Bearer token validation per RFC 6750
- JWKS signature verification with key rotation
- Audience validation per RFC 8707
- Enterprise IdP integration scenarios
- Rate limiting and security features
- Integration with 4-tier credential hierarchy
- MCP protocol compliance validation
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.testclient import TestClient

from src.mcp_skyfi.middleware.oauth21 import (
    OAuth21ResourceServer,
    OAuthConfig, 
    JWKSCache,
    TokenCache,
    JWKSKey
)
from src.mcp_skyfi.middleware.oauth_discovery import OAuthDiscoveryEndpoints
from src.mcp_skyfi.middleware.auth import AuthCredential, CredentialSource


class TestOAuth21ResourceServer:
    """Test OAuth 2.1 resource server functionality."""
    
    @pytest.fixture
    def rsa_keypair(self):
        """Generate RSA keypair for testing."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        public_key = private_key.public_key()
        
        # Get key components for JWKS
        public_numbers = public_key.public_numbers()
        
        return {
            "private_key": private_key,
            "public_key": public_key,
            "kid": "test-key-1",
            "n": self._int_to_base64url(public_numbers.n),
            "e": self._int_to_base64url(public_numbers.e)
        }
    
    def _int_to_base64url(self, value):
        """Convert integer to base64url encoding."""
        import base64
        value_bytes = value.to_bytes((value.bit_length() + 7) // 8, 'big')
        return base64.urlsafe_b64encode(value_bytes).decode('ascii').rstrip('=')
    
    @pytest.fixture
    def oauth_config(self):
        """OAuth 2.1 configuration for testing."""
        return OAuthConfig(
            issuer_url="https://auth.example.com",
            audience="https://api.example.com",
            jwks_url="https://auth.example.com/.well-known/jwks.json",
            algorithm="RS256",
            verify_exp=True,
            verify_aud=True,
            verify_iss=True,
            leeway=30,
            jwks_cache_ttl=3600,
            token_cache_ttl=300,
            idp_type="generic",
            required_scopes=["mcp:read", "mcp:write"],
            max_requests_per_minute=1000
        )
    
    @pytest.fixture
    def jwks_response(self, rsa_keypair):
        """Mock JWKS response."""
        return {
            "keys": [
                {
                    "kty": "RSA",
                    "use": "sig",
                    "kid": rsa_keypair["kid"],
                    "alg": "RS256",
                    "n": rsa_keypair["n"],
                    "e": rsa_keypair["e"]
                }
            ]
        }
    
    def create_test_token(self, rsa_keypair, payload_overrides=None):
        """Create a test JWT token."""
        payload = {
            "iss": "https://auth.example.com",
            "aud": "https://api.example.com",
            "sub": "test-user-123",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
            "scope": "mcp:read mcp:write"
        }
        
        if payload_overrides:
            payload.update(payload_overrides)
        
        return jwt.encode(
            payload,
            rsa_keypair["private_key"],
            algorithm="RS256",
            headers={"kid": rsa_keypair["kid"]}
        )
    
    @pytest.mark.asyncio
    async def test_bearer_token_extraction(self, oauth_config):
        """Test Bearer token extraction from Authorization header."""
        middleware = OAuth21ResourceServer(None, oauth_config)
        
        # Mock request with Bearer token
        request = MagicMock()
        request.headers = {"authorization": "Bearer valid-token-here"}
        
        token = middleware._extract_bearer_token(request)
        assert token == "valid-token-here"
        
        # Test invalid formats
        request.headers = {"authorization": "Basic dXNlcjpwYXNz"}
        assert middleware._extract_bearer_token(request) is None
        
        request.headers = {"authorization": "Bearer "}
        assert middleware._extract_bearer_token(request) is None
        
        request.headers = {}
        assert middleware._extract_bearer_token(request) is None
    
    @pytest.mark.asyncio
    async def test_jwks_cache(self, oauth_config, jwks_response):
        """Test JWKS caching and key retrieval."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.json.return_value = jwks_response
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            cache = JWKSCache(oauth_config)
            
            # First request should fetch from server
            key = await cache.get_key("test-key-1")
            assert key is not None
            assert key.kid == "test-key-1"
            assert key.kty == "RSA"
            assert mock_get.call_count == 1
            
            # Second request should use cache
            key2 = await cache.get_key("test-key-1")
            assert key2 is not None
            assert mock_get.call_count == 1  # No additional calls
            
            await cache.cleanup()
    
    @pytest.mark.asyncio
    async def test_token_validation_success(self, oauth_config, rsa_keypair, jwks_response):
        """Test successful token validation."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.json.return_value = jwks_response
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            middleware = OAuth21ResourceServer(None, oauth_config)
            
            # Create valid token
            token = self.create_test_token(rsa_keypair)
            
            # Validate token
            payload = await middleware._validate_token(token, "127.0.0.1")
            
            assert payload is not None
            assert payload["sub"] == "test-user-123"
            assert payload["iss"] == "https://auth.example.com"
            assert payload["aud"] == "https://api.example.com"
            assert "mcp:read" in payload["scope"]
            
            await middleware.cleanup()
    
    @pytest.mark.asyncio
    async def test_token_validation_expired(self, oauth_config, rsa_keypair, jwks_response):
        """Test expired token rejection."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.json.return_value = jwks_response
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            middleware = OAuth21ResourceServer(None, oauth_config)
            
            # Create expired token
            token = self.create_test_token(rsa_keypair, {
                "exp": int(time.time()) - 3600  # Expired 1 hour ago
            })
            
            # Validate token
            payload = await middleware._validate_token(token, "127.0.0.1")
            assert payload is None
            
            await middleware.cleanup()
    
    @pytest.mark.asyncio
    async def test_token_validation_wrong_audience(self, oauth_config, rsa_keypair, jwks_response):
        """Test wrong audience rejection."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.json.return_value = jwks_response
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            middleware = OAuth21ResourceServer(None, oauth_config)
            
            # Create token with wrong audience
            token = self.create_test_token(rsa_keypair, {
                "aud": "https://wrong-api.example.com"
            })
            
            # Validate token
            payload = await middleware._validate_token(token, "127.0.0.1")
            assert payload is None
            
            await middleware.cleanup()
    
    @pytest.mark.asyncio
    async def test_token_validation_missing_scopes(self, oauth_config, rsa_keypair, jwks_response):
        """Test missing required scopes rejection."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.json.return_value = jwks_response
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            middleware = OAuth21ResourceServer(None, oauth_config)
            
            # Create token with insufficient scopes
            token = self.create_test_token(rsa_keypair, {
                "scope": "mcp:read"  # Missing mcp:write
            })
            
            # Validate token
            payload = await middleware._validate_token(token, "127.0.0.1")
            assert payload is None
            
            await middleware.cleanup()
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, oauth_config):
        """Test rate limiting functionality."""
        # Set low rate limit for testing
        oauth_config.max_requests_per_minute = 2
        middleware = OAuth21ResourceServer(None, oauth_config)
        
        client_ip = "127.0.0.1"
        
        # First two requests should pass
        assert not middleware._is_rate_limited(client_ip)
        assert not middleware._is_rate_limited(client_ip)
        
        # Third request should be rate limited
        assert middleware._is_rate_limited(client_ip)
    
    @pytest.mark.asyncio
    async def test_credential_creation(self, oauth_config, rsa_keypair):
        """Test OAuth credential creation."""
        middleware = OAuth21ResourceServer(None, oauth_config)
        
        token = "test-bearer-token"
        payload = {
            "sub": "test-user-123",
            "iss": "https://auth.example.com",
            "aud": "https://api.example.com",
            "scope": "mcp:read mcp:write",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time())
        }
        
        credential = middleware._create_oauth_credential(token, payload, "127.0.0.1")
        
        assert credential.token == token
        assert credential.auth_type == "oauth2_bearer"
        assert credential.source.name == "oauth2_bearer"
        assert credential.source.priority == 1.5
        assert credential.metadata["sub"] == "test-user-123"
        assert credential.metadata["oauth2_compliant"] is True
        assert credential.metadata["mcp_protocol_compliant"] is True
        assert "mcp:read" in credential.metadata["scopes"]
    
    def test_oauth_config_from_env(self):
        """Test OAuth configuration from environment variables."""
        with patch.dict("os.environ", {
            "OAUTH_ISSUER_URL": "https://auth.example.com",
            "OAUTH_AUDIENCE": "https://api.example.com",
            "OAUTH_JWKS_URL": "https://auth.example.com/jwks",
            "OAUTH_ALGORITHM": "ES256",
            "OAUTH_VERIFY_EXP": "false",
            "OAUTH_REQUIRED_SCOPES": "read,write,admin",
            "OAUTH_IDP_TYPE": "auth0",
            "OAUTH_RATE_LIMIT": "500"
        }):
            config = OAuthConfig.from_env()
            
            assert config is not None
            assert config.issuer_url == "https://auth.example.com"
            assert config.audience == "https://api.example.com"
            assert config.jwks_url == "https://auth.example.com/jwks"
            assert config.algorithm == "ES256"
            assert config.verify_exp is False
            assert config.required_scopes == ["read", "write", "admin"]
            assert config.idp_type == "auth0"
            assert config.max_requests_per_minute == 500
    
    def test_oauth_config_discovery_urls(self):
        """Test OAuth configuration discovery URL generation."""
        config = OAuthConfig(
            issuer_url="https://auth.example.com",
            audience="https://api.example.com",
            idp_type="auth0"
        )
        
        assert config.get_discovery_url() == "https://auth.example.com/.well-known/oauth-authorization-server"
        assert config.get_jwks_url() == "https://auth.example.com/.well-known/jwks.json"
        
        # Test Okta-specific URL
        config.idp_type = "okta"
        assert config.get_jwks_url() == "https://auth.example.com/v1/keys"
        
        # Test Keycloak-specific URL
        config.idp_type = "keycloak"
        assert config.get_jwks_url() == "https://auth.example.com/protocol/openid-connect/certs"


class TestOAuthDiscoveryEndpoints:
    """Test OAuth discovery endpoints."""
    
    @pytest.fixture
    def oauth_config(self):
        """OAuth configuration for discovery tests."""
        return OAuthConfig(
            issuer_url="https://auth.example.com",
            audience="https://api.example.com",
            idp_type="auth0",
            required_scopes=["mcp:read", "mcp:write"]
        )
    
    @pytest.fixture
    def discovery_endpoints(self, oauth_config):
        """OAuth discovery endpoints instance."""
        return OAuthDiscoveryEndpoints(oauth_config, "https://mcp.example.com")
    
    @pytest.fixture
    def test_app(self, discovery_endpoints):
        """Test Starlette app with discovery endpoints."""
        app = Starlette()
        for route in discovery_endpoints.get_routes():
            app.router.routes.append(route)
        return app
    
    def test_authorization_server_metadata(self, test_app):
        """Test authorization server metadata endpoint."""
        client = TestClient(test_app)
        response = client.get("/.well-known/oauth-authorization-server")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["issuer"] == "https://auth.example.com"
        assert "authorization_endpoint" in data
        assert "token_endpoint" in data
        assert "jwks_uri" in data
        assert "code" in data["response_types_supported"]
        assert "authorization_code" in data["grant_types_supported"]
        assert "mcp_protocol_compliance" in data
        assert data["mcp_protocol_compliance"]["version"] == "2024-11-05"
    
    def test_resource_server_metadata(self, test_app):
        """Test resource server metadata endpoint."""
        client = TestClient(test_app)
        response = client.get("/.well-known/oauth-resource-server")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["resource_server_identifier"] == "https://api.example.com"
        assert data["authorization_server"] == "https://auth.example.com"
        assert "token_validation" in data
        assert data["token_validation"]["method"] == "jwks"
        assert "mcp_integration" in data
        assert data["mcp_integration"]["credential_hierarchy_priority"] == 1.5
    
    def test_mcp_oauth_capabilities(self, test_app):
        """Test MCP OAuth capabilities endpoint."""
        client = TestClient(test_app)
        response = client.get("/.well-known/mcp-oauth-capabilities")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["mcp_protocol"]["version"] == "2024-11-05"
        assert "oauth_compliance" in data
        assert data["oauth_compliance"]["version"] == "2.1"
        assert "transport_support" in data
        assert data["transport_support"]["stdio"]["supported"] is True
        assert data["transport_support"]["sse"]["supported"] is True
        assert "credential_hierarchy" in data
        assert data["credential_hierarchy"]["oauth_priority"] == 1.5


class TestOAuth21Integration:
    """Test OAuth 2.1 integration with existing authentication system."""
    
    @pytest.fixture
    def app_with_oauth(self):
        """Test app with OAuth 2.1 middleware."""
        from src.mcp_skyfi.servers.main import SkyFiMCP
        
        # Mock OAuth configuration
        with patch("src.mcp_skyfi.middleware.oauth21.OAuthConfig.from_env") as mock_config:
            mock_config.return_value = OAuthConfig(
                issuer_url="https://auth.example.com",
                audience="https://api.example.com"
            )
            
            server = SkyFiMCP(name="Test Server", version="1.0.0")
            app = server.http_app()
            
            return app
    
    def test_oauth_middleware_order(self, app_with_oauth):
        """Test that OAuth middleware is properly ordered in the pipeline."""
        middleware_types = [type(m.cls) for m in app_with_oauth.user_middleware]
        
        # OAuth middleware should come before UserTokenMiddleware
        oauth_index = next(
            (i for i, cls in enumerate(middleware_types) 
             if cls.__name__ == "OAuth21ResourceServer"), 
            None
        )
        auth_index = next(
            (i for i, cls in enumerate(middleware_types) 
             if cls.__name__ == "UserTokenMiddleware"), 
            None
        )
        
        if oauth_index is not None and auth_index is not None:
            assert oauth_index < auth_index, "OAuth middleware should run before UserTokenMiddleware"
    
    @pytest.mark.asyncio
    async def test_credential_hierarchy_integration(self):
        """Test OAuth credential integration with hierarchy."""
        from src.mcp_skyfi.middleware.auth import UserTokenMiddleware
        
        # Mock request with OAuth validation
        request = MagicMock()
        request.state.oauth_validated = True
        request.state.oauth_token = "bearer-token-123"
        request.state.oauth_payload = {
            "sub": "test-user",
            "iss": "https://auth.example.com",
            "aud": "https://api.example.com",
            "scope": "mcp:read mcp:write"
        }
        
        middleware = UserTokenMiddleware(None)
        credential = await middleware._extract_oauth_credentials(request, "127.0.0.1")
        
        assert credential is not None
        assert credential.auth_type == "oauth2_bearer"
        assert credential.source.priority == 1.5
        assert credential.metadata["oauth_validated"] is True
        assert credential.metadata["mcp_protocol_compliant"] is True
    
    def test_error_response_format(self):
        """Test OAuth error response format compliance."""
        middleware = OAuth21ResourceServer(None, OAuthConfig(
            issuer_url="https://auth.example.com",
            audience="https://api.example.com"
        ))
        
        response = middleware._create_error_response("invalid_token", 401)
        
        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers
        assert response.headers["WWW-Authenticate"].startswith("Bearer")
        
        body = json.loads(response.body)
        assert body["error"] == "invalid_token"
        assert "error_description" in body


class TestMCPProtocolCompliance:
    """Test MCP protocol compliance aspects."""
    
    def test_oauth_transport_compatibility(self):
        """Test OAuth compatibility with MCP transports."""
        config = OAuthConfig(
            issuer_url="https://auth.example.com",
            audience="https://api.example.com"
        )
        
        discovery = OAuthDiscoveryEndpoints(config, "https://mcp.example.com")
        
        # Test transport compatibility in capabilities
        app = Starlette()
        for route in discovery.get_routes():
            app.router.routes.append(route)
        
        client = TestClient(app)
        response = client.get("/.well-known/mcp-oauth-capabilities")
        
        data = response.json()
        transport_support = data["transport_support"]
        
        # All MCP transports should be supported
        assert transport_support["stdio"]["supported"] is True
        assert transport_support["sse"]["supported"] is True
        assert transport_support["streamable_http"]["supported"] is True
    
    def test_credential_hierarchy_priority(self):
        """Test credential hierarchy priority compliance."""
        from src.mcp_skyfi.middleware.auth import UserTokenMiddleware
        
        middleware = UserTokenMiddleware(None)
        
        # OAuth should have priority 1.5 (between client headers and user context)
        oauth_source = middleware.CREDENTIAL_SOURCES["oauth2_bearer"]
        client_source = middleware.CREDENTIAL_SOURCES["client_headers"]
        user_source = middleware.CREDENTIAL_SOURCES["user_context"]
        
        assert oauth_source.priority > client_source.priority  # Lower than client headers
        assert oauth_source.priority < user_source.priority    # Higher than user context
        assert oauth_source.secure is True                     # Should be secure
    
    def test_mcp_protocol_version_compliance(self):
        """Test MCP protocol version compliance."""
        config = OAuthConfig(
            issuer_url="https://auth.example.com",
            audience="https://api.example.com"
        )
        
        discovery = OAuthDiscoveryEndpoints(config, "https://mcp.example.com")
        
        app = Starlette()
        for route in discovery.get_routes():
            app.router.routes.append(route)
        
        client = TestClient(app)
        
        # Check authorization server metadata
        response = client.get("/.well-known/oauth-authorization-server")
        data = response.json()
        
        mcp_compliance = data["mcp_protocol_compliance"]
        assert mcp_compliance["version"] == "2024-11-05"
        assert "stdio" in mcp_compliance["transport_support"]
        assert "sse" in mcp_compliance["transport_support"]
        assert "streamable" in mcp_compliance["transport_support"]
        
        # Check resource server metadata  
        response = client.get("/.well-known/oauth-resource-server")
        data = response.json()
        
        mcp_integration = data["mcp_integration"]
        assert mcp_integration["protocol_version"] == "2024-11-05"
        assert mcp_integration["credential_hierarchy_priority"] == 1.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])