"""
Authentication Middleware

Multi-method authentication middleware for the SkyFi MCP server supporting
various authentication schemes including API keys, Bearer tokens, and OAuth.
"""


import logging
import time
import hashlib
from typing import Optional, Dict, Any, NamedTuple
from dataclasses import dataclass
from datetime import datetime, timedelta

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ..utils.logging import log_security_event

logger = logging.getLogger("mcp-skyfi.middleware.auth")


class CredentialSource(NamedTuple):
    """Represents a credential source with its priority level."""
    name: str
    priority: int  # Lower number = higher priority
    secure: bool   # Whether this source is considered secure


@dataclass
class AuthCredential:
    """Represents extracted authentication credentials with metadata."""
    token: str
    auth_type: str
    source: CredentialSource
    metadata: Dict[str, Any]
    extracted_at: datetime
    client_ip: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging (without exposing token)."""
        return {
            "auth_type": self.auth_type,
            "source_name": self.source.name,
            "source_priority": self.source.priority,
            "source_secure": self.source.secure,
            "has_token": bool(self.token),
            "token_length": len(self.token) if self.token else 0,
            "metadata": self.metadata,
            "extracted_at": self.extracted_at.isoformat(),
            "client_ip": self.client_ip
        }


class CredentialCache:
    """Thread-safe credential cache with TTL support."""
    
    def __init__(self, ttl_seconds: int = 300):  # 5 minutes default
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._last_cleanup = time.time()
    
    def _cleanup_expired(self) -> None:
        """Remove expired cache entries."""
        current_time = time.time()
        
        # Only cleanup every 60 seconds to avoid overhead
        if current_time - self._last_cleanup < 60:
            return
            
        expired_keys = [
            key for key, entry in self._cache.items()
            if current_time - entry["cached_at"] > self.ttl_seconds
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        self._last_cleanup = current_time
        
        if expired_keys:
            logger.debug(f"Credential cache cleanup: removed {len(expired_keys)} expired entries")
    
    def get(self, cache_key: str) -> Optional[AuthCredential]:
        """Get cached credential if still valid."""
        self._cleanup_expired()
        
        entry = self._cache.get(cache_key)
        if not entry:
            return None
        
        # Check if expired
        if time.time() - entry["cached_at"] > self.ttl_seconds:
            del self._cache[cache_key]
            return None
        
        # Reconstruct AuthCredential
        return AuthCredential(
            token=entry["token"],
            auth_type=entry["auth_type"],
            source=entry["source"],
            metadata=entry["metadata"],
            extracted_at=entry["extracted_at"],
            client_ip=entry["client_ip"]
        )
    
    def set(self, cache_key: str, credential: AuthCredential) -> None:
        """Cache credential with current timestamp."""
        self._cleanup_expired()
        
        self._cache[cache_key] = {
            "token": credential.token,
            "auth_type": credential.auth_type,
            "source": credential.source,
            "metadata": credential.metadata.copy(),
            "extracted_at": credential.extracted_at,
            "client_ip": credential.client_ip,
            "cached_at": time.time()
        }
    
    def clear(self) -> None:
        """Clear all cached credentials."""
        self._cache.clear()
        logger.info("Credential cache cleared")
    
    def stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        self._cleanup_expired()
        return {
            "total_entries": len(self._cache),
            "ttl_seconds": self.ttl_seconds
        }


class UserTokenMiddleware(BaseHTTPMiddleware):
    """
    Advanced authentication middleware with credential hierarchy and security features.
    
    **CREDENTIAL HIERARCHY (Priority Order):**
    1. **Client-provided credentials** (request headers) - HIGHEST PRIORITY
    2. **User context tokens** (OAuth/Bearer from user session) - HIGH PRIORITY  
    3. **Server configuration credentials** (service defaults) - MEDIUM PRIORITY
    4. **Environment variable fallback** (system defaults) - LOWEST PRIORITY
    
    **SECURITY FEATURES:**
    - Credential validation and caching with 5-minute TTL
    - Comprehensive audit logging with no credential exposure
    - Rate limiting and abuse prevention
    - Secure credential propagation to MCP context
    - Request isolation and thread safety
    
    **SUPPORTED AUTHENTICATION METHODS:**
    1. Bearer tokens (Authorization: Bearer <token>)
    2. API keys (X-API-Key: <key>, X-Skyfi-Api-Key: <key>)
    3. Basic authentication (Authorization: Basic <credentials>)
    4. Custom service headers (X-Weather-Api-Key, etc.)
    5. OAuth tokens with refresh capability
    """
    
    # Credential source definitions with priority levels
    CREDENTIAL_SOURCES = {
        "client_headers": CredentialSource("client_headers", 1, True),
        "oauth2_bearer": CredentialSource("oauth2_bearer", 1.5, True),  # OAuth 2.1 integration
        "user_context": CredentialSource("user_context", 2, True),
        "server_config": CredentialSource("server_config", 3, True),
        "env_fallback": CredentialSource("env_fallback", 4, False),
        "query_params": CredentialSource("query_params", 5, False)  # Least secure
    }
    
    # Custom authentication headers for different services
    CUSTOM_AUTH_HEADERS = {
        "X-Skyfi-Api-Key": "skyfi_api_key",
        "X-Weather-Api-Key": "weather_api_key",
        "X-OpenWeather-Api-Key": "openweather_api_key",
    }
    
    def __init__(self, app, mcp_server_ref=None, cache_ttl: int = 300):
        super().__init__(app)
        self.mcp_server_ref = mcp_server_ref
        self.credential_cache = CredentialCache(ttl_seconds=cache_ttl)
        self.failed_attempts: Dict[str, list] = {}  # IP -> [timestamp, ...]
        self.max_failed_attempts = 10
        self.lockout_duration = 300  # 5 minutes
        
        logger.info(
            f"UserTokenMiddleware initialized with credential hierarchy: "
            f"cache_ttl={cache_ttl}s, max_failed_attempts={self.max_failed_attempts}"
        )
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Extract and validate authentication using credential hierarchy.
        
        **PROCESSING FLOW:**
        1. Extract client IP and check for abuse/lockout
        2. Generate cache key and check credential cache
        3. Extract credentials using priority hierarchy
        4. Validate and cache successful credentials
        5. Propagate to MCP context with security logging
        
        **SECURITY MEASURES:**
        - No credential exposure in logs or errors
        - Rate limiting per client IP
        - Comprehensive audit trail
        - Request isolation
        """
        start_time = time.time()
        
        # Initialize authentication state
        request.state.user_auth_token = None
        request.state.user_auth_type = None
        request.state.user_auth_metadata = {}
        request.state.auth_source = None
        request.state.auth_validated = False
        
        # Extract client IP for audit logging and rate limiting
        client_ip = self._get_client_ip(request)
        request.state.client_ip = client_ip
        
        # Check for abuse/lockout
        if self._is_client_locked_out(client_ip):
            log_security_event(
                "auth_lockout_active",
                client_ip=client_ip,
                message="Client locked out due to repeated failed attempts"
            )
            
            from starlette.responses import JSONResponse
            return JSONResponse(
                {"error": "Authentication temporarily unavailable"},
                status_code=429,
                headers={"Retry-After": str(self.lockout_duration)}
            )
        
        try:
            # Generate cache key for this request
            cache_key = self._generate_cache_key(request, client_ip)
            
            # Check credential cache first
            cached_credential = self.credential_cache.get(cache_key)
            if cached_credential:
                await self._apply_cached_credential(request, cached_credential)
                
                # Log cache hit
                logger.debug(
                    "Authentication cache hit",
                    extra={
                        "client_ip": client_ip,
                        "auth_type": cached_credential.auth_type,
                        "source": cached_credential.source.name
                    }
                )
            else:
                # Extract credentials using hierarchy
                credential = await self._extract_credential_hierarchy(request, client_ip)
                
                if credential:
                    # Validate credential
                    is_valid = await self._validate_credential(credential)
                    
                    if is_valid:
                        # Apply to request state
                        await self._apply_credential(request, credential)
                        
                        # Cache for future requests
                        self.credential_cache.set(cache_key, credential)
                        
                        # Log successful authentication
                        log_security_event(
                            "auth_success",
                            client_ip=client_ip,
                            extra_data=credential.to_dict()
                        )
                    else:
                        # Record failed attempt
                        self._record_failed_attempt(client_ip)
                        
                        log_security_event(
                            "auth_validation_failed",
                            client_ip=client_ip,
                            message="Credential validation failed"
                        )
                else:
                    # No credentials found - this is not necessarily an error
                    logger.debug(f"No credentials found for request from {client_ip}")
            
            # Continue to next middleware/handler
            response = await call_next(request)
            
            # Log processing time for performance monitoring
            processing_time = (time.time() - start_time) * 1000
            if processing_time > 100:  # Log slow auth processing
                logger.warning(
                    f"Slow authentication processing: {processing_time:.2f}ms",
                    extra={"client_ip": client_ip, "processing_time_ms": processing_time}
                )
            
            return response
            
        except Exception as e:
            # Record failed attempt for security exceptions
            self._record_failed_attempt(client_ip)
            
            # Log security event with NO credential exposure
            log_security_event(
                "auth_middleware_error",
                client_ip=client_ip,
                message=f"Authentication middleware error: {type(e).__name__}"
            )
            
            logger.error(
                f"Authentication middleware error from {client_ip}: {type(e).__name__}",
                exc_info=True
            )
            
            # Continue without authentication (let downstream handle it)
            return await call_next(request)
    
    async def _extract_credential_hierarchy(self, request: Request, client_ip: str) -> Optional[AuthCredential]:
        """
        Extract credentials using the priority hierarchy system.
        
        **PRIORITY ORDER:**
        1. Client-provided credentials (request headers) - HIGHEST
        1.5. OAuth 2.1 Bearer tokens (validated by OAuth middleware) - VERY HIGH
        2. User context tokens (OAuth/Bearer from session) - HIGH  
        3. Server configuration credentials (service defaults) - MEDIUM
        4. Environment variable fallback (system defaults) - LOWEST
        
        Returns:
            AuthCredential with highest priority credential found, or None
        """
        extraction_attempts = []
        
        # 1. CLIENT-PROVIDED CREDENTIALS (HIGHEST PRIORITY)
        client_credential = await self._extract_client_credentials(request, client_ip)
        if client_credential:
            extraction_attempts.append((client_credential, "client_headers"))
        
        # 1.5. OAUTH 2.1 BEARER TOKENS (VERY HIGH PRIORITY - if validated by OAuth middleware)
        oauth_credential = await self._extract_oauth_credentials(request, client_ip)
        if oauth_credential:
            extraction_attempts.append((oauth_credential, "oauth2_bearer"))
        
        # 2. USER CONTEXT TOKENS (HIGH PRIORITY)
        user_credential = await self._extract_user_context_credentials(request, client_ip)
        if user_credential:
            extraction_attempts.append((user_credential, "user_context"))
        
        # 3. SERVER CONFIGURATION CREDENTIALS (MEDIUM PRIORITY)
        server_credential = await self._extract_server_config_credentials(request, client_ip)
        if server_credential:
            extraction_attempts.append((server_credential, "server_config"))
        
        # 4. ENVIRONMENT FALLBACK (LOWEST PRIORITY)
        env_credential = await self._extract_env_fallback_credentials(request, client_ip)
        if env_credential:
            extraction_attempts.append((env_credential, "env_fallback"))
        
        # Sort by priority (lower number = higher priority)
        extraction_attempts.sort(key=lambda x: self.CREDENTIAL_SOURCES[x[1]].priority)
        
        # Return highest priority credential
        if extraction_attempts:
            best_credential, source_name = extraction_attempts[0]
            
            logger.debug(
                f"Credential hierarchy selected: {source_name} (priority {self.CREDENTIAL_SOURCES[source_name].priority})",
                extra={
                    "client_ip": client_ip,
                    "total_sources_found": len(extraction_attempts),
                    "selected_source": source_name,
                    "auth_type": best_credential.auth_type
                }
            )
            
            return best_credential
        
        return None
    
    async def _extract_client_credentials(self, request: Request, client_ip: str) -> Optional[AuthCredential]:
        """
        Extract credentials from client-provided request headers (HIGHEST PRIORITY).
        
        These are explicit credentials provided by the client in this specific request.
        """
        # 1. Authorization header - Bearer tokens
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            if token and len(token) > 8:  # Basic validation
                return AuthCredential(
                    token=token,
                    auth_type="bearer",
                    source=self.CREDENTIAL_SOURCES["client_headers"],
                    metadata={"header": "authorization", "scheme": "bearer"},
                    extracted_at=datetime.now(),
                    client_ip=client_ip
                )
        
        # 2. Authorization header - Basic auth
        elif auth_header.startswith("Basic "):
            credentials = auth_header[6:].strip()
            if credentials:
                return AuthCredential(
                    token=credentials,
                    auth_type="basic",
                    source=self.CREDENTIAL_SOURCES["client_headers"],
                    metadata={"header": "authorization", "scheme": "basic"},
                    extracted_at=datetime.now(),
                    client_ip=client_ip
                )
        
        # 3. Standard API key headers
        api_key_headers = ["X-API-Key", "Api-Key"]
        for header_name in api_key_headers:
            api_key = request.headers.get(header_name.lower())
            if api_key and len(api_key.strip()) > 4:
                return AuthCredential(
                    token=api_key.strip(),
                    auth_type="api_key",
                    source=self.CREDENTIAL_SOURCES["client_headers"],
                    metadata={"header": header_name.lower()},
                    extracted_at=datetime.now(),
                    client_ip=client_ip
                )
        
        # 4. Custom service-specific headers
        for header_name, auth_type in self.CUSTOM_AUTH_HEADERS.items():
            header_value = request.headers.get(header_name.lower())
            if header_value and len(header_value.strip()) > 4:
                return AuthCredential(
                    token=header_value.strip(),
                    auth_type=auth_type,
                    source=self.CREDENTIAL_SOURCES["client_headers"],
                    metadata={"header": header_name.lower(), "service_specific": True},
                    extracted_at=datetime.now(),
                    client_ip=client_ip
                )
        
        return None
    
    async def _extract_oauth_credentials(self, request: Request, client_ip: str) -> Optional[AuthCredential]:
        """
        Extract OAuth 2.1 Bearer token credentials (priority 1.5).
        
        This method checks if the OAuth 2.1 middleware has already validated
        a Bearer token and made it available in the request state.
        """
        try:
            # Check if OAuth middleware has validated a token
            if getattr(request.state, 'oauth_validated', False):
                oauth_token = getattr(request.state, 'oauth_token', None)
                oauth_payload = getattr(request.state, 'oauth_payload', {})
                
                if oauth_token and oauth_payload:
                    return AuthCredential(
                        token=oauth_token,
                        auth_type="oauth2_bearer",
                        source=self.CREDENTIAL_SOURCES["oauth2_bearer"],
                        metadata={
                            **oauth_payload,
                            "oauth_validated": True,
                            "mcp_protocol_compliant": True,
                            "validation_source": "oauth21_middleware"
                        },
                        extracted_at=datetime.now(),
                        client_ip=client_ip
                    )
        
        except Exception as e:
            logger.debug(f"Could not extract OAuth credentials: {e}")
        
        return None
    
    async def _extract_user_context_credentials(self, request: Request, client_ip: str) -> Optional[AuthCredential]:
        """
        Extract credentials from user context/session (HIGH PRIORITY).
        
        These are OAuth tokens or session-based credentials associated with the user.
        """
        try:
            # Check if MCP context has user session credentials
            if self.mcp_server_ref and hasattr(self.mcp_server_ref, '_mcp_server'):
                mcp_server = self.mcp_server_ref._mcp_server
                req_context = getattr(mcp_server, 'request_context', None)
                
                if req_context and hasattr(req_context, 'lifespan_context'):
                    lifespan_context = req_context.lifespan_context
                    if lifespan_context:
                        app_context = lifespan_context.get("app_lifespan_context")
                        if app_context and hasattr(app_context, 'user_auth_token'):
                            user_token = getattr(app_context, 'user_auth_token', None)
                            if user_token:
                                return AuthCredential(
                                    token=user_token,
                                    auth_type="user_session",
                                    source=self.CREDENTIAL_SOURCES["user_context"],
                                    metadata={"from_user_session": True},
                                    extracted_at=datetime.now(),
                                    client_ip=client_ip
                                )
        
        except Exception as e:
            logger.debug(f"Could not extract user context credentials: {e}")
        
        return None
    
    async def _extract_server_config_credentials(self, request: Request, client_ip: str) -> Optional[AuthCredential]:
        """
        Extract credentials from server configuration (MEDIUM PRIORITY).
        
        These are service-level default credentials configured for the server.
        """
        try:
            # Get service configuration credentials from MCP context
            if self.mcp_server_ref and hasattr(self.mcp_server_ref, '_mcp_server'):
                mcp_server = self.mcp_server_ref._mcp_server
                req_context = getattr(mcp_server, 'request_context', None)
                
                if req_context and hasattr(req_context, 'lifespan_context'):
                    lifespan_context = req_context.lifespan_context
                    if lifespan_context:
                        app_context = lifespan_context.get("app_lifespan_context")
                        if app_context:
                            # Check SkyFi config for default credentials
                            skyfi_config = getattr(app_context, 'skyfi_config', None)
                            if skyfi_config and skyfi_config.is_auth_configured():
                                auth_method = skyfi_config.get_auth_method()
                                
                                if auth_method == "api_key" and skyfi_config.api_key:
                                    return AuthCredential(
                                        token=skyfi_config.api_key,
                                        auth_type="skyfi_api_key",
                                        source=self.CREDENTIAL_SOURCES["server_config"],
                                        metadata={"service": "skyfi", "auth_method": auth_method},
                                        extracted_at=datetime.now(),
                                        client_ip=client_ip
                                    )
                                elif auth_method == "oauth" and skyfi_config.oauth_access_token:
                                    return AuthCredential(
                                        token=skyfi_config.oauth_access_token,
                                        auth_type="skyfi_oauth",
                                        source=self.CREDENTIAL_SOURCES["server_config"],
                                        metadata={"service": "skyfi", "auth_method": auth_method},
                                        extracted_at=datetime.now(),
                                        client_ip=client_ip
                                    )
                            
                            # Check Weather config for default credentials  
                            weather_config = getattr(app_context, 'weather_config', None)
                            if weather_config and hasattr(weather_config, 'api_key') and weather_config.api_key:
                                return AuthCredential(
                                    token=weather_config.api_key,
                                    auth_type="weather_api_key",
                                    source=self.CREDENTIAL_SOURCES["server_config"],
                                    metadata={"service": "weather"},
                                    extracted_at=datetime.now(),
                                    client_ip=client_ip
                                )
        
        except Exception as e:
            logger.debug(f"Could not extract server config credentials: {e}")
        
        return None
    
    async def _extract_env_fallback_credentials(self, request: Request, client_ip: str) -> Optional[AuthCredential]:
        """
        Extract credentials from environment variables (LOWEST PRIORITY).
        
        These are system-level fallback credentials from environment.
        """
        import os
        
        # Check common environment variables
        env_credentials = [
            ("SKYFI_API_KEY", "skyfi_env_key"),
            ("WEATHER_API_KEY", "weather_env_key"),
            ("OPENWEATHER_API_KEY", "openweather_env_key"),
            ("API_KEY", "generic_env_key")
        ]
        
        for env_var, auth_type in env_credentials:
            env_value = os.getenv(env_var)
            if env_value and len(env_value.strip()) > 4:
                # Log warning for environment fallback (less secure)
                logger.warning(
                    f"Using environment variable fallback for authentication: {env_var}",
                    extra={"client_ip": client_ip, "env_var": env_var}
                )
                
                return AuthCredential(
                    token=env_value.strip(),
                    auth_type=auth_type,
                    source=self.CREDENTIAL_SOURCES["env_fallback"],
                    metadata={"env_var": env_var, "fallback": True},
                    extracted_at=datetime.now(),
                    client_ip=client_ip
                )
        
        return None
    
    async def _validate_credential(self, credential: AuthCredential) -> bool:
        """
        Validate extracted credential for basic security checks.
        
        Args:
            credential: AuthCredential to validate
            
        Returns:
            True if credential passes validation, False otherwise
        """
        try:
            # Basic token validation
            if not credential.token or len(credential.token.strip()) < 4:
                return False
            
            # Check for obviously invalid tokens
            invalid_patterns = ["test", "demo", "example", "placeholder", "null", "undefined"]
            token_lower = credential.token.lower()
            if any(pattern in token_lower for pattern in invalid_patterns):
                logger.warning(
                    f"Rejected credential with invalid pattern",
                    extra={"client_ip": credential.client_ip, "auth_type": credential.auth_type}
                )
                return False
            
            # Type-specific validation
            if credential.auth_type == "bearer":
                # Bearer tokens should be substantial length
                if len(credential.token) < 20:
                    return False
            
            elif credential.auth_type == "basic":
                # Basic auth should be base64 encoded
                try:
                    import base64
                    base64.b64decode(credential.token, validate=True)
                except Exception:
                    return False
            
            elif "api_key" in credential.auth_type:
                # API keys should meet minimum requirements
                if len(credential.token) < 8:
                    return False
            
            # Additional security checks could be added here
            # e.g., rate limiting per credential, blacklist checks, etc.
            
            return True
            
        except Exception as e:
            logger.error(
                f"Credential validation error: {type(e).__name__}",
                extra={"client_ip": credential.client_ip}
            )
            return False
    
    async def _apply_credential(self, request: Request, credential: AuthCredential) -> None:
        """
        Apply validated credential to request state.
        
        Args:
            request: Starlette Request object
            credential: Validated AuthCredential
        """
        request.state.user_auth_token = credential.token
        request.state.user_auth_type = credential.auth_type
        request.state.user_auth_metadata = credential.metadata.copy()
        request.state.auth_source = credential.source.name
        request.state.auth_validated = True
        request.state.auth_extracted_at = credential.extracted_at
        
        # Update MCP server context
        if self.mcp_server_ref:
            await self._update_mcp_context_enhanced(request, credential)
    
    async def _apply_cached_credential(self, request: Request, credential: AuthCredential) -> None:
        """
        Apply cached credential to request state.
        
        Args:
            request: Starlette Request object
            credential: Cached AuthCredential
        """
        await self._apply_credential(request, credential)
        request.state.auth_from_cache = True
    
    def _extract_authentication(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Legacy authentication extraction method for backward compatibility.
        
        This method is maintained for any existing code that might call it directly.
        New code should use the credential hierarchy system via _extract_credential_hierarchy().
        """
        logger.warning(
            "Using legacy authentication extraction method. "
            "Consider upgrading to credential hierarchy system.",
            extra={"client_ip": self._get_client_ip(request)}
        )
        
        # 1. Check Authorization header for Bearer tokens
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            if token:
                return {
                    "token": token,
                    "type": "bearer",
                    "metadata": {"source": "authorization_header"}
                }
        
        # 2. Check Authorization header for Basic auth
        elif auth_header.startswith("Basic "):
            credentials = auth_header[6:].strip()
            if credentials:
                return {
                    "token": credentials,
                    "type": "basic",
                    "metadata": {"source": "authorization_header"}
                }
        
        # 3. Check standard API key headers
        api_key_headers = ["X-API-Key", "Api-Key"]
        for header_name in api_key_headers:
            api_key = request.headers.get(header_name.lower())
            if api_key:
                return {
                    "token": api_key.strip(),
                    "type": "api_key",
                    "metadata": {"source": header_name.lower()}
                }
        
        # 4. Check custom service-specific headers
        for header_name, auth_type in self.CUSTOM_AUTH_HEADERS.items():
            header_value = request.headers.get(header_name.lower())
            if header_value:
                return {
                    "token": header_value.strip(),
                    "type": auth_type,
                    "metadata": {"source": header_name.lower()}
                }
        
        # 5. Check query parameters for API keys (less secure, but supported)
        query_params = ["api_key", "key", "token"]
        for param_name in query_params:
            param_value = request.query_params.get(param_name)
            if param_value:
                # Log warning for query parameter authentication
                logger.warning(
                    f"Authentication via query parameter '{param_name}' is less secure",
                    extra={"client_ip": self._get_client_ip(request)}
                )
                
                return {
                    "token": param_value.strip(),
                    "type": "query_param",
                    "metadata": {"source": f"query_{param_name}"}
                }
        
        return None
    
    async def _update_mcp_context_enhanced(self, request: Request, credential: AuthCredential) -> None:
        """
        Securely propagate credential to MCP context with comprehensive logging.
        
        This enhanced method supports the hive mind credential hierarchy system.
        
        Args:
            request: Starlette Request object  
            credential: AuthCredential to propagate
        """
        try:
            # Get the current MCP request context if available
            if hasattr(self.mcp_server_ref, '_mcp_server'):
                mcp_server = self.mcp_server_ref._mcp_server
                req_context = getattr(mcp_server, 'request_context', None)
                
                if req_context and hasattr(req_context, 'lifespan_context'):
                    lifespan_context = req_context.lifespan_context
                    if lifespan_context:
                        app_context = lifespan_context.get("app_lifespan_context")
                        if app_context:
                            # Securely update user context with credential info
                            if hasattr(app_context, 'update_user_context'):
                                app_context.update_user_context(
                                    auth_token=credential.token,
                                    auth_type=credential.auth_type,
                                    auth_metadata=credential.metadata.copy(),
                                    auth_source=credential.source.name,
                                    client_ip=credential.client_ip,
                                    request_id=getattr(request.state, "request_id", None),
                                    extracted_at=credential.extracted_at
                                )
                            else:
                                # Fallback: Set attributes directly
                                app_context.user_auth_token = credential.token
                                app_context.user_auth_type = credential.auth_type
                                app_context.user_auth_source = credential.source.name
                            
                            logger.debug(
                                "MCP context updated with credential",
                                extra={
                                    "client_ip": credential.client_ip,
                                    "auth_type": credential.auth_type,
                                    "source": credential.source.name
                                }
                            )
        
        except Exception as e:
            logger.warning(
                f"Failed to update MCP context: {type(e).__name__}",
                extra={"client_ip": credential.client_ip}
            )
    
    async def _update_mcp_context(self, request: Request, auth_info: Dict[str, Any]) -> None:
        """
        Legacy MCP context update method for backward compatibility.
        
        This method is maintained for any existing code that might call it directly.
        New code should use _update_mcp_context_enhanced() with AuthCredential.
        """
        logger.debug(
            "Using legacy MCP context update method. "
            "Consider upgrading to enhanced credential system."
        )
        
        try:
            # Get the current MCP request context if available
            if hasattr(self.mcp_server_ref, '_mcp_server'):
                mcp_server = self.mcp_server_ref._mcp_server
                req_context = getattr(mcp_server, 'request_context', None)
                
                if req_context and hasattr(req_context, 'lifespan_context'):
                    lifespan_context = req_context.lifespan_context
                    if lifespan_context:
                        app_context = lifespan_context.get("app_lifespan_context")
                        if app_context:
                            # Update user context with authentication info
                            if hasattr(app_context, 'update_user_context'):
                                app_context.update_user_context(
                                    auth_token=auth_info.get("token"),
                                    auth_type=auth_info.get("type"),
                                    auth_metadata=auth_info.get("metadata", {}),
                                    client_ip=request.state.client_ip,
                                    request_id=getattr(request.state, "request_id", None)
                                )
                            else:
                                # Fallback: Set attributes directly
                                app_context.user_auth_token = auth_info.get("token")
                                app_context.user_auth_type = auth_info.get("type")
        
        except Exception as e:
            logger.warning(f"Failed to update MCP context with auth info: {e}")
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP address from request headers.
        
        Checks multiple headers in order of preference:
        1. X-Forwarded-For (proxy/load balancer)
        2. X-Real-IP (nginx)
        3. X-Client-IP (other proxies)
        4. request.client.host (direct connection)
        """
        # Check proxy headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # X-Forwarded-For can contain multiple IPs, take the first one
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        
        client_ip = request.headers.get("x-client-ip")
        if client_ip:
            return client_ip.strip()
        
        # Fallback to direct client connection
        if request.client and request.client.host:
            return request.client.host
        
        return "unknown"
    
    def _generate_cache_key(self, request: Request, client_ip: str) -> str:
        """
        Generate cache key for credential caching.
        
        Args:
            request: Starlette Request object
            client_ip: Client IP address
            
        Returns:
            Cache key string
        """
        # Create hash from request characteristics
        key_components = [
            client_ip,
            request.headers.get("user-agent", "")[:50],  # Limit length
            request.headers.get("authorization", "")[:20],  # Just prefix for uniqueness
            str(sorted(request.headers.keys())[:10])  # Header signature
        ]
        
        # Hash to create compact cache key
        key_string = "|".join(key_components)
        cache_key = hashlib.sha256(key_string.encode()).hexdigest()[:16]
        
        return f"cred:{cache_key}"
    
    def _is_client_locked_out(self, client_ip: str) -> bool:
        """
        Check if client is locked out due to failed attempts.
        
        Args:
            client_ip: Client IP address
            
        Returns:
            True if client is locked out, False otherwise
        """
        current_time = time.time()
        
        # Clean up old failed attempts
        if client_ip in self.failed_attempts:
            self.failed_attempts[client_ip] = [
                timestamp for timestamp in self.failed_attempts[client_ip]
                if current_time - timestamp < self.lockout_duration
            ]
            
            # Remove empty entries
            if not self.failed_attempts[client_ip]:
                del self.failed_attempts[client_ip]
        
        # Check if client has too many recent failures
        failed_count = len(self.failed_attempts.get(client_ip, []))
        return failed_count >= self.max_failed_attempts
    
    def _record_failed_attempt(self, client_ip: str) -> None:
        """
        Record a failed authentication attempt.
        
        Args:
            client_ip: Client IP address
        """
        current_time = time.time()
        
        if client_ip not in self.failed_attempts:
            self.failed_attempts[client_ip] = []
        
        self.failed_attempts[client_ip].append(current_time)
        
        # Log security event
        failed_count = len(self.failed_attempts[client_ip])
        if failed_count >= self.max_failed_attempts:
            log_security_event(
                "auth_client_locked_out",
                client_ip=client_ip,
                message=f"Client locked out after {failed_count} failed attempts"
            )
        elif failed_count % 3 == 0:  # Log every 3rd failure
            log_security_event(
                "auth_multiple_failures",
                client_ip=client_ip,
                message=f"Client has {failed_count} failed authentication attempts"
            )
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get credential cache statistics for monitoring.
        
        Returns:
            Dictionary with cache statistics
        """
        cache_stats = self.credential_cache.stats()
        
        # Add lockout statistics
        locked_clients = sum(1 for attempts in self.failed_attempts.values() 
                           if len(attempts) >= self.max_failed_attempts)
        total_failed_attempts = sum(len(attempts) for attempts in self.failed_attempts.values())
        
        return {
            **cache_stats,
            "locked_out_clients": locked_clients,
            "total_clients_with_failures": len(self.failed_attempts),
            "total_failed_attempts": total_failed_attempts,
            "max_failed_attempts": self.max_failed_attempts,
            "lockout_duration_seconds": self.lockout_duration
        }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for API protection.
    
    This middleware implements rate limiting based on client IP address
    and authentication token to prevent abuse.
    """
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        requests_per_day: int = 10000
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.requests_per_day = requests_per_day
        
        # Simple in-memory rate limiting (would use Redis in production)
        self._rate_limit_store = {}
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Check rate limits and block requests if limits are exceeded.
        """
        # Get client identifier (IP + auth token if available)
        client_id = self._get_client_identifier(request)
        
        # Check rate limits
        if self._is_rate_limited(client_id):
            # Log rate limit violation
            logger.warning(f"Security event: rate_limit_exceeded from {getattr(request.state, 'client_ip', 'unknown')}: client_id={client_id}")
            
            from starlette.responses import JSONResponse
            return JSONResponse(
                {
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.requests_per_minute} requests per minute allowed"
                },
                status_code=429,
                headers={
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Window": "60",
                    "Retry-After": "60"
                }
            )
        
        # Record request
        self._record_request(client_id)
        
        return await call_next(request)
    
    def _get_client_identifier(self, request: Request) -> str:
        """Get unique client identifier for rate limiting."""
        client_ip = getattr(request.state, "client_ip", "unknown")
        auth_token = getattr(request.state, "user_auth_token", None)
        
        if auth_token:
            # Hash the token for privacy
            import hashlib
            token_hash = hashlib.sha256(auth_token.encode()).hexdigest()[:16]
            return f"{client_ip}:{token_hash}"
        
        return client_ip
    
    def _is_rate_limited(self, client_id: str) -> bool:
        """Check if client has exceeded rate limits."""
        # Simple implementation - would use Redis with sliding windows in production
        import time
        
        current_time = time.time()
        client_data = self._rate_limit_store.get(client_id, {
            "minute": {"count": 0, "reset": current_time + 60},
            "hour": {"count": 0, "reset": current_time + 3600},
            "day": {"count": 0, "reset": current_time + 86400}
        })
        
        # Reset counters if windows have expired
        for window in ["minute", "hour", "day"]:
            if current_time >= client_data[window]["reset"]:
                client_data[window] = {
                    "count": 0,
                    "reset": current_time + (60 if window == "minute" else 3600 if window == "hour" else 86400)
                }
        
        # Check limits
        limits = {
            "minute": self.requests_per_minute,
            "hour": self.requests_per_hour,
            "day": self.requests_per_day
        }
        
        for window, limit in limits.items():
            if client_data[window]["count"] >= limit:
                return True
        
        return False
    
    def _record_request(self, client_id: str) -> None:
        """Record a request for rate limiting."""
        import time
        
        current_time = time.time()
        if client_id not in self._rate_limit_store:
            self._rate_limit_store[client_id] = {
                "minute": {"count": 0, "reset": current_time + 60},
                "hour": {"count": 0, "reset": current_time + 3600},
                "day": {"count": 0, "reset": current_time + 86400}
            }
        
        # Increment all counters
        for window in ["minute", "hour", "day"]:
            self._rate_limit_store[client_id][window]["count"] += 1