"""
OAuth 2.1 Resource Server Middleware

Enterprise-grade OAuth 2.1 resource server implementation for full MCP protocol compliance.
Supports JWKS-based token validation, audience verification, and enterprise IdP integration.

Key Features:
- Bearer token validation according to RFC 6750
- JWKS signature verification with key caching
- Audience validation per RFC 8707 Resource Parameter
- Support for Auth0, Okta, Keycloak, and custom IdPs
- Stateless operation with comprehensive security logging
- Integration with existing 4-tier credential hierarchy
"""


import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union
from urllib.parse import urljoin

import httpx
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError, InvalidSignatureError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from ..utils.logging import log_security_event
from .auth import AuthCredential, CredentialSource

logger = logging.getLogger("mcp-skyfi.middleware.oauth21")


@dataclass
class OAuthConfig:
    """Configuration for OAuth 2.1 resource server."""
    
    # Identity Provider Configuration
    issuer_url: str
    """OAuth 2.1 issuer URL (e.g., https://auth.example.com)"""
    
    audience: str
    """Expected audience claim (e.g., https://api.example.com)"""
    
    jwks_url: Optional[str] = None
    """JWKS endpoint URL (auto-discovered if None)"""
    
    # Validation Settings
    algorithm: str = "RS256"
    """Expected JWT signature algorithm"""
    
    verify_exp: bool = True
    """Verify token expiration"""
    
    verify_aud: bool = True
    """Verify audience claim"""
    
    verify_iss: bool = True
    """Verify issuer claim"""
    
    leeway: int = 30
    """Clock skew tolerance in seconds"""
    
    # Performance Settings
    jwks_cache_ttl: int = 3600
    """JWKS cache TTL in seconds (1 hour)"""
    
    token_cache_ttl: int = 300
    """Token validation cache TTL in seconds (5 minutes)"""
    
    # Enterprise IdP Support
    idp_type: str = "generic"
    """IdP type: generic, auth0, okta, keycloak, azure"""
    
    required_scopes: Optional[List[str]] = None
    """Required OAuth scopes"""
    
    custom_claims: Optional[Dict[str, Any]] = None
    """Custom claim validation rules"""

    # Rate Limiting
    max_requests_per_minute: int = 1000
    """Maximum requests per minute per client"""

    @classmethod
    def from_env(cls) -> Optional['OAuthConfig']:
        """Create OAuth configuration from environment variables."""
        import os
        
        issuer_url = os.getenv("OAUTH_ISSUER_URL")
        audience = os.getenv("OAUTH_AUDIENCE")
        
        if not issuer_url or not audience:
            return None
        
        return cls(
            issuer_url=issuer_url,
            audience=audience,
            jwks_url=os.getenv("OAUTH_JWKS_URL"),
            algorithm=os.getenv("OAUTH_ALGORITHM", "RS256"),
            verify_exp=os.getenv("OAUTH_VERIFY_EXP", "true").lower() == "true",
            verify_aud=os.getenv("OAUTH_VERIFY_AUD", "true").lower() == "true",
            verify_iss=os.getenv("OAUTH_VERIFY_ISS", "true").lower() == "true",
            leeway=int(os.getenv("OAUTH_LEEWAY", "30")),
            jwks_cache_ttl=int(os.getenv("OAUTH_JWKS_CACHE_TTL", "3600")),
            token_cache_ttl=int(os.getenv("OAUTH_TOKEN_CACHE_TTL", "300")),
            idp_type=os.getenv("OAUTH_IDP_TYPE", "generic"),
            required_scopes=os.getenv("OAUTH_REQUIRED_SCOPES", "").split(",") if os.getenv("OAUTH_REQUIRED_SCOPES") else None,
            max_requests_per_minute=int(os.getenv("OAUTH_RATE_LIMIT", "1000"))
        )

    def get_discovery_url(self) -> str:
        """Get OAuth discovery endpoint URL."""
        return urljoin(self.issuer_url, "/.well-known/oauth-authorization-server")

    def get_jwks_url(self) -> str:
        """Get JWKS endpoint URL (with auto-discovery support)."""
        if self.jwks_url:
            return self.jwks_url
        
        # Auto-discover JWKS URL
        if self.idp_type == "auth0":
            return urljoin(self.issuer_url, "/.well-known/jwks.json")
        elif self.idp_type == "okta":
            return urljoin(self.issuer_url, "/v1/keys")
        elif self.idp_type == "keycloak":
            return urljoin(self.issuer_url, "/protocol/openid-connect/certs")
        elif self.idp_type == "azure":
            return urljoin(self.issuer_url, "/discovery/v2.0/keys")
        else:
            # Generic discovery
            return urljoin(self.issuer_url, "/.well-known/jwks.json")


@dataclass
class JWKSKey:
    """Represents a JSON Web Key from JWKS."""
    kid: str
    kty: str
    use: str
    alg: str
    n: str
    e: str
    x5c: Optional[List[str]] = None
    x5t: Optional[str] = None

    @classmethod
    def from_jwks_dict(cls, key_dict: Dict[str, Any]) -> 'JWKSKey':
        """Create JWKSKey from JWKS response dictionary."""
        return cls(
            kid=key_dict["kid"],
            kty=key_dict["kty"],
            use=key_dict.get("use", "sig"),
            alg=key_dict.get("alg", "RS256"),
            n=key_dict["n"],
            e=key_dict["e"],
            x5c=key_dict.get("x5c"),
            x5t=key_dict.get("x5t")
        )


class JWKSCache:
    """Thread-safe JWKS cache with automatic refresh."""
    
    def __init__(self, config: OAuthConfig):
        self.config = config
        self._keys: Dict[str, JWKSKey] = {}
        self._last_fetch = 0
        self._fetch_lock = asyncio.Lock()
        self._http_client = httpx.AsyncClient(timeout=10.0)

    async def get_key(self, kid: str) -> Optional[JWKSKey]:
        """Get JWKS key by key ID with auto-refresh."""
        # Check if refresh is needed
        if time.time() - self._last_fetch > self.config.jwks_cache_ttl:
            await self._refresh_keys()
        
        return self._keys.get(kid)

    async def _refresh_keys(self) -> None:
        """Refresh JWKS keys from IdP."""
        async with self._fetch_lock:
            # Double-check pattern
            if time.time() - self._last_fetch < self.config.jwks_cache_ttl:
                return
            
            try:
                jwks_url = self.config.get_jwks_url()
                logger.debug(f"Fetching JWKS from {jwks_url}")
                
                response = await self._http_client.get(jwks_url)
                response.raise_for_status()
                
                jwks_data = response.json()
                new_keys = {}
                
                for key_data in jwks_data.get("keys", []):
                    if key_data.get("kty") == "RSA" and key_data.get("use") in ["sig", None]:
                        jwks_key = JWKSKey.from_jwks_dict(key_data)
                        new_keys[jwks_key.kid] = jwks_key
                
                self._keys = new_keys
                self._last_fetch = time.time()
                
                logger.info(f"Refreshed {len(new_keys)} JWKS keys from {jwks_url}")
                
            except Exception as e:
                logger.error(f"Failed to refresh JWKS keys: {e}", exc_info=True)
                # Keep existing keys on error

    async def cleanup(self) -> None:
        """Cleanup HTTP client resources."""
        await self._http_client.aclose()


class TokenCache:
    """Thread-safe token validation cache."""
    
    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._last_cleanup = time.time()

    def _cleanup_expired(self) -> None:
        """Remove expired cache entries."""
        current_time = time.time()
        
        if current_time - self._last_cleanup < 60:
            return
            
        expired_keys = [
            key for key, entry in self._cache.items()
            if current_time - entry["cached_at"] > self.ttl_seconds
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        self._last_cleanup = current_time

    def get(self, token_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached token validation result."""
        self._cleanup_expired()
        
        entry = self._cache.get(token_hash)
        if not entry:
            return None
        
        if time.time() - entry["cached_at"] > self.ttl_seconds:
            del self._cache[token_hash]
            return None
        
        return entry["payload"]

    def set(self, token_hash: str, payload: Dict[str, Any]) -> None:
        """Cache token validation result."""
        self._cleanup_expired()
        
        self._cache[token_hash] = {
            "payload": payload,
            "cached_at": time.time()
        }

    def clear(self) -> None:
        """Clear all cached tokens."""
        self._cache.clear()


class OAuth21ResourceServer(BaseHTTPMiddleware):
    """
    OAuth 2.1 Resource Server Middleware for MCP Protocol Compliance.
    
    Implements OAuth 2.1 resource server functionality with:
    - Bearer token validation per RFC 6750
    - JWKS-based signature verification with key rotation
    - Audience validation per RFC 8707
    - Enterprise IdP integration (Auth0, Okta, Keycloak, Azure)
    - Stateless operation with comprehensive security logging
    - High-performance caching and rate limiting
    
    Integrates seamlessly with existing 4-tier credential hierarchy as tier 1.5:
    1. **Client-provided credentials** (request headers) - HIGHEST PRIORITY
    1.5. **OAuth 2.1 Bearer tokens** (validated by this middleware) - VERY HIGH PRIORITY
    2. **User context tokens** (OAuth/Bearer from user session) - HIGH PRIORITY  
    3. **Server configuration credentials** (service defaults) - MEDIUM PRIORITY
    4. **Environment variable fallback** (system defaults) - LOWEST PRIORITY
    """
    
    def __init__(self, app, config: OAuthConfig, next_middleware=None):
        super().__init__(app)
        self.config = config
        self.next_middleware = next_middleware
        self.jwks_cache = JWKSCache(config)
        self.token_cache = TokenCache(config.token_cache_ttl)
        self.rate_limiter: Dict[str, List[float]] = {}
        
        logger.info(
            f"OAuth 2.1 Resource Server initialized: "
            f"issuer={config.issuer_url}, audience={config.audience}, "
            f"idp_type={config.idp_type}"
        )

    async def dispatch(self, request: Request, call_next) -> JSONResponse:
        """
        OAuth 2.1 Bearer token validation middleware.
        
        Processing Flow:
        1. Extract Bearer token from Authorization header
        2. Check token cache for previous validation
        3. Validate token signature using JWKS
        4. Verify standard claims (aud, iss, exp, etc.)
        5. Verify custom claims and scopes
        6. Apply rate limiting per client
        7. Create OAuth credential and integrate with auth hierarchy
        8. Continue to next middleware or pass through
        """
        start_time = time.time()
        
        # Extract client IP for logging and rate limiting
        client_ip = self._get_client_ip(request)
        
        try:
            # Extract Bearer token
            bearer_token = self._extract_bearer_token(request)
            if not bearer_token:
                # No OAuth token present - pass through to next middleware
                return await call_next(request)

            # Check rate limiting
            if self._is_rate_limited(client_ip):
                log_security_event(
                    "oauth_rate_limit_exceeded",
                    client_ip=client_ip,
                    message="OAuth rate limit exceeded"
                )
                return self._create_error_response("rate_limit_exceeded", 429)

            # Validate Bearer token
            token_payload = await self._validate_token(bearer_token, client_ip)
            if not token_payload:
                # Invalid token - return 401
                return self._create_error_response("invalid_token", 401)

            # Create OAuth credential for integration with auth hierarchy
            oauth_credential = self._create_oauth_credential(
                bearer_token, token_payload, client_ip
            )

            # Apply OAuth credential to request state (priority 1.5)
            await self._apply_oauth_credential(request, oauth_credential)

            # Log successful OAuth validation
            log_security_event(
                "oauth_token_validated",
                client_ip=client_ip,
                extra_data={
                    "sub": token_payload.get("sub"),
                    "iss": token_payload.get("iss"),
                    "aud": token_payload.get("aud"),
                    "scopes": token_payload.get("scope", "").split() if token_payload.get("scope") else []
                }
            )

            # Continue to next middleware/handler
            response = await call_next(request)
            
            # Log processing time
            processing_time = (time.time() - start_time) * 1000
            if processing_time > 100:
                logger.warning(
                    f"Slow OAuth validation: {processing_time:.2f}ms",
                    extra={"client_ip": client_ip, "processing_time_ms": processing_time}
                )

            return response

        except Exception as e:
            # Log OAuth error with no token exposure
            log_security_event(
                "oauth_validation_error",
                client_ip=client_ip,
                message=f"OAuth validation error: {type(e).__name__}"
            )
            
            logger.error(f"OAuth validation error from {client_ip}: {e}", exc_info=True)
            
            # Return proper OAuth error response
            return self._create_error_response("server_error", 500)

    def _extract_bearer_token(self, request: Request) -> Optional[str]:
        """Extract Bearer token from Authorization header."""
        auth_header = request.headers.get("authorization", "")
        
        if not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header[7:].strip()
        
        # Basic token format validation
        if not token or len(token) < 20:
            return None
        
        return token

    async def _validate_token(self, token: str, client_ip: str) -> Optional[Dict[str, Any]]:
        """
        Validate OAuth 2.1 Bearer token with comprehensive checks.
        
        Validation Steps:
        1. Check token cache
        2. Decode JWT header to get key ID
        3. Fetch public key from JWKS
        4. Verify JWT signature
        5. Validate standard claims (aud, iss, exp, etc.)
        6. Validate custom claims and scopes
        7. Cache validation result
        """
        try:
            # Generate cache key (hash of token for security)
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            
            # Check token cache
            cached_payload = self.token_cache.get(token_hash)
            if cached_payload:
                logger.debug("OAuth token validation cache hit", extra={"client_ip": client_ip})
                return cached_payload

            # Decode JWT header to get key ID
            try:
                header = jwt.get_unverified_header(token)
            except InvalidTokenError:
                logger.warning("Invalid JWT header", extra={"client_ip": client_ip})
                return None

            kid = header.get("kid")
            if not kid:
                logger.warning("Missing key ID in JWT header", extra={"client_ip": client_ip})
                return None

            # Get public key from JWKS
            jwks_key = await self.jwks_cache.get_key(kid)
            if not jwks_key:
                logger.warning(f"JWKS key not found: {kid}", extra={"client_ip": client_ip})
                return None

            # Construct RSA public key
            public_key = jwt.algorithms.RSAAlgorithm.from_jwk({
                "kty": jwks_key.kty,
                "use": jwks_key.use,
                "n": jwks_key.n,
                "e": jwks_key.e,
                "alg": jwks_key.alg
            })

            # Verify JWT signature and claims
            payload = jwt.decode(
                token,
                public_key,
                algorithms=[self.config.algorithm],
                audience=self.config.audience if self.config.verify_aud else None,
                issuer=self.config.issuer_url if self.config.verify_iss else None,
                options={
                    "verify_exp": self.config.verify_exp,
                    "verify_aud": self.config.verify_aud,
                    "verify_iss": self.config.verify_iss
                },
                leeway=self.config.leeway
            )

            # Validate required scopes
            if self.config.required_scopes:
                token_scopes = payload.get("scope", "").split()
                missing_scopes = set(self.config.required_scopes) - set(token_scopes)
                if missing_scopes:
                    logger.warning(
                        f"Token missing required scopes: {missing_scopes}",
                        extra={"client_ip": client_ip}
                    )
                    return None

            # Validate custom claims
            if self.config.custom_claims:
                for claim_name, expected_value in self.config.custom_claims.items():
                    token_value = payload.get(claim_name)
                    if token_value != expected_value:
                        logger.warning(
                            f"Custom claim validation failed: {claim_name}",
                            extra={"client_ip": client_ip}
                        )
                        return None

            # Cache successful validation
            self.token_cache.set(token_hash, payload)

            logger.debug(
                "OAuth token validated successfully",
                extra={
                    "client_ip": client_ip,
                    "sub": payload.get("sub"),
                    "iss": payload.get("iss")
                }
            )

            return payload

        except ExpiredSignatureError:
            logger.warning("OAuth token expired", extra={"client_ip": client_ip})
            return None
        except InvalidSignatureError:
            logger.warning("Invalid OAuth token signature", extra={"client_ip": client_ip})
            return None
        except InvalidTokenError as e:
            logger.warning(f"Invalid OAuth token: {e}", extra={"client_ip": client_ip})
            return None
        except Exception as e:
            logger.error(f"OAuth token validation error: {e}", extra={"client_ip": client_ip})
            return None

    def _create_oauth_credential(
        self, 
        token: str, 
        payload: Dict[str, Any], 
        client_ip: str
    ) -> AuthCredential:
        """Create AuthCredential from validated OAuth token."""
        return AuthCredential(
            token=token,
            auth_type="oauth2_bearer",
            source=CredentialSource("oauth2_bearer", 1.5, True),  # Priority 1.5
            metadata={
                "sub": payload.get("sub"),
                "iss": payload.get("iss"),
                "aud": payload.get("aud"),
                "scopes": payload.get("scope", "").split() if payload.get("scope") else [],
                "exp": payload.get("exp"),
                "iat": payload.get("iat"),
                "idp_type": self.config.idp_type,
                "oauth2_compliant": True,
                "mcp_protocol_compliant": True
            },
            extracted_at=datetime.now(),
            client_ip=client_ip
        )

    async def _apply_oauth_credential(self, request: Request, credential: AuthCredential) -> None:
        """Apply OAuth credential to request state with priority 1.5."""
        # Set OAuth-specific state
        request.state.oauth_validated = True
        request.state.oauth_token = credential.token
        request.state.oauth_payload = credential.metadata
        request.state.oauth_subject = credential.metadata.get("sub")
        request.state.oauth_scopes = credential.metadata.get("scopes", [])
        
        # Integration with existing auth hierarchy (priority 1.5)
        # This will be picked up by UserTokenMiddleware if it runs after this
        request.state.user_auth_token = credential.token
        request.state.user_auth_type = credential.auth_type
        request.state.user_auth_metadata = credential.metadata.copy()
        request.state.auth_source = credential.source.name
        request.state.auth_validated = True
        request.state.auth_extracted_at = credential.extracted_at

    def _is_rate_limited(self, client_ip: str) -> bool:
        """Check if client is rate limited."""
        current_time = time.time()
        
        # Clean up old requests
        if client_ip in self.rate_limiter:
            self.rate_limiter[client_ip] = [
                req_time for req_time in self.rate_limiter[client_ip]
                if current_time - req_time < 60  # Keep last minute
            ]
        
        # Check rate limit
        requests_count = len(self.rate_limiter.get(client_ip, []))
        if requests_count >= self.config.max_requests_per_minute:
            return True
        
        # Record request
        if client_ip not in self.rate_limiter:
            self.rate_limiter[client_ip] = []
        self.rate_limiter[client_ip].append(current_time)
        
        return False

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check proxy headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        
        if request.client and request.client.host:
            return request.client.host
        
        return "unknown"

    def _create_error_response(self, error: str, status_code: int) -> JSONResponse:
        """Create OAuth 2.1 compliant error response."""
        error_responses = {
            "invalid_token": {
                "error": "invalid_token",
                "error_description": "The access token provided is expired, revoked, malformed, or invalid for other reasons."
            },
            "insufficient_scope": {
                "error": "insufficient_scope", 
                "error_description": "The request requires higher privileges than provided by the access token."
            },
            "rate_limit_exceeded": {
                "error": "rate_limit_exceeded",
                "error_description": "Too many requests. Please try again later."
            },
            "server_error": {
                "error": "server_error",
                "error_description": "The resource server encountered an unexpected condition."
            }
        }
        
        error_response = error_responses.get(error, error_responses["server_error"])
        
        headers = {
            "WWW-Authenticate": f'Bearer realm="{self.config.audience}"',
            "Cache-Control": "no-store"
        }
        
        if error == "rate_limit_exceeded":
            headers["Retry-After"] = "60"

        return JSONResponse(
            error_response,
            status_code=status_code,
            headers=headers
        )

    async def cleanup(self) -> None:
        """Cleanup resources."""
        await self.jwks_cache.cleanup()
        self.token_cache.clear()