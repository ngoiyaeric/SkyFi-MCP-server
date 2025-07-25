"""
SkyFi Client Factory

Dynamic client factory for creating authenticated SkyFi clients with
credential precedence, connection pooling, and caching based on collective
intelligence design patterns.

Architecture:
- Factory Pattern: Creates clients dynamically based on user context
- Connection Pooling: Reuses HTTP connections efficiently
- Credential Caching: 5-minute TTL cache for valid credentials
- Thread Safety: Supports concurrent request processing
- Fallback Strategy: Graceful degradation through credential hierarchy
"""


import asyncio
import logging
import threading
import time
from typing import Any, Dict, Optional, Tuple
from weakref import WeakValueDictionary

import httpx
from cachetools import TTLCache

from .client import SkyFiClient
from .config import SkyFiConfig
from ..exceptions import SkyFiAPIError, SkyFiAuthenticationError

logger = logging.getLogger("mcp-skyfi.skyfi.factory")


class CredentialCacheEntry:
    """
    Cached credential entry with validation status and metadata.
    
    Stores credential validation results to avoid repeated API calls
    for the same credentials within the TTL window.
    """
    
    def __init__(
        self,
        credential: str,
        auth_type: str,
        is_valid: bool,
        user_info: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ):
        self.credential = credential
        self.auth_type = auth_type
        self.is_valid = is_valid
        self.user_info = user_info or {}
        self.error_message = error_message
        self.created_at = time.time()
        self.last_validated = time.time()
        self.validation_count = 1

    def refresh_validation(self, is_valid: bool, user_info: Optional[Dict[str, Any]] = None, error_message: Optional[str] = None) -> None:
        """Update validation status with new check results."""
        self.is_valid = is_valid
        self.user_info = user_info or {}
        self.error_message = error_message
        self.last_validated = time.time()
        self.validation_count += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging and debugging."""
        return {
            "auth_type": self.auth_type,
            "is_valid": self.is_valid,
            "created_at": self.created_at,
            "last_validated": self.last_validated,
            "validation_count": self.validation_count,
            "has_user_info": bool(self.user_info),
            "error_message": self.error_message
        }


class ConnectionPool:
    """
    HTTP connection pool manager for efficient connection reuse.
    
    Manages HTTP client instances with proper connection limits,
    timeouts, and lifecycle management.
    """
    
    def __init__(self, max_connections: int = 100, max_keepalive: int = 20):
        self.max_connections = max_connections
        self.max_keepalive = max_keepalive
        self._clients: WeakValueDictionary[str, httpx.AsyncClient] = WeakValueDictionary()
        self._lock = threading.Lock()
        self._created_count = 0
        self._cleanup_count = 0

    def get_client_key(self, config: SkyFiConfig, user_context: Dict[str, Any]) -> str:
        """
        Generate unique key for client based on configuration and auth.
        
        This ensures clients with different auth contexts are properly isolated
        while allowing reuse for identical configurations.
        """
        # Base key from configuration
        base_key = f"{config.url}:{config.get_auth_method()}"
        
        # Add user context if available
        auth_token = user_context.get("auth_token")
        if auth_token:
            # Use hash for security, first/last chars for debugging
            import hashlib
            token_hash = hashlib.sha256(auth_token.encode()).hexdigest()[:16]
            auth_type = user_context.get("auth_type", "unknown")
            base_key += f":{auth_type}:{token_hash}"
        
        return base_key

    async def get_or_create_client(self, config: SkyFiConfig, user_context: Dict[str, Any]) -> httpx.AsyncClient:
        """
        Get existing HTTP client or create new one with connection pooling.
        
        Returns a properly configured HTTP client with authentication headers,
        connection limits, and timeout settings.
        """
        client_key = self.get_client_key(config, user_context)
        
        with self._lock:
            # Check if client already exists
            existing_client = self._clients.get(client_key)
            if existing_client and not existing_client.is_closed:
                logger.debug(f"Reusing HTTP client for key: {client_key[:32]}...")
                return existing_client

            # Create new client
            self._created_count += 1
            logger.debug(f"Creating new HTTP client #{self._created_count} for key: {client_key[:32]}...")

        # Build authentication headers
        headers = await self._build_auth_headers(config, user_context)
        
        # Configure connection limits
        limits = httpx.Limits(
            max_keepalive_connections=self.max_keepalive,
            max_connections=self.max_connections,
            keepalive_expiry=30,
        )
        
        # Configure timeouts
        timeout = httpx.Timeout(
            connect=10.0,
            read=float(config.timeout),
            write=10.0,
            pool=60.0
        )
        
        # Create HTTP client
        client = httpx.AsyncClient(
            base_url=config.url.rstrip('/'),
            headers=headers,
            timeout=timeout,
            verify=config.ssl_verify,
            limits=limits,
            http2=True,
            follow_redirects=True,
        )
        
        # Store in pool
        with self._lock:
            self._clients[client_key] = client
        
        logger.info(f"HTTP client created with {config.get_auth_method()} authentication")
        return client

    async def _build_auth_headers(self, config: SkyFiConfig, user_context: Dict[str, Any]) -> Dict[str, str]:
        """Build authentication headers based on config and user context."""
        headers = {
            "User-Agent": "SkyFi-MCP-Factory/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        
        # Add custom headers from configuration
        if config.custom_headers:
            headers.update(config.custom_headers)
        
        # Determine authentication method and credentials
        auth_token = user_context.get("auth_token")
        auth_type = user_context.get("auth_type", "bearer")
        
        if auth_token:
            # Use per-request authentication
            if auth_type == "bearer" or auth_type == "oauth":
                headers["Authorization"] = f"Bearer {auth_token}"
            elif auth_type == "api_key" or auth_type == "skyfi_api_key":
                headers["X-Skyfi-Api-Key"] = auth_token
            elif auth_type == "personal_token":
                headers["Authorization"] = f"Bearer {auth_token}"
            else:
                # Default to API key for unknown types
                headers["X-Skyfi-Api-Key"] = auth_token
        else:
            # Fall back to configuration authentication
            auth_method = config.get_auth_method()
            
            if auth_method == "oauth" and config.oauth_access_token:
                headers["Authorization"] = f"Bearer {config.oauth_access_token}"
            elif auth_method == "api_key" and config.api_key:
                headers["X-Skyfi-Api-Key"] = config.api_key
            elif auth_method == "personal_token" and config.personal_token:
                headers["Authorization"] = f"Bearer {config.personal_token}"
        
        return headers

    async def cleanup_closed_clients(self) -> int:
        """Remove closed clients from the pool."""
        with self._lock:
            closed_keys = [key for key, client in self._clients.items() if client.is_closed]
            for key in closed_keys:
                del self._clients[key]
                self._cleanup_count += 1
            
            if closed_keys:
                logger.debug(f"Cleaned up {len(closed_keys)} closed HTTP clients")
            
            return len(closed_keys)

    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        with self._lock:
            active_clients = len([c for c in self._clients.values() if not c.is_closed])
            return {
                "total_created": self._created_count,
                "active_clients": active_clients,
                "total_in_pool": len(self._clients),
                "cleaned_up": self._cleanup_count,
                "max_connections": self.max_connections,
                "max_keepalive": self.max_keepalive
            }


class SkyFiClientFactory:
    """
    Factory for creating authenticated SkyFi clients with connection pooling and credential caching.
    
    This factory implements the collective intelligence design pattern for dynamic
    client creation with the following features:
    
    - **Credential Precedence**: User context > OAuth > API Key > Personal Token
    - **Credential Caching**: 5-minute TTL cache for validation results
    - **Connection Pooling**: Efficient HTTP connection reuse
    - **Thread Safety**: Concurrent request support
    - **Fallback Strategy**: Graceful degradation through credential hierarchy
    - **Performance Optimization**: Minimal API calls through intelligent caching
    
    Usage:
        factory = SkyFiClientFactory()
        client = await factory.create_client(user_context, config)
        async with client:
            result = await client.get("archives/search")
    """
    
    def __init__(
        self,
        credential_cache_ttl: int = 300,  # 5 minutes
        credential_cache_size: int = 1000,
        connection_pool_size: int = 100,
        enable_credential_validation: bool = True
    ):
        """
        Initialize the SkyFi client factory.
        
        Args:
            credential_cache_ttl: TTL for credential validation cache in seconds
            credential_cache_size: Maximum number of cached credentials
            connection_pool_size: Maximum HTTP connections in pool
            enable_credential_validation: Whether to validate credentials before caching
        """
        self.credential_cache_ttl = credential_cache_ttl
        self.credential_cache_size = credential_cache_size
        self.enable_credential_validation = enable_credential_validation
        
        # Thread-safe credential cache
        self._credential_cache: TTLCache[str, CredentialCacheEntry] = TTLCache(
            maxsize=credential_cache_size,
            ttl=credential_cache_ttl
        )
        self._cache_lock = threading.RLock()
        
        # HTTP connection pool
        self._connection_pool = ConnectionPool(max_connections=connection_pool_size)
        
        # Factory statistics
        self._stats = {
            "clients_created": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "validation_attempts": 0,
            "validation_successes": 0,
            "validation_failures": 0,
            "fallback_attempts": 0
        }
        self._stats_lock = threading.Lock()
        
        logger.info(f"SkyFiClientFactory initialized: cache_ttl={credential_cache_ttl}s, pool_size={connection_pool_size}")

    async def create_client(self, user_context: Dict[str, Any], config: SkyFiConfig) -> SkyFiClient:
        """
        Create an authenticated SkyFi client with credential precedence and caching.
        
        This method implements the core factory logic:
        1. Determine authentication credentials using precedence hierarchy
        2. Check credential cache for validation results
        3. Validate credentials if not cached or validation enabled
        4. Create SkyFiClient with proper HTTP client from connection pool
        5. Cache validation results for future requests
        
        Args:
            user_context: Per-request user context with potential auth overrides
            config: SkyFi configuration with server-level authentication
            
        Returns:
            Configured SkyFiClient instance ready for API calls
            
        Raises:
            SkyFiAuthenticationError: If no valid authentication is available
            SkyFiAPIError: If client creation fails
        """
        with self._stats_lock:
            self._stats["clients_created"] += 1
        
        try:
            # 1. Determine authentication credentials
            auth_info = self._determine_auth_credentials(user_context, config)
            logger.debug(f"Determined auth method: {auth_info['type']}")
            
            # 2. Check credential cache
            cache_key = self._build_cache_key(auth_info)
            cached_entry = self._get_cached_credential(cache_key)
            
            if cached_entry:
                with self._stats_lock:
                    self._stats["cache_hits"] += 1
                logger.debug(f"Credential cache hit for {auth_info['type']}")
                
                # Use cached validation result
                if not cached_entry.is_valid:
                    logger.warning(f"Using cached invalid credential for {auth_info['type']}: {cached_entry.error_message}")
                    # Try fallback auth if cache shows invalid
                    fallback_auth = self._try_fallback_auth(user_context, config, auth_info['type'])
                    if fallback_auth:
                        auth_info = fallback_auth
                        cache_key = self._build_cache_key(auth_info)
                        cached_entry = self._get_cached_credential(cache_key)
            else:
                with self._stats_lock:
                    self._stats["cache_misses"] += 1
                logger.debug(f"Credential cache miss for {auth_info['type']}")
            
            # 3. Validate credentials if needed
            if self.enable_credential_validation and (not cached_entry or not cached_entry.is_valid):
                try:
                    validation_result = await self._validate_credentials(auth_info, config)
                    
                    # Cache validation result
                    cache_entry = CredentialCacheEntry(
                        credential=auth_info['token'][:16] + "...",  # Masked for security
                        auth_type=auth_info['type'],
                        is_valid=validation_result['is_valid'],
                        user_info=validation_result.get('user_info'),
                        error_message=validation_result.get('error_message')
                    )
                    self._cache_credential(cache_key, cache_entry)
                    
                    if not validation_result['is_valid']:
                        logger.warning(f"Credential validation failed for {auth_info['type']}")
                        # Try fallback authentication
                        fallback_auth = self._try_fallback_auth(user_context, config, auth_info['type'])
                        if fallback_auth:
                            auth_info = fallback_auth
                        else:
                            raise SkyFiAuthenticationError(
                                f"Authentication failed: {validation_result.get('error_message', 'Invalid credentials')}"
                            )
                
                except Exception as e:
                    logger.error(f"Credential validation error: {e}")
                    # Continue with unvalidated credentials if validation fails
                    pass
            
            # 4. Create SkyFi client with enhanced user context
            enhanced_user_context = {**user_context}
            enhanced_user_context.update({
                "auth_token": auth_info['token'],
                "auth_type": auth_info['type'],
                "factory_created": True,
                "credential_cached": bool(cached_entry),
                "validation_status": cached_entry.is_valid if cached_entry else "unknown"
            })
            
            # Create the client
            client = SkyFiClient(config=config, user_context=enhanced_user_context)
            
            # Override HTTP client with pooled connection
            try:
                pooled_client = await self._connection_pool.get_or_create_client(config, enhanced_user_context)
                client._client = pooled_client
            except Exception as e:
                logger.warning(f"Failed to use pooled HTTP client: {e}")
                # Fall back to default client creation
            
            logger.info(f"SkyFi client created successfully with {auth_info['type']} authentication")
            return client
            
        except Exception as e:
            logger.error(f"Failed to create SkyFi client: {e}", exc_info=True)
            if isinstance(e, (SkyFiAuthenticationError, SkyFiAPIError)):
                raise
            raise SkyFiAPIError(f"Client factory error: {str(e)}")

    def _determine_auth_credentials(self, user_context: Dict[str, Any], config: SkyFiConfig) -> Dict[str, str]:
        """
        Determine authentication credentials using precedence hierarchy.
        
        Precedence Order:
        1. User context authentication (per-request override)
        2. OAuth access token (most secure)
        3. API key (standard authentication)
        4. Personal access token (enterprise/self-hosted)
        
        Returns:
            Dictionary with 'token' and 'type' keys
            
        Raises:
            SkyFiAuthenticationError: If no authentication is available
        """
        # 1. Check user-provided authentication (highest precedence)
        user_token = user_context.get("auth_token")
        if user_token:
            auth_type = user_context.get("auth_type", "bearer")
            logger.debug("Using per-request authentication from user context")
            return {"token": user_token, "type": auth_type}
        
        # 2. Check OAuth access token
        if config.oauth_access_token:
            logger.debug("Using OAuth access token from configuration")
            return {"token": config.oauth_access_token, "type": "oauth"}
        
        # 3. Check API key
        if config.api_key:
            logger.debug("Using API key from configuration")
            return {"token": config.api_key, "type": "api_key"}
        
        # 4. Check personal access token
        if config.personal_token:
            logger.debug("Using personal token from configuration")
            return {"token": config.personal_token, "type": "personal_token"}
        
        # No authentication available
        raise SkyFiAuthenticationError(
            "No authentication credentials available. Please provide API key, OAuth token, or personal token."
        )

    def _try_fallback_auth(self, user_context: Dict[str, Any], config: SkyFiConfig, failed_auth_type: str) -> Optional[Dict[str, str]]:
        """
        Try fallback authentication methods when primary method fails.
        
        This implements graceful degradation through the credential hierarchy.
        """
        with self._stats_lock:
            self._stats["fallback_attempts"] += 1
        
        logger.info(f"Attempting fallback authentication (failed: {failed_auth_type})")
        
        # Skip the failed auth type and try remaining methods
        fallback_order = []
        
        if failed_auth_type != "oauth" and config.oauth_access_token:
            fallback_order.append(("oauth", config.oauth_access_token))
        
        if failed_auth_type != "api_key" and config.api_key:
            fallback_order.append(("api_key", config.api_key))
        
        if failed_auth_type != "personal_token" and config.personal_token:
            fallback_order.append(("personal_token", config.personal_token))
        
        for auth_type, token in fallback_order:
            logger.debug(f"Trying fallback authentication: {auth_type}")
            return {"token": token, "type": auth_type}
        
        logger.warning("No fallback authentication methods available")
        return None

    async def _validate_credentials(self, auth_info: Dict[str, str], config: SkyFiConfig) -> Dict[str, Any]:
        """
        Validate authentication credentials by making a test API call.
        
        This uses the /auth/whoami endpoint to verify credentials are valid
        and returns user information for caching.
        """
        with self._stats_lock:
            self._stats["validation_attempts"] += 1
        
        try:
            logger.debug(f"Validating {auth_info['type']} credentials")
            
            # Create temporary client for validation
            temp_user_context = {
                "auth_token": auth_info['token'],
                "auth_type": auth_info['type']
            }
            temp_client = SkyFiClient(config=config, user_context=temp_user_context)
            
            # Make validation request
            async with temp_client:
                user_info = await temp_client.validate_auth()
                
                with self._stats_lock:
                    self._stats["validation_successes"] += 1
                
                logger.info(f"Credential validation successful for {auth_info['type']}")
                return {
                    "is_valid": True,
                    "user_info": user_info,
                    "error_message": None
                }
                
        except SkyFiAuthenticationError as e:
            with self._stats_lock:
                self._stats["validation_failures"] += 1
            
            logger.warning(f"Credential validation failed for {auth_info['type']}: {e}")
            return {
                "is_valid": False,
                "user_info": None,
                "error_message": str(e)
            }
        
        except Exception as e:
            with self._stats_lock:
                self._stats["validation_failures"] += 1
            
            logger.error(f"Credential validation error for {auth_info['type']}: {e}")
            return {
                "is_valid": False,
                "user_info": None,
                "error_message": f"Validation error: {str(e)}"
            }

    def _build_cache_key(self, auth_info: Dict[str, str]) -> str:
        """Build cache key for credential validation results."""
        import hashlib
        
        # Create key from auth type and hashed token
        token_hash = hashlib.sha256(auth_info['token'].encode()).hexdigest()
        return f"{auth_info['type']}:{token_hash[:32]}"

    def _get_cached_credential(self, cache_key: str) -> Optional[CredentialCacheEntry]:
        """Get cached credential validation result."""
        with self._cache_lock:
            return self._credential_cache.get(cache_key)

    def _cache_credential(self, cache_key: str, entry: CredentialCacheEntry) -> None:
        """Cache credential validation result."""
        with self._cache_lock:
            self._credential_cache[cache_key] = entry
            logger.debug(f"Cached credential validation for {entry.auth_type} (valid: {entry.is_valid})")

    async def cleanup_resources(self) -> Dict[str, Any]:
        """
        Clean up factory resources and return cleanup statistics.
        
        This method should be called periodically or during shutdown
        to clean up closed connections and expired cache entries.
        """
        logger.info("Cleaning up SkyFiClientFactory resources")
        
        # Clean up connection pool
        closed_clients = await self._connection_pool.cleanup_closed_clients()
        
        # Clean up credential cache (TTL cache handles expiration automatically)
        with self._cache_lock:
            cache_size_before = len(self._credential_cache)
            # Force cleanup of expired entries
            self._credential_cache.expire()
            cache_size_after = len(self._credential_cache)
            cache_cleaned = cache_size_before - cache_size_after
        
        cleanup_stats = {
            "closed_clients_removed": closed_clients,
            "cache_entries_expired": cache_cleaned,
            "cache_size_after": cache_size_after,
            "cleanup_timestamp": time.time()
        }
        
        logger.info(f"Cleanup completed: {cleanup_stats}")
        return cleanup_stats

    def get_factory_stats(self) -> Dict[str, Any]:
        """Get comprehensive factory statistics."""
        with self._stats_lock:
            factory_stats = self._stats.copy()
        
        with self._cache_lock:
            cache_stats = {
                "cache_size": len(self._credential_cache),
                "cache_maxsize": self._credential_cache.maxsize,
                "cache_ttl": self._credential_cache.ttl,
                "cache_hit_rate": (
                    factory_stats["cache_hits"] / 
                    (factory_stats["cache_hits"] + factory_stats["cache_misses"])
                    if (factory_stats["cache_hits"] + factory_stats["cache_misses"]) > 0 else 0
                )
            }
        
        connection_stats = self._connection_pool.get_stats()
        
        return {
            "factory": factory_stats,
            "cache": cache_stats,
            "connections": connection_stats,
            "timestamp": time.time()
        }

    def clear_credential_cache(self) -> int:
        """Clear all cached credentials and return count of cleared entries."""
        with self._cache_lock:
            cleared_count = len(self._credential_cache)
            self._credential_cache.clear()
            logger.info(f"Cleared {cleared_count} cached credential entries")
            return cleared_count

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.cleanup_resources()


# Global factory instance for reuse across requests
_global_factory: Optional[SkyFiClientFactory] = None
_factory_lock = threading.Lock()


def get_client_factory(
    credential_cache_ttl: int = 300,
    credential_cache_size: int = 1000,
    connection_pool_size: int = 100,
    enable_credential_validation: bool = True
) -> SkyFiClientFactory:
    """
    Get or create global SkyFiClientFactory instance.
    
    This function provides a singleton factory instance for efficient
    resource sharing across multiple requests and services.
    
    Args:
        credential_cache_ttl: TTL for credential validation cache
        credential_cache_size: Maximum cached credentials
        connection_pool_size: Maximum HTTP connections
        enable_credential_validation: Whether to validate credentials
        
    Returns:
        Shared SkyFiClientFactory instance
    """
    global _global_factory
    
    with _factory_lock:
        if _global_factory is None:
            logger.info("Creating global SkyFiClientFactory instance")
            _global_factory = SkyFiClientFactory(
                credential_cache_ttl=credential_cache_ttl,
                credential_cache_size=credential_cache_size,
                connection_pool_size=connection_pool_size,
                enable_credential_validation=enable_credential_validation
            )
        
        return _global_factory


async def create_skyfi_client(user_context: Dict[str, Any], config: SkyFiConfig) -> SkyFiClient:
    """
    Convenience function to create SkyFi client using global factory.
    
    This is the primary entry point for creating authenticated SkyFi clients
    with all the factory benefits (caching, pooling, etc.).
    
    Args:
        user_context: Per-request user context with auth information
        config: SkyFi configuration
        
    Returns:
        Configured SkyFiClient instance
        
    Usage:
        client = await create_skyfi_client(user_context, config)
        async with client:
            archives = await client.search_archives(geometry)
    """
    factory = get_client_factory()
    return await factory.create_client(user_context, config)