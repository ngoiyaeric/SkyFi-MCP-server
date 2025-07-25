"""
OAuth 2.1 Discovery Endpoints

Implements OAuth 2.1 discovery endpoints for client compatibility and MCP protocol compliance.
Provides well-known endpoints as specified in RFC 8414 (OAuth 2.0 Authorization Server Metadata).

Key Features:
- OAuth Authorization Server Metadata endpoint
- JWKS endpoint for public key distribution
- Resource server capability advertisement
- Client configuration assistance
- MCP protocol compliance indicators
"""


import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from .oauth21 import OAuthConfig

logger = logging.getLogger("mcp-skyfi.middleware.oauth_discovery")


class OAuthDiscoveryEndpoints:
    """
    OAuth 2.1 Discovery Endpoints for MCP Protocol Compliance.
    
    Implements RFC 8414 OAuth 2.0 Authorization Server Metadata and related
    discovery endpoints to enable client configuration and compatibility.
    """
    
    def __init__(self, config: OAuthConfig, base_url: str):
        self.config = config
        self.base_url = base_url.rstrip('/')

    def get_routes(self) -> List[Route]:
        """Get discovery endpoint routes."""
        return [
            Route(
                "/.well-known/oauth-authorization-server",
                self.authorization_server_metadata,
                methods=["GET"]
            ),
            Route(
                "/.well-known/oauth-resource-server",
                self.resource_server_metadata,
                methods=["GET"]
            ),
            Route(
                "/.well-known/mcp-oauth-capabilities",
                self.mcp_oauth_capabilities,
                methods=["GET"]
            ),
            Route(
                "/oauth/jwks",
                self.jwks_endpoint,
                methods=["GET"]
            )
        ]

    async def authorization_server_metadata(self, request: Request) -> JSONResponse:
        """
        OAuth 2.0 Authorization Server Metadata endpoint per RFC 8414.
        
        Provides discovery information for OAuth clients including:
        - Supported grant types and response types
        - Token endpoint locations
        - Supported scopes and claims
        - Security capabilities
        """
        try:
            metadata = {
                "issuer": self.config.issuer_url,
                "authorization_endpoint": urljoin(self.config.issuer_url, "/oauth/authorize"),
                "token_endpoint": urljoin(self.config.issuer_url, "/oauth/token"),
                "jwks_uri": self.config.get_jwks_url(),
                "userinfo_endpoint": urljoin(self.config.issuer_url, "/oauth/userinfo"),
                "revocation_endpoint": urljoin(self.config.issuer_url, "/oauth/revoke"),
                "introspection_endpoint": urljoin(self.config.issuer_url, "/oauth/introspect"),
                
                # OAuth 2.1 compliance
                "response_types_supported": [
                    "code"
                ],
                "grant_types_supported": [
                    "authorization_code",
                    "client_credentials",
                    "refresh_token"
                ],
                "token_endpoint_auth_methods_supported": [
                    "client_secret_basic",
                    "client_secret_post",
                    "private_key_jwt",
                    "client_secret_jwt"
                ],
                "scopes_supported": self._get_supported_scopes(),
                "claims_supported": self._get_supported_claims(),
                
                # Cryptographic capabilities
                "id_token_signing_alg_values_supported": ["RS256", "ES256"],
                "userinfo_signing_alg_values_supported": ["RS256", "ES256"],
                "request_object_signing_alg_values_supported": ["RS256", "ES256"],
                "token_endpoint_auth_signing_alg_values_supported": ["RS256", "ES256"],
                
                # Security features
                "code_challenge_methods_supported": ["S256"],
                "tls_client_certificate_bound_access_tokens": True,
                "dpop_signing_alg_values_supported": ["RS256", "ES256"],
                
                # Resource server integration
                "resource_server": {
                    "audience": self.config.audience,
                    "introspection_required": False,
                    "bearer_token_supported": True,
                    "token_validation_method": "jwks"
                },
                
                # MCP protocol compliance
                "mcp_protocol_compliance": {
                    "version": "2024-11-05",
                    "transport_support": ["stdio", "sse", "streamable"],
                    "authentication_methods": ["oauth2_bearer", "api_key", "basic"],
                    "resource_server_rfc": "RFC6750",
                    "oauth_version": "2.1"
                }
            }
            
            # Add IdP-specific extensions
            if self.config.idp_type != "generic":
                metadata.update(self._get_idp_extensions())
            
            return JSONResponse(
                metadata,
                headers={
                    "Cache-Control": "public, max-age=3600",
                    "Content-Type": "application/json"
                }
            )
            
        except Exception as e:
            logger.error(f"Error generating authorization server metadata: {e}", exc_info=True)
            return JSONResponse(
                {"error": "server_error", "error_description": "Unable to generate metadata"},
                status_code=500
            )

    async def resource_server_metadata(self, request: Request) -> JSONResponse:
        """
        Resource Server Metadata endpoint for MCP protocol compliance.
        
        Provides specific information about resource server capabilities,
        token validation requirements, and MCP protocol integration.
        """
        try:
            metadata = {
                "resource_server_identifier": self.config.audience,
                "authorization_server": self.config.issuer_url,
                "jwks_uri": self.config.get_jwks_url(),
                
                # Token validation configuration
                "token_validation": {
                    "method": "jwks",
                    "algorithm": self.config.algorithm,
                    "audience_validation": self.config.verify_aud,
                    "issuer_validation": self.config.verify_iss,
                    "expiration_validation": self.config.verify_exp,
                    "clock_skew_tolerance": self.config.leeway
                },
                
                # Security features
                "security_features": {
                    "bearer_token_support": True,
                    "rate_limiting": True,
                    "max_requests_per_minute": self.config.max_requests_per_minute,
                    "token_caching": True,
                    "jwks_caching": True,
                    "secure_token_logging": True
                },
                
                # Required scopes and claims
                "access_control": {
                    "required_scopes": self.config.required_scopes or [],
                    "custom_claims": list(self.config.custom_claims.keys()) if self.config.custom_claims else [],
                    "scope_validation": bool(self.config.required_scopes),
                    "claim_validation": bool(self.config.custom_claims)
                },
                
                # MCP protocol integration
                "mcp_integration": {
                    "protocol_version": "2024-11-05",
                    "credential_hierarchy_priority": 1.5,
                    "fallback_auth_methods": ["api_key", "basic", "env_fallback"],
                    "transport_compatibility": ["stdio", "sse", "streamable-http"],
                    "tool_filtering_support": True,
                    "context_propagation": True
                },
                
                # Enterprise features
                "enterprise_support": {
                    "multi_tenant": True,
                    "custom_claims": True,
                    "audit_logging": True,
                    "performance_monitoring": True,
                    "idp_integration": {
                        "type": self.config.idp_type,
                        "supported_idps": ["auth0", "okta", "keycloak", "azure", "generic"]
                    }
                }
            }
            
            return JSONResponse(
                metadata,
                headers={
                    "Cache-Control": "public, max-age=3600",
                    "Content-Type": "application/json"
                }
            )
            
        except Exception as e:
            logger.error(f"Error generating resource server metadata: {e}", exc_info=True)
            return JSONResponse(
                {"error": "server_error", "error_description": "Unable to generate metadata"},
                status_code=500
            )

    async def mcp_oauth_capabilities(self, request: Request) -> JSONResponse:
        """
        MCP-specific OAuth capabilities endpoint.
        
        Provides detailed information about MCP protocol OAuth integration,
        including supported features, configuration guidelines, and compatibility matrix.
        """
        try:
            capabilities = {
                "mcp_protocol": {
                    "version": "2024-11-05",
                    "specification_url": "https://spec.modelcontextprotocol.io/specification/",
                    "oauth_integration_version": "1.0.0"
                },
                
                # OAuth 2.1 compliance
                "oauth_compliance": {
                    "version": "2.1",
                    "rfc_references": [
                        "RFC 6749 - OAuth 2.0 Authorization Framework",
                        "RFC 6750 - Bearer Token Usage", 
                        "RFC 7636 - PKCE",
                        "RFC 8414 - Authorization Server Metadata",
                        "RFC 8707 - Resource Parameter"
                    ],
                    "security_best_practices": [
                        "PKCE required for public clients",
                        "Short-lived access tokens",
                        "Audience validation enforced",
                        "JWKS key rotation supported"
                    ]
                },
                
                # Transport compatibility
                "transport_support": {
                    "stdio": {
                        "supported": True,
                        "oauth_method": "bearer_token_injection",
                        "configuration": "environment_variables"
                    },
                    "sse": {
                        "supported": True,
                        "oauth_method": "authorization_header",
                        "websocket_compatible": True
                    },
                    "streamable_http": {
                        "supported": True,
                        "oauth_method": "authorization_header",
                        "rest_api_compatible": True
                    }
                },
                
                # Authentication hierarchy integration
                "credential_hierarchy": {
                    "oauth_priority": 1.5,
                    "integration_method": "middleware_chain",
                    "fallback_behavior": "graceful_degradation",
                    "hierarchy": [
                        {"priority": 1, "method": "client_headers", "secure": True},
                        {"priority": 1.5, "method": "oauth2_bearer", "secure": True},
                        {"priority": 2, "method": "user_context", "secure": True},
                        {"priority": 3, "method": "server_config", "secure": True},
                        {"priority": 4, "method": "env_fallback", "secure": False}
                    ]
                },
                
                # Client configuration guidance
                "client_configuration": {
                    "recommended_flow": "authorization_code_with_pkce",
                    "token_endpoint": urljoin(self.config.issuer_url, "/oauth/token"),
                    "authorization_endpoint": urljoin(self.config.issuer_url, "/oauth/authorize"),
                    "required_scopes": self.config.required_scopes or ["mcp:read", "mcp:write"],
                    "audience": self.config.audience,
                    "token_usage": {
                        "header": "Authorization: Bearer <token>",
                        "parameter": "Not recommended for security",
                        "context_injection": "Supported for stdio transport"
                    }
                },
                
                # Error handling
                "error_responses": {
                    "invalid_token": {
                        "status_code": 401,
                        "description": "Token is expired, revoked, malformed, or invalid"
                    },
                    "insufficient_scope": {
                        "status_code": 403,
                        "description": "Token lacks required scopes"
                    },
                    "rate_limit_exceeded": {
                        "status_code": 429,
                        "description": "Too many requests from client"
                    }
                },
                
                # Performance characteristics
                "performance": {
                    "token_validation_cache_ttl": self.config.token_cache_ttl,
                    "jwks_cache_ttl": self.config.jwks_cache_ttl,
                    "rate_limit_window": 60,
                    "max_requests_per_minute": self.config.max_requests_per_minute,
                    "average_validation_time_ms": "< 50ms (cached), < 200ms (uncached)"
                }
            }
            
            return JSONResponse(
                capabilities,
                headers={
                    "Cache-Control": "public, max-age=3600",
                    "Content-Type": "application/json"
                }
            )
            
        except Exception as e:
            logger.error(f"Error generating MCP OAuth capabilities: {e}", exc_info=True)
            return JSONResponse(
                {"error": "server_error", "error_description": "Unable to generate capabilities"},
                status_code=500
            )

    async def jwks_endpoint(self, request: Request) -> JSONResponse:
        """
        Local JWKS endpoint for development and testing.
        
        Note: In production, this would typically be served by the authorization server.
        This endpoint is provided for development convenience and testing scenarios.
        """
        try:
            # This is a placeholder - in production, JWKS would come from the authorization server
            jwks = {
                "keys": [
                    {
                        "kty": "RSA",
                        "use": "sig",
                        "kid": "development-key-1",
                        "alg": "RS256",
                        "n": "example-modulus",
                        "e": "AQAB"
                    }
                ],
                "note": "This is a development endpoint. In production, use the authorization server's JWKS endpoint.",
                "production_jwks_uri": self.config.get_jwks_url()
            }
            
            return JSONResponse(
                jwks,
                headers={
                    "Cache-Control": "public, max-age=300",  # Shorter cache for development
                    "Content-Type": "application/json"
                }
            )
            
        except Exception as e:
            logger.error(f"Error generating JWKS: {e}", exc_info=True)
            return JSONResponse(
                {"error": "server_error", "error_description": "Unable to generate JWKS"},
                status_code=500
            )

    def _get_supported_scopes(self) -> List[str]:
        """Get list of supported OAuth scopes."""
        base_scopes = ["openid", "profile", "email"]
        
        # Add MCP-specific scopes
        mcp_scopes = ["mcp:read", "mcp:write", "mcp:admin"]
        
        # Add service-specific scopes
        service_scopes = [
            "skyfi:read", "skyfi:write", "skyfi:order",
            "osm:read", "osm:geocode",
            "weather:read", "weather:forecast"
        ]
        
        # Add required scopes from configuration
        config_scopes = self.config.required_scopes or []
        
        all_scopes = base_scopes + mcp_scopes + service_scopes + config_scopes
        return sorted(list(set(all_scopes)))

    def _get_supported_claims(self) -> List[str]:
        """Get list of supported JWT claims."""
        standard_claims = [
            "iss", "sub", "aud", "exp", "iat", "auth_time",
            "nonce", "email", "email_verified", "name",
            "given_name", "family_name", "locale"
        ]
        
        mcp_claims = [
            "mcp_permissions", "mcp_tools", "mcp_transports",
            "resource_access", "client_permissions"
        ]
        
        # Add custom claims from configuration
        custom_claims = list(self.config.custom_claims.keys()) if self.config.custom_claims else []
        
        all_claims = standard_claims + mcp_claims + custom_claims
        return sorted(list(set(all_claims)))

    def _get_idp_extensions(self) -> Dict[str, Any]:
        """Get IdP-specific metadata extensions."""
        extensions = {}
        
        if self.config.idp_type == "auth0":
            extensions.update({
                "auth0_extensions": {
                    "management_api": True,
                    "custom_domains": True,
                    "rules_support": True,
                    "hooks_support": True
                }
            })
        elif self.config.idp_type == "okta":
            extensions.update({
                "okta_extensions": {
                    "org_authorization_server": True,  
                    "custom_authorization_server": True,
                    "api_access_management": True,
                    "universal_directory": True
                }
            })
        elif self.config.idp_type == "keycloak":
            extensions.update({
                "keycloak_extensions": {
                    "realm_management": True,
                    "client_scopes": True,
                    "user_federation": True,
                    "custom_protocols": True
                }
            })
        elif self.config.idp_type == "azure":
            extensions.update({
                "azure_extensions": {
                    "microsoft_graph": True,
                    "azure_ad_b2c": True,
                    "conditional_access": True,
                    "enterprise_applications": True
                }
            })
        
        return extensions