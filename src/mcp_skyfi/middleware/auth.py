"""
Authentication Middleware

Multi-method authentication middleware for the SkyFi MCP server supporting
various authentication schemes including API keys, Bearer tokens, and OAuth.
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ..utils.logging import log_security_event

logger = logging.getLogger("mcp-skyfi.middleware.auth")


class UserTokenMiddleware(BaseHTTPMiddleware):
    """
    Extract and validate per-request authentication tokens.
    
    This middleware extracts authentication information from various headers
    and makes it available to the downstream request handlers through the
    request state.
    
    Supported Authentication Methods:
    1. Bearer tokens (Authorization: Bearer <token>)
    2. API keys (X-API-Key: <key>, X-Skyfi-Api-Key: <key>)
    3. Basic authentication (Authorization: Basic <credentials>)
    4. Custom headers (configurable per service)
    """
    
    # Custom authentication headers for different services
    CUSTOM_AUTH_HEADERS = {
        "X-Skyfi-Api-Key": "skyfi_api_key",
        "X-Weather-Api-Key": "weather_api_key",
        "X-OpenWeather-Api-Key": "openweather_api_key",
    }
    
    def __init__(self, app, mcp_server_ref=None):
        super().__init__(app)
        self.mcp_server_ref = mcp_server_ref
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Extract authentication information from request headers.
        
        The extracted authentication information is stored in request.state
        for use by downstream handlers and service clients.
        """
        # Initialize authentication state
        request.state.user_auth_token = None
        request.state.user_auth_type = None
        request.state.user_auth_metadata = {}
        
        # Extract client IP for audit logging
        client_ip = self._get_client_ip(request)
        request.state.client_ip = client_ip
        
        try:
            # Extract authentication from various headers
            auth_info = self._extract_authentication(request)
            
            if auth_info:
                request.state.user_auth_token = auth_info.get("token")
                request.state.user_auth_type = auth_info.get("type")
                request.state.user_auth_metadata = auth_info.get("metadata", {})
                
                # Log successful authentication extraction
                logger.debug(
                    f"Authentication extracted: type={auth_info.get('type')}",
                    extra={
                        "auth_type": auth_info.get("type"),
                        "client_ip": client_ip,
                        "has_token": bool(auth_info.get("token"))
                    }
                )
                
                # Update MCP server context if available
                if self.mcp_server_ref:
                    await self._update_mcp_context(request, auth_info)
            
            # Continue to next middleware/handler
            response = await call_next(request)
            
            return response
            
        except Exception as e:
            logger.error(f"Authentication middleware error: {e}", exc_info=True)
            
            # Log security event for middleware errors
            log_security_event(
                event_type="auth_middleware_error",
                ip_address=client_ip,
                details={"error": str(e)}
            )
            
            # Continue without authentication (let downstream handle it)
            return await call_next(request)
    
    def _extract_authentication(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Extract authentication information from request headers.
        
        Returns:
            Dictionary with token, type, and metadata, or None if no auth found
        """
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
    
    async def _update_mcp_context(self, request: Request, auth_info: Dict[str, Any]) -> None:
        """
        Update MCP server context with authentication information.
        
        This allows the MCP tools to access user authentication data
        for making authenticated requests to external services.
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
                            # Update user context with authentication info
                            app_context.update_user_context(
                                auth_token=auth_info.get("token"),
                                auth_type=auth_info.get("type"),
                                auth_metadata=auth_info.get("metadata", {}),
                                client_ip=request.state.client_ip,
                                request_id=getattr(request.state, "request_id", None)
                            )
        
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
            log_security_event(
                event_type="rate_limit_exceeded",
                ip_address=getattr(request.state, "client_ip", "unknown"),
                details={"client_id": client_id}
            )
            
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