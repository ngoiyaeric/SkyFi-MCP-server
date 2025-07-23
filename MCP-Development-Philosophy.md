# The Scalable MCP Server Development Philosophy

## Overview

Based on reverse engineering the MCP Atlassian server architecture and documentation, this guide presents a comprehensive development philosophy for building production-ready, scalable MCP servers. The philosophy centers on **layered architecture**, **modular services**, **enterprise authentication**, and **exceptional user experience**.

## Core Development Philosophy

### 1. The Foundation Principle: "Enterprise-First, Developer-Friendly"

**Philosophy**: Build for enterprise scalability from day one, but maintain developer simplicity for basic use cases.

**Implementation Strategy**:
- Support both simple API key auth AND complex OAuth 2.0/SAML flows
- Provide single-service setup AND multi-tenant deployments
- Enable basic STDIO usage AND advanced HTTP transports
- Offer simple Docker run AND complex Kubernetes deployments

### 2. The Architecture Principle: "Strict Layering with Clear Boundaries"

**Philosophy**: Each layer should have a single responsibility and clear interfaces.

**Required Layers** (in order):
1. **MCP Transport Layer** - Protocol handling (STDIO, SSE, Streamable HTTP)
2. **FastMCP Server Layer** - Framework integration and tool filtering
3. **Service Layer** - Business logic for each target service
4. **Data Processing Layer** - Model transformation and validation
5. **Authentication Layer** - Multi-method security handling
6. **Network Layer** - HTTP clients and external API management

### 3. The Service Principle: "Independent, Mountable Modules"

**Philosophy**: Each target service should be completely independent and mountable.

**Service Module Requirements**:
- Dedicated configuration class with `from_env()` factory
- Independent authentication validation via `is_auth_configured()`
- Isolated client implementation with connection pooling
- Service-specific tool registration with consistent patterns
- Separate error handling and logging namespaces

## Development Framework Template

### 1. Project Structure Template

```
mcp-{service-name}/
├── src/
│   └── mcp_{service_name}/
│       ├── __init__.py                 # CLI entry point
│       ├── exceptions.py               # Custom exceptions
│       ├── servers/
│       │   ├── __init__.py
│       │   ├── main.py                 # Main server class
│       │   ├── context.py              # Application context
│       │   └── dependencies.py         # Dependency injection
│       ├── {service_a}/                # First service module
│       │   ├── __init__.py
│       │   ├── client.py               # Service client
│       │   ├── config.py               # Service configuration
│       │   ├── constants.py            # Service constants
│       │   ├── {feature_1}.py          # Feature-specific tools
│       │   ├── {feature_2}.py          # Feature-specific tools
│       │   └── utils.py                # Service utilities
│       ├── {service_b}/                # Second service module
│       │   └── [same structure]
│       ├── models/
│       │   ├── __init__.py
│       │   ├── base.py                 # Base model classes
│       │   ├── constants.py            # Shared constants
│       │   ├── {service_a}/            # Service A models
│       │   └── {service_b}/            # Service B models
│       ├── preprocessing/
│       │   ├── __init__.py
│       │   ├── base.py                 # Base preprocessors
│       │   ├── {service_a}.py          # Service A preprocessing
│       │   └── {service_b}.py          # Service B preprocessing
│       └── utils/
│           ├── __init__.py
│           ├── auth.py                 # Authentication utilities
│           ├── environment.py          # Environment handling
│           ├── logging.py              # Logging setup
│           ├── networking.py           # HTTP client utilities
│           └── tools.py                # Tool utilities
├── tests/                              # Comprehensive test suite
├── docs/                               # Micro-documentation
├── .env.example                        # Configuration template
├── Dockerfile                          # Container definition
├── pyproject.toml                      # Project configuration
└── README.md                           # User-focused documentation
```

### 2. Main Server Class Template

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
from .{service_a} import {service_a}_mcp
from .{service_b} import {service_b}_mcp

logger = logging.getLogger("mcp-{service-name}.server.main")

class {ServiceName}MCP(FastMCP[MainAppContext]):
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
        for service_name in ["{service_a}", "{service_b}"]:
            if service_name in tool_tags:
                service_config = getattr(context, f"full_{service_name}_config")
                if not service_config:
                    return False

        return True

    def http_app(
        self,
        path: str | None = None,
        middleware: list[Middleware] | None = None,
        transport: Literal["streamable-http", "sse"] = "streamable-http",
    ) -> Starlette:
        """Create HTTP app with custom middleware pipeline."""
        # Add authentication middleware
        auth_middleware = Middleware(UserTokenMiddleware, mcp_server_ref=self)
        final_middleware = [auth_middleware]
        
        if middleware:
            final_middleware.extend(middleware)

        return super().http_app(
            path=path,
            middleware=final_middleware,
            transport=transport
        )

@asynccontextmanager
async def main_lifespan(app: FastMCP[MainAppContext]) -> AsyncIterator[dict]:
    """Server lifespan management with service configuration loading."""
    logger.info("MCP {ServiceName} server lifespan starting...")
    
    # Load and validate service configurations
    services = get_available_services()
    service_configs = {}
    
    for service_name in ["{service_a}", "{service_b}"]:
        if services.get(service_name):
            try:
                config_class = get_config_class(service_name)
                config = config_class.from_env()
                if config.is_auth_configured():
                    service_configs[f"full_{service_name}_config"] = config
                    logger.info(f"{service_name.title()} configuration loaded successfully")
                else:
                    logger.warning(f"{service_name.title()} URL found but authentication incomplete")
            except Exception as e:
                logger.error(f"Failed to load {service_name} configuration: {e}")

    # Create application context
    app_context = MainAppContext(
        read_only=is_read_only_mode(),
        enabled_tools=get_enabled_tools(),
        **service_configs
    )

    try:
        yield {"app_lifespan_context": app_context}
    finally:
        logger.info("MCP {ServiceName} server lifespan shutting down...")

# Initialize main server with service mounting
main_mcp = {ServiceName}MCP(name="{ServiceName} MCP", lifespan=main_lifespan)
main_mcp.mount("{service_a}", {service_a}_mcp)
main_mcp.mount("{service_b}", {service_b}_mcp)

# Add health check endpoint
@main_mcp.custom_route("/healthz", methods=["GET"], include_in_schema=False)
async def health_check(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})
```

### 3. Service Configuration Template

```python
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from ..utils.environment import get_env_bool, get_env_list

@dataclass
class {ServiceName}Config:
    """Configuration for {ServiceName} service integration."""
    
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
    
    # Service-specific configuration
    default_workspace: Optional[str] = None
    rate_limit: Optional[int] = None
    
    # Filtering and access control
    allowed_projects: Optional[list[str]] = None
    custom_headers: Optional[dict[str, str]] = None

    @classmethod
    def from_env(cls) -> {ServiceName}Config:
        """Create configuration from environment variables."""
        
        # Parse custom headers
        custom_headers = {}
        headers_str = os.getenv("{SERVICE_NAME}_CUSTOM_HEADERS", "")
        if headers_str:
            for header_pair in headers_str.split(","):
                if "=" in header_pair:
                    key, value = header_pair.strip().split("=", 1)
                    custom_headers[key] = value

        return cls(
            # Required
            url=os.getenv("{SERVICE_NAME}_URL", ""),
            
            # OAuth 2.0
            oauth_client_id=os.getenv("{SERVICE_NAME}_OAUTH_CLIENT_ID"),
            oauth_client_secret=os.getenv("{SERVICE_NAME}_OAUTH_CLIENT_SECRET"),
            oauth_access_token=os.getenv("{SERVICE_NAME}_OAUTH_ACCESS_TOKEN"),
            oauth_refresh_token=os.getenv("{SERVICE_NAME}_OAUTH_REFRESH_TOKEN"),
            oauth_scope=os.getenv("{SERVICE_NAME}_OAUTH_SCOPE"),
            
            # API Key
            api_key=os.getenv("{SERVICE_NAME}_API_KEY"),
            api_secret=os.getenv("{SERVICE_NAME}_API_SECRET"),
            username=os.getenv("{SERVICE_NAME}_USERNAME"),
            
            # Personal Access Token
            personal_token=os.getenv("{SERVICE_NAME}_PERSONAL_TOKEN"),
            
            # Network
            ssl_verify=get_env_bool("{SERVICE_NAME}_SSL_VERIFY", True),
            timeout=int(os.getenv("{SERVICE_NAME}_TIMEOUT", "30")),
            max_retries=int(os.getenv("{SERVICE_NAME}_MAX_RETRIES", "3")),
            
            # Service-specific
            default_workspace=os.getenv("{SERVICE_NAME}_DEFAULT_WORKSPACE"),
            rate_limit=int(os.getenv("{SERVICE_NAME}_RATE_LIMIT", "0")) or None,
            
            # Filtering
            allowed_projects=get_env_list("{SERVICE_NAME}_ALLOWED_PROJECTS"),
            custom_headers=custom_headers or None,
        )

    def is_auth_configured(self) -> bool:
        """Check if any authentication method is properly configured."""
        
        # OAuth 2.0 (most secure)
        if (self.oauth_client_id and self.oauth_client_secret and 
            (self.oauth_access_token or self._has_stored_tokens())):
            return True
        
        # API Key authentication
        if self.api_key and (self.api_secret or self.username):
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
        # Implementation depends on token storage strategy
        return False
```

### 4. Service Client Template

```python
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx
from cachetools import TTLCache

from .config import {ServiceName}Config
from ..exceptions import {ServiceName}AuthenticationError, {ServiceName}APIError
from ..utils.networking import create_http_client, handle_http_error

logger = logging.getLogger("mcp-{service-name}.{service_name}.client")

class {ServiceName}Client:
    """HTTP client for {ServiceName} API with authentication and error handling."""
    
    def __init__(self, config: {ServiceName}Config, user_context: Optional[dict] = None):
        self.config = config
        self.user_context = user_context or {}
        self._client: Optional[httpx.AsyncClient] = None
        self._auth_cache = TTLCache(maxsize=100, ttl=300)  # 5-minute cache
        
    async def __aenter__(self) -> {ServiceName}Client:
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
        headers = {"User-Agent": "MCP-{ServiceName}/1.0"}
        
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
                if self.config.api_secret:
                    headers["X-API-Secret"] = self.config.api_secret
        elif auth_method == "personal_token":
            token = self.user_context.get("auth_token") or self.config.personal_token
            if token:
                headers["Authorization"] = f"Bearer {token}"
                
        return headers
        
    async def get(self, endpoint: str, params: Optional[dict] = None) -> dict[str, Any]:
        """Make authenticated GET request."""
        return await self._request("GET", endpoint, params=params)
        
    async def post(self, endpoint: str, data: Optional[dict] = None, json: Optional[dict] = None) -> dict[str, Any]:
        """Make authenticated POST request."""
        return await self._request("POST", endpoint, data=data, json=json)
        
    async def put(self, endpoint: str, data: Optional[dict] = None, json: Optional[dict] = None) -> dict[str, Any]:
        """Make authenticated PUT request."""  
        return await self._request("PUT", endpoint, data=data, json=json)
        
    async def delete(self, endpoint: str) -> dict[str, Any]:
        """Make authenticated DELETE request."""
        return await self._request("DELETE", endpoint)
        
    async def _request(
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
                    await handle_http_error(response, {ServiceName}APIError, {ServiceName}AuthenticationError)
                
                # Parse JSON response
                return response.json()
                
            except httpx.TimeoutException:
                if attempt == self.config.max_retries:
                    raise {ServiceName}APIError(f"Request timeout after {self.config.max_retries} retries")
                logger.warning(f"Request timeout, retrying ({attempt + 1}/{self.config.max_retries})")
                
            except httpx.RequestError as e:
                if attempt == self.config.max_retries:
                    raise {ServiceName}APIError(f"Request failed: {str(e)}")
                logger.warning(f"Request error, retrying ({attempt + 1}/{self.config.max_retries}): {e}")
```

## Authentication Architecture Philosophy

### 1. Multi-Method Authentication Pattern

**Implementation Requirements**:
```python
class AuthenticationMethods:
    """Standard authentication methods for MCP servers."""
    
    # Method 1: OAuth 2.0 (Most Secure - for Cloud/SaaS)
    OAUTH2_AUTHORIZATION_CODE = "oauth2_auth_code"
    OAUTH2_CLIENT_CREDENTIALS = "oauth2_client_creds"
    OAUTH2_BYOT = "oauth2_byot"  # Bring Your Own Token
    
    # Method 2: API Key/Token (Standard - for Cloud/SaaS)
    API_KEY_SECRET = "api_key_secret"
    API_TOKEN_USERNAME = "api_token_username"
    
    # Method 3: Personal Access Token (Enterprise - for Self-Hosted)
    PERSONAL_ACCESS_TOKEN = "personal_token"
    
    # Method 4: Basic Authentication (Legacy - for Self-Hosted)
    BASIC_AUTH = "basic_auth"
```

### 2. Authentication Precedence Rules

**Implementation Pattern**:
```python
def determine_auth_method(config: ServiceConfig, user_context: dict) -> str:
    """Determine authentication method with clear precedence rules."""
    
    # 1. Per-request authentication (highest priority)
    if user_context.get("auth_token"):
        return user_context.get("auth_type", "bearer")
    
    # 2. OAuth 2.0 (server-configured)
    if config.oauth_client_id and config.oauth_client_secret:
        if config.oauth_access_token or has_stored_tokens():
            return "oauth2"
    
    # 3. API Key/Token
    if config.api_key:
        return "api_key"
    
    # 4. Personal Access Token
    if config.personal_token:
        return "personal_token"
    
    # 5. Basic authentication (fallback)
    if config.username and config.password:
        return "basic_auth"
    
    return "none"
```

### 3. Multi-Tenant Authentication Middleware

**Implementation Template**:
```python
class UserTokenMiddleware(BaseHTTPMiddleware):
    """Extract and validate per-request authentication tokens."""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Extract authentication headers
        auth_header = request.headers.get("Authorization", "")
        api_key_header = request.headers.get("X-API-Key", "")
        
        # Parse Bearer tokens (OAuth/PAT)
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            request.state.user_auth_token = token
            request.state.user_auth_type = "bearer"
            
        # Parse API keys
        elif api_key_header:
            request.state.user_auth_token = api_key_header
            request.state.user_auth_type = "api_key"
            
        # Additional service-specific headers
        for header_name, auth_type in self.CUSTOM_AUTH_HEADERS.items():
            if header_value := request.headers.get(header_name):
                request.state.user_auth_token = header_value
                request.state.user_auth_type = auth_type
                break
        
        return await call_next(request)
```

## Tool Development Philosophy

### 1. Tool Organization Pattern

**Philosophy**: Organize tools by **feature domain**, not by CRUD operations.

**Implementation**:
```python
# ✅ GOOD: Feature-domain organization
{service_name}/
├── projects.py          # project_create, project_get, project_list, project_update
├── issues.py            # issue_create, issue_get, issue_search, issue_update
├── users.py             # user_get, user_search, user_invite
├── workflows.py         # workflow_trigger, workflow_status, workflow_history
└── reports.py           # report_generate, report_export, report_schedule

# ❌ BAD: CRUD-based organization
{service_name}/
├── create.py            # Mixed create operations
├── read.py              # Mixed read operations  
├── update.py            # Mixed update operations
└── delete.py            # Mixed delete operations
```

### 2. Tool Definition Standards

**Template for every tool**:
```python
@{service}_mcp.tool(
    name="{service}_{feature}_{action}",  # Consistent naming
    description="{Action verb} {object} in {ServiceName} {additional context}",
    tags=["{service}", "{read|write}", "{feature_category}"]  # Consistent tagging
)
def {feature}_{action}_tool(
    # Required parameters first
    {required_param}: Annotated[{type}, "{Clear description with example}"],
    
    # Optional parameters with defaults
    {optional_param}: Annotated[{type} | None, "{Description}"] = None,
    
    # Context injection (always last)
    context: Annotated[{ServiceName}Context, Context]
) -> str:
    """
    {Detailed docstring describing tool behavior}
    
    Args:
        {required_param}: {Description with constraints and examples}
        {optional_param}: {Description with default behavior}
        
    Returns:
        Formatted string with {describe return format}
        
    Raises:
        MCPError: If {describe error conditions}
    """
    try:
        # Validate inputs
        if not {required_param} or not {required_param}.strip():
            raise ValueError(f"{required_param} cannot be empty")
        
        # Check read-only mode for write operations
        if context.read_only and "write" in context.current_tool_tags:
            raise MCPError("Cannot perform write operation in read-only mode")
        
        # Execute business logic
        client = context.{service}_client
        result = client.{feature}_{action}({required_param}, **optional_params)
        
        # Format response consistently
        return format_{feature}_response(result)
        
    except {ServiceName}AuthenticationError:
        raise MCPError("Authentication failed. Check your credentials.")
    except {ServiceName}NotFoundError:
        raise MCPError(f"{Feature} not found: {required_param}")
    except {ServiceName}PermissionError:
        raise MCPError(f"Insufficient permissions for {action} operation")
    except Exception as e:
        logger.error(f"Unexpected error in {feature}_{action}_tool: {e}", exc_info=True)
        raise MCPError(f"Failed to {action} {feature}: {str(e)}")
```

### 3. Tool Tagging Strategy

**Standardized Tags**:
```python
class ToolTags:
    # Service identification
    SERVICE_TAGS = ["{service_a}", "{service_b}"]
    
    # Operation level (for read-only mode filtering)
    OPERATION_TAGS = ["read", "write"]
    
    # Feature categories (for tool discovery)
    FEATURE_TAGS = [
        "projects", "issues", "users", "workflows", 
        "reports", "admin", "integrations", "search"
    ]
    
    # Special capabilities
    CAPABILITY_TAGS = [
        "batch",      # Supports batch operations
        "paginated",  # Supports pagination
        "filtered",   # Supports filtering
        "export",     # Can export data
        "webhook",    # Webhook-related
        "realtime"    # Real-time operations
    ]
```

## Data Processing Philosophy

### 1. Response Formatting Standards

**Philosophy**: Consistent, human-readable responses with structured data.

**Implementation Template**:
```python
class ResponseFormatter:
    """Standardized response formatting for all tools."""
    
    @staticmethod
    def format_item_response(item: dict, item_type: str) -> str:
        """Format single item response."""
        lines = [
            f"# {item_type}: {item.get('id', 'Unknown')}",
            f"**Name**: {item.get('name', 'N/A')}",
            f"**Status**: {item.get('status', 'N/A')}",
            f"**Created**: {format_timestamp(item.get('created_at'))}",
            f"**Updated**: {format_timestamp(item.get('updated_at'))}",
            "",
            "## Description",
            item.get('description', 'No description provided'),
        ]
        
        # Add optional sections
        if item.get('tags'):
            lines.extend([
                "",
                "## Tags",
                ", ".join(item['tags'])
            ])
            
        if item.get('metadata'):
            lines.extend([
                "",
                "## Additional Information",
                format_metadata(item['metadata'])
            ])
            
        return "\n".join(lines)
    
    @staticmethod
    def format_list_response(items: list[dict], item_type: str, total: int = None) -> str:
        """Format list response with summary."""
        if not items:
            return f"No {item_type.lower()}s found."
            
        lines = [f"# {item_type}s ({len(items)} shown{f' of {total} total' if total else ''})"]
        lines.append("")
        
        for item in items:
            lines.extend([
                f"## {item.get('name', item.get('id', 'Unknown'))}",
                f"- **ID**: {item.get('id', 'N/A')}",
                f"- **Status**: {item.get('status', 'N/A')}",
                f"- **Created**: {format_timestamp(item.get('created_at'))}",
                ""
            ])
            
        return "\n".join(lines)
    
    @staticmethod
    def format_error_response(error: Exception, operation: str) -> str:
        """Format error response with actionable guidance."""
        error_type = type(error).__name__
        
        lines = [
            f"❌ {operation} failed",
            f"**Error**: {error_type}",
            f"**Message**: {str(error)}",
            "",
            "## Troubleshooting",
        ]
        
        # Add specific guidance based on error type
        if "Authentication" in error_type:
            lines.extend([
                "- Verify your authentication credentials",
                "- Check if your token/key has expired",
                "- Ensure you have the required permissions"
            ])
        elif "NotFound" in error_type:
            lines.extend([
                "- Verify the ID/identifier is correct",
                "- Check if the resource still exists",
                "- Ensure you have access to view this resource"
            ])
        elif "Permission" in error_type:
            lines.extend([
                "- Contact your administrator for required permissions",
                "- Check if your account has the necessary role",
                "- Verify the resource is in an accessible workspace"
            ])
        else:
            lines.extend([
                "- Check your network connection",
                "- Verify the service is accessible",
                "- Try again after a few moments"
            ])
            
        return "\n".join(lines)
```

### 2. Model System Architecture

**Base Model Pattern**:
```python
from datetime import datetime
from typing import Any, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T", bound="BaseApiModel")

class BaseApiModel(BaseModel):
    """Base model for all API response models."""
    
    @classmethod
    def from_api_response(cls: type[T], data: dict[str, Any], **kwargs: Any) -> T:
        """Convert API response to model instance with error handling."""
        try:
            # Handle nested objects
            processed_data = cls._preprocess_api_data(data)
            return cls(**processed_data)
        except Exception as e:
            logger.error(f"Failed to create {cls.__name__} from API data: {e}")
            # Return minimal valid instance
            return cls._create_fallback_instance(data)
    
    @classmethod
    def _preprocess_api_data(cls, data: dict) -> dict:
        """Preprocess API data before model creation."""
        # Handle common API response patterns
        processed = {}
        
        for field_name, field_info in cls.model_fields.items():
            api_value = data.get(field_name) or data.get(to_snake_case(field_name))
            
            if api_value is not None:
                processed[field_name] = cls._convert_field_value(api_value, field_info)
                
        return processed
    
    def to_simplified_dict(self) -> dict[str, Any]:
        """Convert to simplified dictionary for MCP responses."""
        return self.model_dump(
            exclude_none=True,
            exclude_unset=True,
            by_alias=True
        )
    
    def to_formatted_string(self) -> str:
        """Convert to human-readable formatted string."""
        # Delegate to ResponseFormatter
        return ResponseFormatter.format_item_response(
            self.to_simplified_dict(), 
            self.__class__.__name__.replace("Model", "")
        )
```

## Configuration and Environment Philosophy

### 1. Environment Variable Standardization

**Naming Convention**:
```
{SERVICE_NAME}_{COMPONENT}_{SETTING}

Examples:
SLACK_API_TOKEN
SLACK_OAUTH_CLIENT_ID  
SLACK_CUSTOM_HEADERS
SLACK_SSL_VERIFY
SLACK_RATE_LIMIT

GITHUB_PERSONAL_TOKEN
GITHUB_OAUTH_CLIENT_SECRET
GITHUB_DEFAULT_ORG
GITHUB_MAX_RETRIES
```

### 2. Configuration Hierarchy Template

**Implementation Priority**:
```python
def get_config_value(key: str, default: Any = None) -> Any:
    """Get configuration value with standardized precedence."""
    
    # 1. Command-line arguments (highest priority)
    if cli_args := get_cli_argument(key):
        return cli_args
    
    # 2. Environment variables
    if env_value := os.getenv(key):
        return env_value
    
    # 3. .env file variables
    if env_file_value := get_env_file_value(key):
        return env_file_value
    
    # 4. Configuration file (JSON/YAML)
    if config_file_value := get_config_file_value(key):
        return config_file_value
    
    # 5. Default value (lowest priority)
    return default
```

### 3. Docker Configuration Strategy

**Multi-Configuration Approach**:
```dockerfile
# Dockerfile template
FROM python:3.11-slim

# Create app user for security
RUN useradd --create-home --shell /bin/bash app
USER app
WORKDIR /home/app

# Install dependencies
COPY --chown=app:app pyproject.toml uv.lock ./
RUN pip install -e .

# Copy application code
COPY --chown=app:app src/ ./src/

# Support multiple configuration methods
ENV CONFIG_METHOD=environment
VOLUME ["/home/app/.config"]  # For config files
VOLUME ["/home/app/.credentials"]  # For OAuth tokens

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Entry point with configuration flexibility
ENTRYPOINT ["python", "-m", "mcp_{service_name}"]
CMD ["--transport", "stdio"]
```

## User Experience Philosophy

### 1. Progressive Disclosure in Documentation

**Documentation Structure Template**:
```markdown
# {ServiceName} MCP Server

## Quick Start (30 seconds)
[Minimal setup for immediate value]

## Standard Setup (5 minutes)  
[Common production configuration]

## Advanced Configuration (15 minutes)
[Enterprise features and customization]

## Expert Configuration (30+ minutes)
[Multi-tenant, custom auth, etc.]
```

### 2. Error Message Design Standards

**Template for Error Messages**:
```python
class ErrorMessageTemplates:
    """Standardized error message patterns."""
    
    AUTHENTICATION_ERROR = """
    ❌ Authentication failed for {service_name}
    
    **Cause**: {specific_cause}
    
    **Solutions**:
    1. Verify your {auth_method} is valid and not expired
    2. Check your {service_name} account permissions
    3. Ensure the {service_name} service is accessible
    
    **Need help?** Check the authentication guide: {docs_url}
    """
    
    PERMISSION_ERROR = """
    ❌ Insufficient permissions for {operation}
    
    **Required permission**: {required_permission}
    **Your current role**: {current_role}
    
    **Solutions**:
    1. Contact your {service_name} administrator
    2. Request the '{required_permission}' permission  
    3. Check if you're in the correct workspace/organization
    """
    
    CONFIGURATION_ERROR = """
    ❌ {service_name} configuration error
    
    **Missing**: {missing_config}
    
    **To fix this**:
    1. Set the environment variable: {env_var_example}
    2. Or add to your .env file: {env_file_example}  
    3. Or use command line: {cli_example}
    
    **Configuration guide**: {docs_url}
    """
```

### 3. Installation Experience Optimization

**UX Journey Mapping**:
```python
class InstallationJourney:
    """Map user journey and optimize each step."""
    
    STEPS = {
        "discovery": {
            "duration": "2-5 minutes",
            "pain_points": ["Too much information", "Unclear value prop"],
            "optimizations": ["Clear examples", "Video demos", "Quick start"]
        },
        "authentication": {
            "duration": "5-15 minutes", 
            "pain_points": ["Complex OAuth", "Multiple auth methods", "Unclear instructions"],
            "optimizations": ["Guided wizard", "Auth method selection", "Clear precedence"]
        },
        "configuration": {
            "duration": "5-10 minutes",
            "pain_points": ["JSON syntax errors", "Environment variables", "Docker complexity"],
            "optimizations": ["Configuration validator", "Template generator", "Error checking"]
        },
        "first_success": {
            "duration": "1-3 minutes",
            "pain_points": ["Tool discovery", "Unclear capabilities", "No guidance"],
            "optimizations": ["Guided first use", "Example queries", "Success indicators"]
        }
    }
```

## Testing Philosophy

### 1. Test Architecture Pattern

**Test Organization**:
```
tests/
├── unit/                    # Fast, isolated tests
│   ├── test_config.py      # Configuration validation
│   ├── test_models.py      # Data model tests
│   ├── test_client.py      # HTTP client tests
│   └── services/
│       ├── test_{service_a}_tools.py
│       └── test_{service_b}_tools.py
├── integration/             # Real API tests (optional)
│   ├── test_auth_flows.py  # Authentication integration
│   ├── test_tool_execution.py
│   └── test_multi_service.py
├── mcp_protocol/           # MCP compliance tests
│   ├── test_tool_discovery.py  
│   ├── test_tool_execution.py
│   └── test_transport_layers.py
└── fixtures/               # Test data and mocks
    ├── mock_responses.py
    ├── test_configs.py
    └── sample_data.py
```

### 2. Mock Strategy Pattern

**Comprehensive Mocking**:
```python
class ServiceMockFactory:
    """Factory for creating consistent service mocks."""
    
    @staticmethod
    def create_service_client_mock(service_name: str) -> Mock:
        """Create mock service client with standard responses."""
        mock_client = Mock()
        
        # Standard successful responses
        mock_client.get.return_value = ServiceMockFactory._create_success_response()
        mock_client.post.return_value = ServiceMockFactory._create_creation_response()
        mock_client.put.return_value = ServiceMockFactory._create_update_response()
        mock_client.delete.return_value = ServiceMockFactory._create_deletion_response()
        
        # Configure common error scenarios
        ServiceMockFactory._configure_error_scenarios(mock_client)
        
        return mock_client
    
    @staticmethod
    def create_auth_scenarios() -> dict[str, Mock]:
        """Create mock scenarios for different authentication methods."""
        return {
            "oauth_success": Mock(is_auth_configured=Mock(return_value=True)),
            "oauth_failure": Mock(is_auth_configured=Mock(return_value=False)),
            "api_key_success": Mock(is_auth_configured=Mock(return_value=True)),
            "no_auth": Mock(is_auth_configured=Mock(return_value=False)),
        }
```

## Performance and Scalability Philosophy

### 1. Caching Strategy

**Multi-Level Caching**:
```python
class CachingStrategy:
    """Standardized caching approach for MCP servers."""
    
    # Level 1: Token validation cache (5 minutes TTL)
    token_cache = TTLCache(maxsize=100, ttl=300)
    
    # Level 2: Configuration cache (server lifetime)
    config_cache = {}
    
    # Level 3: API response cache (1 minute TTL, optional)
    response_cache = TTLCache(maxsize=500, ttl=60)
    
    # Level 4: Tool discovery cache (per configuration)
    tool_discovery_cache = {}
    
    @staticmethod
    def cache_key_generator(method: str, *args, **kwargs) -> str:
        """Generate consistent cache keys."""
        key_parts = [method]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return ":".join(key_parts)
```

### 2. Connection Pooling Standards

**HTTP Client Configuration**:
```python
def create_optimized_http_client(config: ServiceConfig) -> httpx.AsyncClient:
    """Create HTTP client optimized for MCP server use."""
    
    limits = httpx.Limits(
        max_keepalive_connections=20,  # Keep connections alive
        max_connections=100,           # Total connection pool size
        keepalive_expiry=30,          # 30 seconds keepalive
    )
    
    timeout = httpx.Timeout(
        connect=10.0,    # Connection timeout
        read=30.0,       # Read timeout  
        write=10.0,      # Write timeout
        pool=60.0        # Pool timeout
    )
    
    return httpx.AsyncClient(
        base_url=config.url,
        limits=limits,
        timeout=timeout,
        verify=config.ssl_verify,
        http2=True,  # Enable HTTP/2 if available
        follow_redirects=True,
    )
```

## Deployment Philosophy

### 1. Container-First Strategy

**Multi-Architecture Support**:
```dockerfile
# Multi-stage build for optimization
FROM python:3.11-slim AS builder
WORKDIR /build
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen

FROM python:3.11-slim AS runtime
COPY --from=builder /build/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Security hardening
RUN useradd --create-home --shell /bin/bash app
USER app
WORKDIR /home/app

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Support multiple transports
EXPOSE 8000
ENTRYPOINT ["python", "-m", "mcp_{service_name}"]
```

### 2. Kubernetes-Ready Design

**Kubernetes Manifests Template**:
```yaml
# ConfigMap for environment variables
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcp-{service-name}-config
data:
  TRANSPORT: "streamable-http"
  PORT: "8000"
  READ_ONLY_MODE: "false"
  # Add non-sensitive configuration

---
# Secret for sensitive data
apiVersion: v1
kind: Secret
metadata:
  name: mcp-{service-name}-secrets
type: Opaque
stringData:
  # Add sensitive configuration (API keys, tokens, etc.)
  
---
# Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-{service-name}
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mcp-{service-name}
  template:
    metadata:
      labels:
        app: mcp-{service-name}
    spec:
      containers:
      - name: mcp-{service-name}
        image: ghcr.io/your-org/mcp-{service-name}:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: mcp-{service-name}-config
        - secretRef:
            name: mcp-{service-name}-secrets
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /healthz
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

## Monitoring and Observability

### 1. Structured Logging Standards

**Logging Configuration**:
```python
import structlog

def configure_logging(level: str = "INFO") -> None:
    """Configure structured logging for the MCP server."""
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

### 2. Metrics Collection

**Key Metrics Template**:
```python
class MCPServerMetrics:
    """Standardized metrics for MCP servers."""
    
    # Tool execution metrics
    tool_execution_duration = histogram("mcp_tool_execution_duration_seconds")
    tool_execution_count = counter("mcp_tool_execution_total")
    tool_execution_errors = counter("mcp_tool_execution_errors_total")
    
    # Authentication metrics
    auth_attempts = counter("mcp_auth_attempts_total")
    auth_failures = counter("mcp_auth_failures_total")
    auth_cache_hits = counter("mcp_auth_cache_hits_total")
    
    # Service API metrics
    service_api_duration = histogram("mcp_service_api_duration_seconds")
    service_api_errors = counter("mcp_service_api_errors_total")
    
    # System metrics
    active_connections = gauge("mcp_active_connections")
    memory_usage = gauge("mcp_memory_usage_bytes")
```

This comprehensive philosophy provides a scalable foundation for building enterprise-ready MCP servers that maintain simplicity for basic use cases while supporting complex deployment scenarios. The key is **layered architecture**, **modular services**, **multi-method authentication**, and **exceptional UX** at every step.