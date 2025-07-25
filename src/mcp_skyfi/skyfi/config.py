"""
SkyFi Configuration

Configuration management for SkyFi Platform API integration with
multi-method authentication and enterprise features.
"""


import os
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

from ..utils.environment import (
    get_env_bool, get_env_int, get_env_list, get_env_dict, validate_env_url
)


@dataclass
class SkyFiConfig:
    """
    Configuration for SkyFi Platform API integration.
    
    Supports multiple authentication methods in order of precedence:
    1. OAuth 2.0 (highest priority if configured)
    2. API Key authentication
    3. Personal Access Token (for enterprise/self-hosted)
    
    Also includes network configuration, rate limiting, and filtering options.
    """
    
    # Required configuration
    url: str
    """SkyFi Platform API base URL"""
    
    # Authentication methods (in order of precedence)
    # OAuth 2.0 (highest priority if configured)
    oauth_client_id: Optional[str] = None
    oauth_client_secret: Optional[str] = None  
    oauth_access_token: Optional[str] = None
    oauth_refresh_token: Optional[str] = None
    oauth_scope: Optional[str] = None
    
    # API Key authentication (standard method)
    api_key: Optional[str] = None
    """SkyFi Platform API key - primary authentication method"""
    
    # Personal Access Token (for enterprise/self-hosted)
    personal_token: Optional[str] = None
    
    # Network configuration
    ssl_verify: bool = True
    """Enable SSL certificate verification"""
    
    timeout: int = 30
    """HTTP request timeout in seconds"""
    
    max_retries: int = 3
    """Maximum number of retry attempts for failed requests"""
    
    # Service-specific configuration
    default_workspace: Optional[str] = None
    """Default workspace/organization ID"""
    
    rate_limit: Optional[int] = None
    """Custom rate limit override (requests per minute)"""
    
    # Filtering and access control
    allowed_projects: Optional[List[str]] = None
    """Whitelist of project IDs that can be accessed"""
    
    custom_headers: Optional[Dict[str, str]] = None
    """Custom HTTP headers to include with requests"""
    
    # Feature toggles
    enable_webhooks: bool = True
    """Enable webhook notification features"""
    
    enable_ordering: bool = True
    """Enable order creation features"""
    
    enable_open_data: bool = True
    """Enable access to open data (free) imagery"""
    
    # Caching configuration
    cache_enabled: bool = True
    """Enable response caching for read operations"""
    
    cache_ttl: int = 300
    """Cache time-to-live in seconds (5 minutes default)"""

    @classmethod
    def from_env(cls) -> 'SkyFiConfig':
        """
        Create configuration from environment variables.
        
        Environment Variables:
            SKYFI_API_URL or SKYFI_URL: API base URL (required)
            SKYFI_API_KEY: API key for authentication
            SKYFI_OAUTH_CLIENT_ID: OAuth client ID
            SKYFI_OAUTH_CLIENT_SECRET: OAuth client secret
            SKYFI_OAUTH_ACCESS_TOKEN: OAuth access token
            SKYFI_OAUTH_REFRESH_TOKEN: OAuth refresh token
            SKYFI_OAUTH_SCOPE: OAuth scope
            SKYFI_PERSONAL_TOKEN: Personal access token
            SKYFI_SSL_VERIFY: Enable SSL verification (default: true)
            SKYFI_TIMEOUT: Request timeout in seconds (default: 30)
            SKYFI_MAX_RETRIES: Maximum retry attempts (default: 3)
            SKYFI_DEFAULT_WORKSPACE: Default workspace ID
            SKYFI_RATE_LIMIT: Rate limit override
            SKYFI_ALLOWED_PROJECTS: Comma-separated project IDs
            SKYFI_CUSTOM_HEADERS: Custom headers (key=value,key2=value2)
            SKYFI_ENABLE_WEBHOOKS: Enable webhook features (default: true)
            SKYFI_ENABLE_ORDERING: Enable ordering features (default: true)
            SKYFI_ENABLE_OPEN_DATA: Enable open data access (default: true)
            SKYFI_CACHE_ENABLED: Enable response caching (default: true)
            SKYFI_CACHE_TTL: Cache TTL in seconds (default: 300)
        
        Returns:
            SkyFiConfig instance populated from environment
            
        Raises:
            ValueError: If required URL is not provided
        """
        
        # Get API URL (required)
        api_url = validate_env_url("SKYFI_API_URL") or validate_env_url("SKYFI_URL")
        if not api_url:
            raise ValueError(
                "SkyFi API URL is required. Set SKYFI_API_URL or SKYFI_URL environment variable."
            )
        
        # Parse custom headers
        custom_headers = get_env_dict("SKYFI_CUSTOM_HEADERS")

        return cls(
            # Required
            url=api_url,
            
            # OAuth 2.0
            oauth_client_id=os.getenv("SKYFI_OAUTH_CLIENT_ID"),
            oauth_client_secret=os.getenv("SKYFI_OAUTH_CLIENT_SECRET"),
            oauth_access_token=os.getenv("SKYFI_OAUTH_ACCESS_TOKEN"),
            oauth_refresh_token=os.getenv("SKYFI_OAUTH_REFRESH_TOKEN"),
            oauth_scope=os.getenv("SKYFI_OAUTH_SCOPE"),
            
            # API Key
            api_key=os.getenv("SKYFI_API_KEY"),
            
            # Personal Access Token
            personal_token=os.getenv("SKYFI_PERSONAL_TOKEN"),
            
            # Network
            ssl_verify=get_env_bool("SKYFI_SSL_VERIFY", True),
            timeout=get_env_int("SKYFI_TIMEOUT", 30),
            max_retries=get_env_int("SKYFI_MAX_RETRIES", 3),
            
            # Service-specific
            default_workspace=os.getenv("SKYFI_DEFAULT_WORKSPACE"),
            rate_limit=get_env_int("SKYFI_RATE_LIMIT") or None,
            
            # Filtering
            allowed_projects=get_env_list("SKYFI_ALLOWED_PROJECTS"),
            custom_headers=custom_headers,
            
            # Feature toggles
            enable_webhooks=get_env_bool("SKYFI_ENABLE_WEBHOOKS", True),
            enable_ordering=get_env_bool("SKYFI_ENABLE_ORDERING", True),
            enable_open_data=get_env_bool("SKYFI_ENABLE_OPEN_DATA", True),
            
            # Caching
            cache_enabled=get_env_bool("SKYFI_CACHE_ENABLED", True),
            cache_ttl=get_env_int("SKYFI_CACHE_TTL", 300),
        )

    def is_auth_configured(self) -> bool:
        """
        Check if any authentication method is properly configured.
        
        Returns:
            True if authentication is available, False otherwise
        """
        
        # OAuth 2.0 (most secure)
        if (self.oauth_client_id and self.oauth_client_secret and 
            (self.oauth_access_token or self._has_stored_tokens())):
            return True
        
        # API Key authentication (standard)
        if self.api_key:
            return True
        
        # Personal Access Token (enterprise)
        if self.personal_token:
            return True
        
        return False

    def get_auth_method(self) -> str:
        """
        Determine the best available authentication method.
        
        Returns:
            Authentication method name ("oauth", "api_key", "personal_token", "none")
        """
        if (self.oauth_client_id and self.oauth_client_secret):
            return "oauth"
        elif self.api_key:
            return "api_key"
        elif self.personal_token:
            return "personal_token"
        else:
            return "none"

    def get_effective_headers(self) -> Dict[str, str]:
        """
        Get effective HTTP headers including custom headers and user agent.
        
        Returns:
            Dictionary of HTTP headers to include with requests
        """
        headers = {
            "User-Agent": "SkyFi-MCP-Server/1.0.0",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        # Add custom headers
        if self.custom_headers:
            headers.update(self.custom_headers)
        
        return headers

    def get_auth_headers(self, user_token: Optional[str] = None) -> Dict[str, str]:
        """
        Get authentication headers based on configuration and user context.
        
        Args:
            user_token: Per-request authentication token (overrides config)
            
        Returns:
            Dictionary of authentication headers
        """
        headers = {}
        
        # User-provided token takes precedence
        if user_token:
            headers["X-Skyfi-Api-Key"] = user_token
            return headers
        
        # Use configured authentication
        auth_method = self.get_auth_method()
        
        if auth_method == "oauth" and self.oauth_access_token:
            headers["Authorization"] = f"Bearer {self.oauth_access_token}"
        elif auth_method == "api_key" and self.api_key:
            headers["X-Skyfi-Api-Key"] = self.api_key
        elif auth_method == "personal_token" and self.personal_token:
            headers["Authorization"] = f"Bearer {self.personal_token}"
        
        return headers

    def _has_stored_tokens(self) -> bool:
        """
        Check if OAuth tokens are stored securely.
        
        This would integrate with a secure token storage system
        in a production environment.
        
        Returns:
            True if tokens are available in secure storage
        """
        # TODO: Implement secure token storage integration
        return False

    def validate_config(self) -> List[str]:
        """
        Validate the current configuration and return any issues.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Check required fields
        if not self.url:
            errors.append("API URL is required")
        
        # Validate URL format
        if self.url and not (self.url.startswith("http://") or self.url.startswith("https://")):
            errors.append("API URL must be a valid HTTP(S) URL")
        
        # Check authentication
        if not self.is_auth_configured():
            errors.append("No authentication method configured")
        
        # Validate numeric fields
        if self.timeout <= 0:
            errors.append("Timeout must be greater than 0")
        
        if self.max_retries < 0:
            errors.append("Max retries cannot be negative")
        
        if self.rate_limit and self.rate_limit <= 0:
            errors.append("Rate limit must be greater than 0")
        
        if self.cache_ttl <= 0:
            errors.append("Cache TTL must be greater than 0")
        
        return errors

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary for debugging/logging.
        
        Note: Sensitive values (tokens, keys) are masked.
        
        Returns:
            Dictionary representation with masked sensitive data
        """
        def mask_sensitive(value: Optional[str]) -> Optional[str]:
            if not value:
                return None
            if len(value) <= 8:
                return "***"
            return f"{value[:4]}...{value[-4:]}"
        
        return {
            "url": self.url,
            "auth_method": self.get_auth_method(),
            "oauth_client_id": mask_sensitive(self.oauth_client_id),
            "oauth_client_secret": "***" if self.oauth_client_secret else None,
            "oauth_access_token": mask_sensitive(self.oauth_access_token),
            "api_key": mask_sensitive(self.api_key),
            "personal_token": mask_sensitive(self.personal_token),
            "ssl_verify": self.ssl_verify,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "default_workspace": self.default_workspace,
            "rate_limit": self.rate_limit,
            "allowed_projects": len(self.allowed_projects) if self.allowed_projects else None,
            "custom_headers": len(self.custom_headers) if self.custom_headers else None,
            "features": {
                "webhooks": self.enable_webhooks,
                "ordering": self.enable_ordering,
                "open_data": self.enable_open_data
            },
            "cache": {
                "enabled": self.cache_enabled,
                "ttl": self.cache_ttl
            }
        }

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"SkyFiConfig(url={self.url}, auth={self.get_auth_method()}, "
            f"features={sum([self.enable_webhooks, self.enable_ordering, self.enable_open_data])})"
        )