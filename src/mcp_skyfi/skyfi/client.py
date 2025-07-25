
import logging
from typing import Any, Optional, Dict
import asyncio
from contextlib import asynccontextmanager

import httpx
from cachetools import TTLCache

from .config import SkyFiConfig
from ..exceptions import SkyFiAuthenticationError, SkyFiAPIError
from ..utils.networking import create_http_client, handle_http_error

logger = logging.getLogger("mcp-skyfi.skyfi.client")

class SkyFiClient:
    """HTTP client for SkyFi Platform API with authentication and error handling."""
    
    def __init__(self, config: SkyFiConfig, user_context: Optional[dict] = None):
        self.config = config
        self.user_context = user_context or {}
        self._client: Optional[httpx.AsyncClient] = None
        self._auth_cache = TTLCache(maxsize=100, ttl=300)  # 5-minute cache
        self._request_semaphore: Optional[asyncio.Semaphore] = None
        
        # Initialize rate limiting semaphore if configured
        if self.config.rate_limit:
            self._request_semaphore = asyncio.Semaphore(self.config.rate_limit)
        
    async def __aenter__(self) -> 'SkyFiClient':
        """Async context manager entry."""
        await self._ensure_client()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None
            
    async def _ensure_client(self) -> None:
        """Ensure HTTP client is initialized with proper authentication."""
        if self._client:
            return
            
        # Determine authentication method
        auth_method = self._get_auth_method()
        headers = await self._build_auth_headers(auth_method)
        
        # Create HTTP client with connection pooling and HTTP/2 support
        limits = httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=30,
        )
        
        timeout = httpx.Timeout(
            connect=10.0,
            read=float(self.config.timeout),
            write=10.0,
            pool=60.0
        )
        
        self._client = httpx.AsyncClient(
            base_url=self.config.url.rstrip('/'),
            headers=headers,
            timeout=timeout,
            verify=self.config.ssl_verify,
            limits=limits,
            http2=True,
            follow_redirects=True,
        )
        
        logger.info(f"SkyFi client initialized with {auth_method} authentication")
        
    def _get_auth_method(self) -> str:
        """Determine authentication method based on user context and config."""
        # Check user-provided authentication first (per-request override)
        if self.user_context.get("auth_token"):
            return self.user_context.get("auth_type", "bearer")
        
        # Check for effective credentials from context (new hive mind integration)
        if hasattr(self.user_context, 'get') and 'effective_credentials' in self.user_context:
            creds = self.user_context['effective_credentials']
            if creds.get('token'):
                return creds.get('type', 'bearer')
        
        # Fall back to server configuration
        return self.config.get_auth_method()
        
    async def _build_auth_headers(self, auth_method: str) -> dict[str, str]:
        """Build authentication headers based on method with enhanced credential support."""
        headers = {
            "User-Agent": "MCP-SkyFi/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        
        # Add custom headers from configuration
        if self.config.custom_headers:
            headers.update(self.config.custom_headers)
        
        # Get effective credentials (new hive mind integration)
        effective_creds = self.user_context.get('effective_credentials', {})
        
        # Add authentication based on method with precedence hierarchy
        if auth_method == "oauth":
            token = (effective_creds.get('token') if effective_creds.get('type') == 'oauth' else
                    self.user_context.get("auth_token") or self.config.oauth_access_token)
            if token:
                headers["Authorization"] = f"Bearer {token}"
        elif auth_method == "api_key":
            api_key = (effective_creds.get('token') if effective_creds.get('type') == 'api_key' else
                      self.user_context.get("auth_token") or self.config.api_key)
            if api_key:
                headers["X-Skyfi-Api-Key"] = api_key
        elif auth_method == "personal_token":
            token = (effective_creds.get('token') if effective_creds.get('type') == 'personal_token' else
                    self.user_context.get("auth_token") or self.config.personal_token)
            if token:
                headers["Authorization"] = f"Bearer {token}"
        elif auth_method == "bearer":
            # Generic bearer token (from client credentials)
            token = (effective_creds.get('token') if effective_creds.get('type') == 'bearer' else
                    self.user_context.get("auth_token"))
            if token:
                headers["Authorization"] = f"Bearer {token}"
                
        return headers
        
    async def get(self, endpoint: str, params: Optional[dict] = None) -> dict[str, Any]:
        """Make authenticated GET request."""
        return await self._request("GET", endpoint, params=params)
        
    async def post(self, endpoint: str, json_data: Optional[dict] = None, params: Optional[dict] = None) -> dict[str, Any]:
        """Make authenticated POST request."""
        return await self._request("POST", endpoint, json=json_data, params=params)
        
    async def put(self, endpoint: str, json_data: Optional[dict] = None) -> dict[str, Any]:
        """Make authenticated PUT request."""  
        return await self._request("PUT", endpoint, json=json_data)
        
    async def delete(self, endpoint: str) -> dict[str, Any]:
        """Make authenticated DELETE request."""
        return await self._request("DELETE", endpoint)
        
    async def _request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[dict] = None,
        json: Optional[dict] = None
    ) -> dict[str, Any]:
        """Make authenticated HTTP request with error handling and retries."""
        await self._ensure_client()
        
        # Apply rate limiting if configured
        if self._request_semaphore:
            async with self._request_semaphore:
                return await self._execute_request(method, endpoint, params, json)
        else:
            return await self._execute_request(method, endpoint, params, json)
    
    async def _execute_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        json: Optional[dict] = None
    ) -> dict[str, Any]:
        """Execute the actual HTTP request with retry logic."""
        url = endpoint.lstrip('/')
        
        for attempt in range(self.config.max_retries + 1):
            try:
                logger.debug(f"Making {method} request to /{url} (attempt {attempt + 1})")
                
                response = await self._client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json
                )
                
                # Handle successful responses
                if response.status_code < 400:
                    try:
                        return response.json()
                    except ValueError:
                        # Handle non-JSON responses
                        return {"status": "success", "data": response.text}
                
                # Handle HTTP errors
                await self._handle_http_error(response, attempt)
                
            except httpx.TimeoutException as e:
                if attempt == self.config.max_retries:
                    logger.error(f"Request timeout after {self.config.max_retries} retries")
                    raise SkyFiAPIError(f"Request timeout after {self.config.max_retries} retries")
                
                logger.warning(f"Request timeout, retrying ({attempt + 1}/{self.config.max_retries})")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
            except httpx.RequestError as e:
                if attempt == self.config.max_retries:
                    logger.error(f"Request failed: {str(e)}")
                    raise SkyFiAPIError(f"Request failed: {str(e)}")
                
                logger.warning(f"Request error, retrying ({attempt + 1}/{self.config.max_retries}): {e}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    async def _handle_http_error(self, response: httpx.Response, attempt: int) -> None:
        """Handle HTTP error responses with appropriate exceptions."""
        try:
            error_data = response.json()
        except ValueError:
            error_data = {"error": response.text or "Unknown error"}
        
        # Authentication errors (don't retry)
        if response.status_code == 401:
            logger.error("Authentication failed - invalid or expired API key")
            raise SkyFiAuthenticationError("Authentication failed. Check your API key.")
        
        # Permission errors (don't retry)
        elif response.status_code == 403:
            logger.error("Permission denied - insufficient privileges")
            raise SkyFiAPIError("Permission denied. Check your account permissions.")
        
        # Not found errors (don't retry)
        elif response.status_code == 404:
            logger.error(f"Resource not found: {response.url}")
            raise SkyFiAPIError("Resource not found.")
        
        # Validation errors (don't retry)
        elif response.status_code == 422:
            error_msg = error_data.get("message", "Validation failed")
            details = error_data.get("details", [])
            logger.error(f"Validation error: {error_msg}, details: {details}")
            raise SkyFiAPIError(f"Validation error: {error_msg}")
        
        # Rate limiting (retry with exponential backoff)
        elif response.status_code == 429:
            if attempt < self.config.max_retries:
                retry_after = int(response.headers.get("Retry-After", 2 ** attempt))
                logger.warning(f"Rate limited, retrying after {retry_after} seconds")
                await asyncio.sleep(retry_after)
                return  # Allow retry
            else:
                raise SkyFiAPIError("Rate limit exceeded. Try again later.")
        
        # Server errors (retry with exponential backoff)
        elif response.status_code >= 500:
            if attempt < self.config.max_retries:
                logger.warning(f"Server error {response.status_code}, retrying...")
                await asyncio.sleep(2 ** attempt)
                return  # Allow retry
            else:
                raise SkyFiAPIError(f"Server error: {response.status_code}")
        
        # Other client errors (don't retry)
        else:
            error_msg = error_data.get("message", f"HTTP {response.status_code}")
            logger.error(f"HTTP error {response.status_code}: {error_msg}")
            raise SkyFiAPIError(f"HTTP {response.status_code}: {error_msg}")
    
    async def validate_auth(self) -> dict[str, Any]:
        """Validate authentication using the /auth/whoami endpoint."""
        try:
            user_info = await self.get("auth/whoami")
            logger.info(f"Authentication validated for user: {user_info.get('email', 'Unknown')}")
            return user_info
        except Exception as e:
            logger.error(f"Authentication validation failed: {e}")
            raise
    
    async def health_check(self) -> dict[str, Any]:
        """Perform health check using the /ping endpoint."""
        try:
            result = await self.get("ping")
            logger.debug("SkyFi API health check passed")
            return result
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise
    
    # Archive-specific methods
    async def search_archives(
        self, 
        geometry: dict, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_cloud_cover: Optional[float] = None,
        limit: int = 100,
        offset: int = 0
    ) -> dict[str, Any]:
        """Search satellite archives with specified criteria."""
        params = {
            "geometry": geometry,
            "limit": limit,
            "offset": offset,
        }
        
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if max_cloud_cover is not None:
            params["max_cloud_cover"] = max_cloud_cover
        
        logger.info(f"Searching archives with geometry: {geometry}")
        return await self.post("archives/search", json_data=params)
    
    async def get_archive_details(self, archive_id: str) -> dict[str, Any]:
        """Get detailed information about a specific archive."""
        logger.info(f"Getting archive details for ID: {archive_id}")
        return await self.get(f"archives/{archive_id}")


class SkyFiClientFactory:
    """
    Factory for creating SkyFi clients with enhanced credential resolution.
    
    This factory integrates with the hive mind architecture to automatically
    resolve credentials using the 4-tier precedence system from MainAppContext.
    """
    
    @staticmethod
    async def create_client(
        app_context: 'MainAppContext',
        user_context: Optional[Dict[str, Any]] = None,
        service: str = "skyfi"
    ) -> SkyFiClient:
        """
        Create a SkyFi client with automatic credential resolution.
        
        Args:
            app_context: Main application context with credential resolution
            user_context: Optional per-request user context
            service: Service name for credential resolution
            
        Returns:
            Configured SkyFi client with resolved credentials
            
        Raises:
            SkyFiMCPError: If no valid credentials are found or service not configured
        """
        from ..servers.context import MainAppContext
        
        # Ensure we have SkyFi configuration
        if not app_context.skyfi_config:
            raise SkyFiAPIError("SkyFi service is not configured")
        
        # Get effective credentials using hive mind resolution
        try:
            credentials = app_context.get_effective_credentials(user_context, service)
            logger.info(f"Resolved credentials from {credentials['source']} (level {credentials['precedence_level']})")
            
            # Enhance user context with resolved credentials
            enhanced_user_context = user_context.copy() if user_context else {}
            enhanced_user_context.update({
                'effective_credentials': credentials,
                'auth_token': credentials['token'],
                'auth_type': credentials['type'],
                'credential_source': credentials['source'],
                'precedence_level': credentials['precedence_level']
            })
            
            # Create client with enhanced context
            client = SkyFiClient(
                config=app_context.skyfi_config,
                user_context=enhanced_user_context
            )
            
            logger.debug(f"Created SkyFi client with {credentials['type']} authentication from {credentials['source']}")
            return client
            
        except Exception as e:
            logger.error(f"Failed to create SkyFi client: {e}")
            raise
    
    @staticmethod
    async def create_authenticated_client(
        app_context: 'MainAppContext',
        auth_token: str,
        auth_type: str = "bearer",
        user_context: Optional[Dict[str, Any]] = None
    ) -> SkyFiClient:
        """
        Create a SkyFi client with explicit authentication override.
        
        This bypasses the credential resolution hierarchy and uses the provided
        authentication directly (Level 1 - Client credentials).
        
        Args:
            app_context: Main application context
            auth_token: Authentication token to use
            auth_type: Type of authentication (bearer, api_key, etc.)
            user_context: Optional additional user context
            
        Returns:
            Configured SkyFi client with explicit authentication
        """
        if not app_context.skyfi_config:
            raise SkyFiAPIError("SkyFi service is not configured")
        
        # Create client-level credential override
        override_context = user_context.copy() if user_context else {}
        override_context.update({
            'auth_token': auth_token,
            'auth_type': auth_type,
            'effective_credentials': {
                'token': auth_token,
                'type': auth_type,
                'source': 'client_override',
                'precedence_level': 1,
                'metadata': {'override': True}
            }
        })
        
        client = SkyFiClient(
            config=app_context.skyfi_config,
            user_context=override_context
        )
        
        logger.info(f"Created SkyFi client with explicit {auth_type} authentication override")
        return client
    
    @staticmethod
    def validate_credentials(credentials: Dict[str, Any]) -> bool:
        """
        Validate credential structure and content.
        
        Args:
            credentials: Credential dictionary to validate
            
        Returns:
            True if credentials are valid, False otherwise
        """
        required_fields = ['token', 'type', 'source', 'precedence_level']
        
        # Check required fields
        if not all(field in credentials for field in required_fields):
            return False
        
        # Check token is not empty
        if not credentials['token'] or not credentials['token'].strip():
            return False
        
        # Check valid authentication types
        valid_types = ['bearer', 'api_key', 'oauth', 'personal_token']
        if credentials['type'] not in valid_types:
            return False
        
        # Check valid precedence level
        if not isinstance(credentials['precedence_level'], int) or credentials['precedence_level'] < 1:
            return False
        
        return True