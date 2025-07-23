# SkyFi MCP Server - Modular Service Layer Architecture

## Overview

This document defines the comprehensive service layer architecture for the SkyFi MCP server, following enterprise-ready patterns with clear separation of concerns, modular services, and scalable authentication strategies.

## 1. Service Architecture Foundation

### 1.1 Core Architecture Principles

**Enterprise-First, Developer-Friendly Philosophy**
- Support both simple API key auth AND complex OAuth 2.0/SAML flows
- Enable single-service setup AND multi-tenant deployments  
- Provide basic STDIO usage AND advanced HTTP transports
- Offer simple Docker run AND complex Kubernetes deployments

**Strict Layering with Clear Boundaries**
```
┌─────────────────────────────────────┐
│ MCP Transport Layer                 │ ← Protocol handling (STDIO, SSE, HTTP)
├─────────────────────────────────────┤
│ FastMCP Server Layer               │ ← Framework integration & tool filtering
├─────────────────────────────────────┤
│ Service Layer                       │ ← Business logic for each target service
├─────────────────────────────────────┤
│ Data Processing Layer              │ ← Model transformation & validation
├─────────────────────────────────────┤
│ Authentication Layer               │ ← Multi-method security handling
├─────────────────────────────────────┤
│ Network Layer                      │ ← HTTP clients & external API management
└─────────────────────────────────────┘
```

### 1.2 Project Structure Template

```
src/
├── mcp_skyfi/
│   ├── __init__.py                 # CLI entry point
│   ├── exceptions.py               # Custom exceptions
│   ├── servers/
│   │   ├── __init__.py
│   │   ├── main.py                 # Main server class
│   │   ├── context.py              # Application context
│   │   └── dependencies.py         # Dependency injection
│   ├── skyfi/                      # SkyFi service module
│   │   ├── __init__.py
│   │   ├── client.py               # Service client
│   │   ├── config.py               # Service configuration
│   │   ├── constants.py            # Service constants
│   │   ├── archives.py             # Archive search & retrieval
│   │   ├── orders.py               # Order creation & management
│   │   ├── notifications.py        # Notification management
│   │   ├── feasibility.py          # Feasibility checking
│   │   ├── pricing.py              # Pricing information
│   │   └── utils.py                # Service utilities
│   ├── osm/                        # OpenStreetMap service module
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── config.py
│   │   ├── geocoding.py            # Address geocoding
│   │   ├── places.py               # POI search
│   │   ├── geometry.py             # AOI generation
│   │   └── utils.py
│   ├── weather/                    # Weather service module
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── config.py
│   │   ├── current.py              # Current weather data
│   │   ├── forecast.py             # Weather forecasting
│   │   ├── historical.py           # Historical weather
│   │   └── utils.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py                 # Base model classes
│   │   ├── constants.py            # Shared constants
│   │   ├── skyfi/                  # SkyFi models
│   │   ├── osm/                    # OSM models
│   │   └── weather/                # Weather models
│   ├── preprocessing/
│   │   ├── __init__.py
│   │   ├── base.py                 # Base preprocessors
│   │   ├── skyfi.py                # SkyFi preprocessing
│   │   ├── osm.py                  # OSM preprocessing
│   │   └── weather.py              # Weather preprocessing
│   └── utils/
│       ├── __init__.py
│       ├── auth.py                 # Authentication utilities
│       ├── environment.py          # Environment handling
│       ├── logging.py              # Logging setup
│       ├── networking.py           # HTTP client utilities
│       └── tools.py                # Tool utilities
```

## 2. Service Configuration Class Patterns

### 2.1 Base Configuration Pattern

```python
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional
from ..utils.environment import get_env_bool, get_env_list

@dataclass
class BaseServiceConfig:
    """Base configuration class with common patterns."""
    
    # Required configuration
    url: str
    
    # Authentication methods (in order of precedence)
    # OAuth 2.0 (highest priority if configured)
    oauth_client_id: Optional[str] = None
    oauth_client_secret: Optional[str] = None  
    oauth_access_token: Optional[str] = None
    oauth_refresh_token: Optional[str] = None
    oauth_scope: Optional[str] = None
    
    # API Token/Key authentication
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    username: Optional[str] = None
    
    # Personal Access Token (for enterprise/self-hosted)
    personal_token: Optional[str] = None
    
    # Network configuration
    ssl_verify: bool = True
    timeout: int = 30
    max_retries: int = 3
    
    # Filtering and access control
    custom_headers: Optional[dict[str, str]] = None

    def is_auth_configured(self) -> bool:
        """Check if any authentication method is properly configured."""
        
        # OAuth 2.0 (most secure)
        if (self.oauth_client_id and self.oauth_client_secret and 
            (self.oauth_access_token or self._has_stored_tokens())):
            return True
        
        # API Key authentication
        if self.api_key:
            return True
        
        # Personal Access Token
        if self.personal_token:
            return True
        
        return False

    def get_auth_method(self) -> str:
        """Determine the best available authentication method."""
        if (self.oauth_client_id and self.oauth_client_secret):
            return "oauth"
        elif self.api_key:
            return "api_key"
        elif self.personal_token:
            return "personal_token"
        else:
            return "none"

    def _has_stored_tokens(self) -> bool:
        """Check if OAuth tokens are stored securely."""
        return False  # Implementation depends on token storage strategy
```

### 2.2 SkyFi Service Configuration

```python
@dataclass
class SkyFiConfig(BaseServiceConfig):
    """Configuration for SkyFi API service integration."""
    
    # SkyFi-specific settings
    default_page_size: int = 20
    max_page_size: int = 100
    cache_ttl_seconds: int = 300
    rate_limit_requests: int = 100
    rate_limit_window: int = 60
    
    # Service-specific filtering
    allowed_order_types: Optional[list[str]] = None
    max_order_cost: Optional[float] = None
    default_delivery_driver: str = "S3"

    @classmethod
    def from_env(cls) -> SkyFiConfig:
        """Create configuration from environment variables."""
        
        # Parse custom headers
        custom_headers = {}
        headers_str = os.getenv("SKYFI_CUSTOM_HEADERS", "")
        if headers_str:
            for header_pair in headers_str.split(","):
                if "=" in header_pair:
                    key, value = header_pair.strip().split("=", 1)
                    custom_headers[key] = value

        return cls(
            # Base configuration
            url=os.getenv("SKYFI_URL", "https://app.skyfi.com/platform-api"),
            
            # Authentication
            api_key=os.getenv("SKYFI_API_KEY"),
            oauth_client_id=os.getenv("SKYFI_OAUTH_CLIENT_ID"),
            oauth_client_secret=os.getenv("SKYFI_OAUTH_CLIENT_SECRET"),
            oauth_access_token=os.getenv("SKYFI_OAUTH_ACCESS_TOKEN"),
            personal_token=os.getenv("SKYFI_PERSONAL_TOKEN"),
            
            # Network
            ssl_verify=get_env_bool("SKYFI_SSL_VERIFY", True),
            timeout=int(os.getenv("SKYFI_TIMEOUT", "30")),
            max_retries=int(os.getenv("SKYFI_MAX_RETRIES", "3")),
            
            # Service-specific
            default_page_size=int(os.getenv("SKYFI_DEFAULT_PAGE_SIZE", "20")),
            max_page_size=int(os.getenv("SKYFI_MAX_PAGE_SIZE", "100")),
            cache_ttl_seconds=int(os.getenv("SKYFI_CACHE_TTL", "300")),
            rate_limit_requests=int(os.getenv("SKYFI_RATE_LIMIT_REQUESTS", "100")),
            max_order_cost=float(os.getenv("SKYFI_MAX_ORDER_COST", "0")) or None,
            
            # Filtering
            allowed_order_types=get_env_list("SKYFI_ALLOWED_ORDER_TYPES"),
            custom_headers=custom_headers or None,
        )

    def is_auth_configured(self) -> bool:
        """SkyFi requires at minimum an API key."""
        return bool(self.api_key or self.oauth_access_token or self.personal_token)
```

### 2.3 OSM Service Configuration

```python
@dataclass
class OSMConfig(BaseServiceConfig):
    """Configuration for OpenStreetMap service integration."""
    
    # OSM-specific settings
    nominatim_url: str = "https://nominatim.openstreetmap.org"
    overpass_url: str = "https://overpass-api.de/api/interpreter"
    user_agent: str = "SkyFi-MCP-Server/1.0"
    
    # Rate limiting (respect OSM usage policy)
    rate_limit_delay: float = 1.0  # 1 second between requests
    max_results_per_query: int = 50
    
    # Caching configuration
    geocode_cache_ttl: int = 3600  # 1 hour
    poi_cache_ttl: int = 1800     # 30 minutes

    @classmethod
    def from_env(cls) -> OSMConfig:
        """Create configuration from environment variables."""
        return cls(
            url=os.getenv("OSM_NOMINATIM_URL", "https://nominatim.openstreetmap.org"),
            nominatim_url=os.getenv("OSM_NOMINATIM_URL", "https://nominatim.openstreetmap.org"),
            overpass_url=os.getenv("OSM_OVERPASS_URL", "https://overpass-api.de/api/interpreter"),
            user_agent=os.getenv("OSM_USER_AGENT", "SkyFi-MCP-Server/1.0"),
            
            # Network
            ssl_verify=get_env_bool("OSM_SSL_VERIFY", True),
            timeout=int(os.getenv("OSM_TIMEOUT", "30")),
            max_retries=int(os.getenv("OSM_MAX_RETRIES", "3")),
            
            # Service-specific
            rate_limit_delay=float(os.getenv("OSM_RATE_LIMIT_DELAY", "1.0")),
            max_results_per_query=int(os.getenv("OSM_MAX_RESULTS", "50")),
            geocode_cache_ttl=int(os.getenv("OSM_GEOCODE_CACHE_TTL", "3600")),
            poi_cache_ttl=int(os.getenv("OSM_POI_CACHE_TTL", "1800")),
        )

    def is_auth_configured(self) -> bool:
        """OSM services typically don't require authentication."""
        return bool(self.url and self.nominatim_url)
```

## 3. Service Client Implementation

### 3.1 Base Service Client Pattern

```python
from __future__ import annotations

import logging
from typing import Any, Optional
import httpx
from cachetools import TTLCache
from ..exceptions import BaseAPIError, BaseAuthenticationError
from ..utils.networking import create_http_client, handle_http_error

logger = logging.getLogger("mcp-skyfi.base.client")

class BaseServiceClient:
    """Base HTTP client with authentication and error handling."""
    
    def __init__(self, config: BaseServiceConfig, user_context: Optional[dict] = None):
        self.config = config
        self.user_context = user_context or {}
        self._client: Optional[httpx.AsyncClient] = None
        self._auth_cache = TTLCache(maxsize=100, ttl=300)  # 5-minute cache
        
    async def __aenter__(self) -> BaseServiceClient:
        """Async context manager entry."""
        await self._ensure_client()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            
    async def _ensure_client(self) -> None:
        """Ensure HTTP client is initialized with proper authentication."""
        if self._client:
            return
            
        # Determine authentication method
        auth_method = self._get_auth_method()
        headers = await self._build_auth_headers(auth_method)
        
        # Create HTTP client with connection pooling
        self._client = create_http_client(
            base_url=self.config.url,
            headers=headers,
            timeout=self.config.timeout,
            verify=self.config.ssl_verify,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
        )
        
    def _get_auth_method(self) -> str:
        """Determine authentication method based on user context and config."""
        # Check user-provided authentication first
        if self.user_context.get("auth_token"):
            return self.user_context.get("auth_type", "bearer")
        
        # Fall back to server configuration
        return self.config.get_auth_method()
        
    async def _build_auth_headers(self, auth_method: str) -> dict[str, str]:
        """Build authentication headers based on method."""
        headers = {"User-Agent": "SkyFi-MCP-Server/1.0"}
        
        # Add custom headers
        if self.config.custom_headers:
            headers.update(self.config.custom_headers)
            
        # Add authentication
        if auth_method == "oauth":
            token = self.user_context.get("auth_token") or self.config.oauth_access_token
            if token:
                headers["Authorization"] = f"Bearer {token}"
        elif auth_method == "api_key":
            if self.config.api_key:
                headers["X-API-Key"] = self.config.api_key
        elif auth_method == "personal_token":
            token = self.user_context.get("auth_token") or self.config.personal_token
            if token:
                headers["Authorization"] = f"Bearer {token}"
                
        return headers
        
    async def request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[dict] = None,
        data: Optional[dict] = None,
        json: Optional[dict] = None
    ) -> dict[str, Any]:
        """Make authenticated HTTP request with error handling and retries."""
        await self._ensure_client()
        
        url = endpoint if endpoint.startswith("http") else f"{self.config.url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        for attempt in range(self.config.max_retries + 1):
            try:
                response = await self._client.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    json=json
                )
                
                # Handle HTTP errors
                if response.status_code >= 400:
                    await handle_http_error(response, BaseAPIError, BaseAuthenticationError)
                
                # Parse JSON response
                return response.json()
                
            except httpx.TimeoutException:
                if attempt == self.config.max_retries:
                    raise BaseAPIError(f"Request timeout after {self.config.max_retries} retries")
                logger.warning(f"Request timeout, retrying ({attempt + 1}/{self.config.max_retries})")
                
            except httpx.RequestError as e:
                if attempt == self.config.max_retries:
                    raise BaseAPIError(f"Request failed: {str(e)}")
                logger.warning(f"Request error, retrying ({attempt + 1}/{self.config.max_retries}): {e}")
```

### 3.2 SkyFi Service Client

```python
from .config import SkyFiConfig
from ..exceptions import SkyFiAPIError, SkyFiAuthenticationError

class SkyFiClient(BaseServiceClient):
    """HTTP client for SkyFi API with specific authentication handling."""
    
    def __init__(self, config: SkyFiConfig, user_context: Optional[dict] = None):
        super().__init__(config, user_context)
        self.config: SkyFiConfig = config
        
    async def _build_auth_headers(self, auth_method: str) -> dict[str, str]:
        """Build SkyFi-specific authentication headers."""
        headers = await super()._build_auth_headers(auth_method)
        
        # SkyFi uses X-Skyfi-Api-Key header
        if auth_method == "api_key" and self.config.api_key:
            headers["X-Skyfi-Api-Key"] = self.config.api_key
            # Remove generic X-API-Key if present
            headers.pop("X-API-Key", None)
            
        return headers
    
    async def get_user_info(self) -> dict[str, Any]:
        """Get current user information and budget status."""
        return await self.request("GET", "/auth/whoami")
    
    async def search_archives(self, **params) -> dict[str, Any]:
        """Search satellite imagery archives."""
        return await self.request("GET", "/archives", params=params)
    
    async def create_archive_order(self, order_data: dict) -> dict[str, Any]:
        """Create a new archive order."""
        return await self.request("POST", "/orders", json=order_data)
    
    async def get_order_status(self, order_id: str) -> dict[str, Any]:
        """Get order status and details."""
        return await self.request("GET", f"/orders/{order_id}")
    
    async def get_pricing(self) -> dict[str, Any]:
        """Get current pricing information."""
        return await self.request("GET", "/pricing")
```

## 4. Tool Organization by Feature Domains

### 4.1 Feature Domain Structure

**✅ CORRECT: Feature-domain organization**
```
skyfi/
├── archives.py          # archive_search, archive_get_details, archive_get_thumbnail
├── orders.py            # order_create_archive, order_create_tasking, order_get_status, order_list
├── notifications.py     # notification_create, notification_list, notification_delete
├── feasibility.py       # feasibility_check, feasibility_get_passes
├── pricing.py           # pricing_get, pricing_calculate_cost
└── auth.py             # auth_get_user_info, auth_verify_key

osm/
├── geocoding.py        # geocode_address, geocode_reverse
├── places.py           # places_search_pois, places_get_details
├── geometry.py         # geometry_generate_aoi, geometry_calculate_area
└── routing.py          # routing_get_directions, routing_calculate_distance

weather/
├── current.py          # weather_get_current
├── forecast.py         # weather_get_forecast
└── historical.py       # weather_get_historical
```

### 4.2 Tool Definition Standards

```python
from fastmcp import FastMCP
from typing import Annotated
from contextlib import asynccontextmanager

# Service-specific MCP instance
skyfi_mcp = FastMCP("SkyFi Tools")

@skyfi_mcp.tool(
    name="skyfi_archive_search",
    description="Search satellite imagery archives in SkyFi platform",
    tags=["skyfi", "read", "archives", "search"]
)
def archive_search_tool(
    # Required parameters first
    aoi: Annotated[str, "WKT polygon defining area of interest. Example: 'POLYGON((-97.7 30.3, -97.7 30.2, -97.6 30.2, -97.6 30.3, -97.7 30.3))'"],
    
    # Optional parameters with defaults
    from_date: Annotated[str | None, "Start date for search in ISO format (YYYY-MM-DDTHH:MM:SSZ)"] = None,
    to_date: Annotated[str | None, "End date for search in ISO format (YYYY-MM-DDTHH:MM:SSZ)"] = None,
    max_cloud_coverage: Annotated[int | None, "Maximum cloud coverage percentage (0-100)"] = None,
    resolutions: Annotated[list[str] | None, "List of resolutions: LOW, MEDIUM, HIGH, VERY_HIGH, SUPER_HIGH, ULTRA_HIGH"] = None,
    product_types: Annotated[list[str] | None, "List of product types: DAY, NIGHT, VIDEO, MULTISPECTRAL, SAR"] = None,
    open_data: Annotated[bool | None, "Filter for free open data only"] = None,
    page_size: Annotated[int | None, "Number of results per page (1-100)"] = 20,
    
    # Context injection (always last)
    context: Annotated[SkyFiContext, Context]
) -> str:
    """
    Search for satellite imagery archives in the SkyFi platform.
    
    This tool searches the SkyFi archive database for satellite imagery matching
    the specified criteria. Results include metadata, pricing, and availability
    information for each matching archive.
    
    Args:
        aoi: WKT polygon defining the area of interest
        from_date: Optional start date filter
        to_date: Optional end date filter  
        max_cloud_coverage: Optional cloud coverage filter (0-100%)
        resolutions: Optional list of desired resolutions
        product_types: Optional list of desired product types
        open_data: Optional filter for free Sentinel-2 and other open data
        page_size: Number of results per page
        
    Returns:
        Formatted string with archive list including:
        - Archive ID and basic metadata
        - Capture date and quality metrics
        - Pricing information per square km
        - Thumbnail URLs and download options
        
    Raises:
        MCPError: If AOI is invalid, authentication fails, or search fails
    """
    try:
        # Validate inputs
        if not aoi or not aoi.strip():
            raise ValueError("AOI cannot be empty")
        
        if not _is_valid_wkt_polygon(aoi):
            raise ValueError("AOI must be a valid WKT polygon")
        
        # Check read-only mode (not applicable for read operations)
        
        # Execute search
        async with context.skyfi_client as client:
            search_params = {
                "aoi": aoi,
                "pageSize": page_size
            }
            
            # Add optional parameters
            if from_date:
                search_params["fromDate"] = from_date
            if to_date:
                search_params["toDate"] = to_date  
            if max_cloud_coverage is not None:
                search_params["maxCloudCoveragePercent"] = max_cloud_coverage
            if resolutions:
                search_params["resolutions"] = resolutions
            if product_types:
                search_params["productTypes"] = product_types
            if open_data is not None:
                search_params["openData"] = open_data
            
            result = await client.search_archives(**search_params)
        
        # Format response
        return format_archive_search_response(result)
        
    except SkyFiAuthenticationError:
        raise MCPError("Authentication failed. Check your SkyFi API key.")
    except SkyFiNotFoundError:
        raise MCPError("No archives found matching the specified criteria.")
    except SkyFiPermissionError:
        raise MCPError("Insufficient permissions for archive search.")
    except Exception as e:
        logger.error(f"Unexpected error in archive_search_tool: {e}", exc_info=True)
        raise MCPError(f"Failed to search archives: {str(e)}")
```

## 5. Service Mounting and Dependency Injection

### 5.1 Main Server Class with Service Mounting

```python
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextual import asynccontextmanager
from typing import Any, Literal, Optional

from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware import Middleware

from .context import MainAppContext
from .dependencies import get_available_services, is_read_only_mode
from ..skyfi import skyfi_mcp
from ..osm import osm_mcp
from ..weather import weather_mcp

logger = logging.getLogger("mcp-skyfi.server.main")

class SkyFiMCP(FastMCP[MainAppContext]):
    """Custom FastMCP server class with multi-service support and tool filtering."""

    async def _mcp_list_tools(self) -> list[MCPTool]:
        """Override FastMCP's tool discovery with custom filtering logic."""
        # Get application context
        req_context = self._mcp_server.request_context
        if req_context is None or req_context.lifespan_context is None:
            logger.warning("Lifespan context not available during tool list")
            return []

        app_context = req_context.lifespan_context.get("app_lifespan_context")
        if not app_context:
            return []

        # Apply multi-level filtering
        all_tools = await self.get_tools()
        filtered_tools = []

        for tool_name, tool_obj in all_tools.items():
            if self._should_include_tool(tool_name, tool_obj, app_context):
                filtered_tools.append(tool_obj.to_mcp_tool(name=tool_name))

        return filtered_tools

    def _should_include_tool(self, tool_name: str, tool_obj: Any, context: MainAppContext) -> bool:
        """Multi-level tool filtering logic."""
        # 1. Enabled tools filter
        if context.enabled_tools and tool_name not in context.enabled_tools:
            return False

        # 2. Read-only mode filter
        if context.read_only and "write" in tool_obj.tags:
            return False

        # 3. Service availability filter
        tool_tags = tool_obj.tags
        if "skyfi" in tool_tags and not context.skyfi_config:
            return False
        if "osm" in tool_tags and not context.osm_config:
            return False
        if "weather" in tool_tags and not context.weather_config:
            return False

        return True

@asynccontextmanager
async def main_lifespan(app: FastMCP[MainAppContext]) -> AsyncIterator[dict]:
    """Server lifespan management with service configuration loading."""
    logger.info("SkyFi MCP server lifespan starting...")
    
    # Load and validate service configurations
    services = get_available_services()
    service_configs = {}
    
    # SkyFi configuration
    if services.get("skyfi"):
        try:
            from ..skyfi.config import SkyFiConfig
            config = SkyFiConfig.from_env()
            if config.is_auth_configured():
                service_configs["skyfi_config"] = config
                logger.info("SkyFi configuration loaded successfully")
            else:
                logger.warning("SkyFi URL found but API key not configured")
        except Exception as e:
            logger.error(f"Failed to load SkyFi configuration: {e}")

    # OSM configuration
    if services.get("osm"):
        try:
            from ..osm.config import OSMConfig
            config = OSMConfig.from_env()
            if config.is_auth_configured():
                service_configs["osm_config"] = config
                logger.info("OSM configuration loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load OSM configuration: {e}")

    # Weather configuration
    if services.get("weather"):
        try:
            from ..weather.config import WeatherConfig
            config = WeatherConfig.from_env()
            if config.is_auth_configured():
                service_configs["weather_config"] = config
                logger.info("Weather configuration loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Weather configuration: {e}")

    # Create application context
    app_context = MainAppContext(
        read_only=is_read_only_mode(),
        enabled_tools=get_enabled_tools(),
        **service_configs
    )

    try:
        yield {"app_lifespan_context": app_context}
    finally:
        logger.info("SkyFi MCP server lifespan shutting down...")

# Initialize main server with service mounting
main_mcp = SkyFiMCP(name="SkyFi MCP Server", lifespan=main_lifespan)

# Mount service modules
main_mcp.mount("skyfi", skyfi_mcp)
main_mcp.mount("osm", osm_mcp)
main_mcp.mount("weather", weather_mcp)

# Add health check endpoint
@main_mcp.custom_route("/healthz", methods=["GET"], include_in_schema=False)
async def health_check(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "services": ["skyfi", "osm", "weather"]})
```

### 5.2 Application Context Pattern

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..skyfi.config import SkyFiConfig
from ..skyfi.client import SkyFiClient
from ..osm.config import OSMConfig  
from ..osm.client import OSMClient
from ..weather.config import WeatherConfig
from ..weather.client import WeatherClient

@dataclass
class MainAppContext:
    """Main application context with service configurations and clients."""
    
    # Global settings
    read_only: bool = False
    enabled_tools: Optional[set[str]] = None
    
    # Service configurations
    skyfi_config: Optional[SkyFiConfig] = None
    osm_config: Optional[OSMConfig] = None
    weather_config: Optional[WeatherConfig] = None
    
    def __post_init__(self):
        """Initialize service clients after configuration."""
        self._skyfi_client: Optional[SkyFiClient] = None
        self._osm_client: Optional[OSMClient] = None
        self._weather_client: Optional[WeatherClient] = None
    
    @property
    def skyfi_client(self) -> SkyFiClient:
        """Get or create SkyFi client instance."""
        if not self.skyfi_config:
            raise ValueError("SkyFi configuration not available")
        
        if not self._skyfi_client:
            self._skyfi_client = SkyFiClient(self.skyfi_config)
        
        return self._skyfi_client
    
    @property  
    def osm_client(self) -> OSMClient:
        """Get or create OSM client instance."""
        if not self.osm_config:
            raise ValueError("OSM configuration not available")
        
        if not self._osm_client:
            self._osm_client = OSMClient(self.osm_config)
        
        return self._osm_client
    
    @property
    def weather_client(self) -> WeatherClient:
        """Get or create Weather client instance."""  
        if not self.weather_config:
            raise ValueError("Weather configuration not available")
        
        if not self._weather_client:
            self._weather_client = WeatherClient(self.weather_config)
        
        return self._weather_client
```

### 5.3 Dependency Injection Utilities

```python
import os
from typing import Dict, Optional, Set

def get_available_services() -> Dict[str, bool]:
    """Determine which services are configured via environment variables."""
    services = {}
    
    # Check SkyFi
    services["skyfi"] = bool(
        os.getenv("SKYFI_URL") or 
        os.getenv("SKYFI_API_KEY")
    )
    
    # Check OSM (always available as it doesn't require auth)
    services["osm"] = bool(
        os.getenv("OSM_NOMINATIM_URL") or 
        True  # Default OSM endpoints
    )
    
    # Check Weather service
    services["weather"] = bool(
        os.getenv("WEATHER_API_KEY") or
        os.getenv("WEATHER_URL")
    )
    
    return services

def is_read_only_mode() -> bool:
    """Check if server should run in read-only mode."""
    return os.getenv("READ_ONLY_MODE", "false").lower() in ("true", "1", "yes")

def get_enabled_tools() -> Optional[Set[str]]:
    """Get set of explicitly enabled tools."""
    tools_str = os.getenv("ENABLED_TOOLS")
    if not tools_str:
        return None
    
    return set(tool.strip() for tool in tools_str.split(",") if tool.strip())

def get_service_config_class(service_name: str):
    """Get configuration class for a service."""
    config_classes = {
        "skyfi": "mcp_skyfi.skyfi.config.SkyFiConfig",
        "osm": "mcp_skyfi.osm.config.OSMConfig", 
        "weather": "mcp_skyfi.weather.config.WeatherConfig"
    }
    
    class_path = config_classes.get(service_name)
    if not class_path:
        raise ValueError(f"Unknown service: {service_name}")
    
    module_path, class_name = class_path.rsplit(".", 1)
    module = __import__(module_path, fromlist=[class_name])
    return getattr(module, class_name)
```

## 6. Authentication Layer Design

### 6.1 Multi-Method Authentication Strategy

```python
from enum import Enum
from typing import Optional, Dict, Any

class AuthenticationMethod(Enum):
    """Standard authentication methods for MCP servers."""
    
    # OAuth 2.0 (Most Secure - for Cloud/SaaS)
    OAUTH2_AUTHORIZATION_CODE = "oauth2_auth_code"
    OAUTH2_CLIENT_CREDENTIALS = "oauth2_client_creds"  
    OAUTH2_BYOT = "oauth2_byot"  # Bring Your Own Token
    
    # API Key/Token (Standard - for Cloud/SaaS)
    API_KEY_HEADER = "api_key_header"
    API_TOKEN_USERNAME = "api_token_username"
    
    # Personal Access Token (Enterprise - for Self-Hosted)
    PERSONAL_ACCESS_TOKEN = "personal_token"
    
    # Basic Authentication (Legacy - for Self-Hosted)
    BASIC_AUTH = "basic_auth"
    
    # No Authentication
    NONE = "none"

def determine_auth_method(config: BaseServiceConfig, user_context: Dict[str, Any]) -> AuthenticationMethod:
    """Determine authentication method with clear precedence rules."""
    
    # 1. Per-request authentication (highest priority)
    if user_context.get("auth_token"):
        auth_type = user_context.get("auth_type", "bearer")
        if auth_type == "oauth" or auth_type == "bearer":
            return AuthenticationMethod.OAUTH2_BYOT
        elif auth_type == "api_key":
            return AuthenticationMethod.API_KEY_HEADER
    
    # 2. OAuth 2.0 (server-configured)
    if config.oauth_client_id and config.oauth_client_secret:
        if config.oauth_access_token:
            return AuthenticationMethod.OAUTH2_AUTHORIZATION_CODE
        else:
            return AuthenticationMethod.OAUTH2_CLIENT_CREDENTIALS
    
    # 3. API Key/Token
    if config.api_key:
        return AuthenticationMethod.API_KEY_HEADER
    
    # 4. Personal Access Token
    if config.personal_token:
        return AuthenticationMethod.PERSONAL_ACCESS_TOKEN
    
    # 5. No authentication
    return AuthenticationMethod.NONE
```

### 6.2 Authentication Middleware

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class UserTokenMiddleware(BaseHTTPMiddleware):
    """Extract and validate per-request authentication tokens."""
    
    CUSTOM_AUTH_HEADERS = {
        "X-Skyfi-Api-Key": "api_key",
        "X-Weather-Api-Key": "api_key", 
        "X-API-Key": "api_key",
        "Authorization": "bearer"
    }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Extract authentication from request headers."""
        
        # Extract authentication headers
        auth_header = request.headers.get("Authorization", "")
        
        # Parse Bearer tokens (OAuth/PAT)
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            request.state.user_auth_token = token
            request.state.user_auth_type = "bearer"
            
        # Parse custom service headers  
        else:
            for header_name, auth_type in self.CUSTOM_AUTH_HEADERS.items():
                if header_value := request.headers.get(header_name):
                    request.state.user_auth_token = header_value
                    request.state.user_auth_type = auth_type
                    break
        
        return await call_next(request)
```

This comprehensive service layer architecture provides:

1. **Modular Service Design** - Each service (SkyFi, OSM, Weather) is completely independent
2. **Flexible Configuration** - Environment-based configuration with multiple authentication methods
3. **Connection Pooling** - Efficient HTTP client management with proper resource handling
4. **Feature-Domain Organization** - Tools organized by business functionality, not CRUD operations
5. **Dependency Injection** - Clean separation of concerns with proper context management
6. **Multi-Method Authentication** - Support for OAuth, API keys, and personal tokens with clear precedence
7. **Tool Filtering** - Dynamic tool availability based on configuration and read-only mode
8. **Error Handling** - Comprehensive error handling with meaningful user feedback

The architecture follows enterprise patterns while maintaining simplicity for basic use cases, enabling both single-service deployments and complex multi-tenant scenarios.