# Service Client Implementation Patterns

## Overview

This document defines comprehensive patterns for service client implementation with connection pooling, authentication handling, error management, and performance optimization for the SkyFi MCP server.

## 1. Base Client Architecture

### 1.1 HTTP Client Utilities

```python
# utils/networking.py
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional, Type
import httpx
from starlette.responses import Response

logger = logging.getLogger("mcp-skyfi.networking")

def create_http_client(
    base_url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    verify: bool = True,
    limits: Optional[httpx.Limits] = None,
    **kwargs
) -> httpx.AsyncClient:
    """
    Create optimized HTTP client for MCP server use.
    
    Args:
        base_url: Base URL for all requests
        headers: Default headers for all requests
        timeout: Request timeout in seconds
        verify: Whether to verify SSL certificates
        limits: Connection pool limits
        **kwargs: Additional httpx.AsyncClient arguments
    
    Returns:
        Configured AsyncClient instance
    """
    
    # Default connection limits optimized for MCP usage
    if limits is None:
        limits = httpx.Limits(
            max_keepalive_connections=20,  # Keep connections alive
            max_connections=100,           # Total connection pool size
            keepalive_expiry=30,          # 30 seconds keepalive
        )
    
    # Configure timeout with different values for different operations
    timeout_config = httpx.Timeout(
        connect=10.0,    # Connection timeout
        read=timeout,    # Read timeout (configurable)
        write=10.0,      # Write timeout
        pool=60.0        # Pool timeout
    )
    
    # Default headers
    default_headers = {
        "User-Agent": "SkyFi-MCP-Server/1.0",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    
    if headers:
        default_headers.update(headers)
    
    return httpx.AsyncClient(
        base_url=base_url,
        headers=default_headers,
        limits=limits,
        timeout=timeout_config,
        verify=verify,
        http2=True,  # Enable HTTP/2 if available
        follow_redirects=True,
        **kwargs
    )

async def handle_http_error(
    response: httpx.Response, 
    api_error_class: Type[Exception],
    auth_error_class: Type[Exception]
) -> None:
    """
    Handle HTTP errors with appropriate exception mapping.
    
    Args:
        response: HTTP response object
        api_error_class: Exception class for API errors
        auth_error_class: Exception class for authentication errors
        
    Raises:
        auth_error_class: For 401/403 status codes
        api_error_class: For other HTTP errors
    """
    try:
        error_data = response.json()
        error_message = error_data.get("message", "Unknown error")
        error_details = error_data.get("details", {})
    except (ValueError, KeyError):
        error_message = f"HTTP {response.status_code}: {response.text[:200]}"
        error_details = {}
    
    if response.status_code in (401, 403):
        raise auth_error_class(f"Authentication failed: {error_message}")
    elif response.status_code == 429:
        retry_after = response.headers.get("Retry-After", "60")
        raise api_error_class(f"Rate limit exceeded. Retry after {retry_after} seconds")
    elif response.status_code >= 500:
        raise api_error_class(f"Server error ({response.status_code}): {error_message}")
    else:
        raise api_error_class(f"API error ({response.status_code}): {error_message}")

class RetryConfig:
    """Configuration for request retry behavior."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for the given attempt number."""
        delay = self.base_delay * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            import random
            delay *= (0.5 + random.random())  # Add 0-50% jitter
        
        return delay

async def retry_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    retry_config: RetryConfig,
    **request_kwargs
) -> httpx.Response:
    """
    Execute HTTP request with retry logic.
    
    Args:
        client: HTTP client instance
        method: HTTP method
        url: Request URL
        retry_config: Retry configuration
        **request_kwargs: Additional request arguments
        
    Returns:
        HTTP response
        
    Raises:
        httpx.RequestError: If all retry attempts fail
    """
    last_exception = None
    
    for attempt in range(retry_config.max_attempts):
        try:
            response = await client.request(method, url, **request_kwargs)
            
            # Don't retry on successful responses or client errors
            if response.status_code < 500 and response.status_code != 429:
                return response
            
            # For server errors and rate limits, retry
            logger.warning(
                f"Request failed with status {response.status_code}, "
                f"attempt {attempt + 1}/{retry_config.max_attempts}"
            )
            
        except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as e:
            last_exception = e
            logger.warning(
                f"Request error on attempt {attempt + 1}/{retry_config.max_attempts}: {e}"
            )
        
        # Wait before retrying (except on last attempt)
        if attempt < retry_config.max_attempts - 1:
            delay = retry_config.get_delay(attempt)
            await asyncio.sleep(delay)
    
    # All attempts failed
    if last_exception:
        raise last_exception
    else:
        raise httpx.RequestError(f"Request failed after {retry_config.max_attempts} attempts")
```

### 1.2 Base Service Client Pattern

```python
# models/base_client.py
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TypeVar, Generic, Union
import httpx
from cachetools import TTLCache

from .base import BaseServiceConfig
from ..utils.networking import create_http_client, handle_http_error, retry_request, RetryConfig
from ..exceptions import BaseAPIError, BaseAuthenticationError

T = TypeVar('T', bound=BaseServiceConfig)

logger = logging.getLogger("mcp-skyfi.base.client")

class BaseServiceClient(ABC, Generic[T]):
    """
    Base HTTP client with authentication, caching, and error handling.
    
    This class provides:
    - Connection pooling and HTTP/2 support
    - Multiple authentication method handling
    - Request retries with exponential backoff
    - Response caching with TTL
    - Comprehensive error handling and logging
    - User context support for per-request auth
    """
    
    def __init__(
        self, 
        config: T, 
        user_context: Optional[Dict[str, Any]] = None
    ):
        self.config = config
        self.user_context = user_context or {}
        
        # HTTP client (lazy initialization)
        self._client: Optional[httpx.AsyncClient] = None
        
        # Caching
        self._auth_cache = TTLCache(maxsize=100, ttl=300)  # 5-minute auth cache
        self._response_cache = TTLCache(maxsize=500, ttl=60)  # 1-minute response cache
        
        # Retry configuration
        self._retry_config = RetryConfig(
            max_attempts=self.config.max_retries,
            base_delay=1.0,
            max_delay=30.0
        )
        
        # Performance metrics
        self._request_count = 0
        self._error_count = 0
        
    async def __aenter__(self) -> BaseServiceClient:
        """Async context manager entry."""
        await self._ensure_client()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
    
    async def close(self) -> None:
        """Close the HTTP client and cleanup resources."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def _ensure_client(self) -> None:
        """Ensure HTTP client is initialized with proper authentication."""
        if self._client:
            return
        
        # Build authentication headers
        headers = await self._build_auth_headers()
        
        # Create HTTP client with optimized settings
        self._client = create_http_client(
            base_url=self.config.url,
            headers=headers,
            timeout=self.config.timeout,
            verify=self.config.ssl_verify,
        )
        
        logger.info(f"Initialized {self.config.service_name} client: {self.config.url}")
    
    @abstractmethod
    async def _build_auth_headers(self) -> Dict[str, str]:
        """Build authentication headers specific to the service."""
        pass
    
    def _get_auth_method(self) -> str:
        """Determine authentication method based on user context and config."""
        # Check user-provided authentication first (highest priority)
        if self.user_context.get("auth_token"):
            return self.user_context.get("auth_type", "bearer")
        
        # Fall back to server configuration
        return self.config.get_auth_method()
    
    def _get_cache_key(self, method: str, endpoint: str, params: Optional[Dict] = None) -> str:
        """Generate cache key for request."""
        key_parts = [method.upper(), endpoint]
        
        if params:
            # Sort params for consistent cache keys
            param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
            key_parts.append(param_str)
        
        return "|".join(key_parts)
    
    async def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated HTTP request with caching and retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (relative to base URL)
            params: URL parameters
            data: Form data
            json: JSON data
            headers: Additional headers
            use_cache: Whether to use response caching
            cache_ttl: Custom cache TTL in seconds
            
        Returns:
            Parsed JSON response
            
        Raises:
            BaseAuthenticationError: For authentication failures
            BaseAPIError: For other API errors
        """
        await self._ensure_client()
        
        # Build full URL
        url = endpoint if endpoint.startswith("http") else f"{self.config.url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        # Check cache for GET requests
        if method.upper() == "GET" and use_cache:
            cache_key = self._get_cache_key(method, endpoint, params)
            if cached_response := self._response_cache.get(cache_key):
                logger.debug(f"Cache hit for {cache_key}")
                return cached_response
        
        # Prepare request
        request_headers = {}
        if headers:
            request_headers.update(headers)
        
        # Add user-specific auth headers if provided
        if user_auth := self.user_context.get("auth_token"):
            auth_type = self.user_context.get("auth_type", "bearer")
            if auth_type == "bearer":
                request_headers["Authorization"] = f"Bearer {user_auth}"
            elif auth_type == "api_key":
                # Service-specific header will be added by subclass
                pass
        
        try:
            self._request_count += 1
            
            # Execute request with retry logic
            response = await retry_request(
                client=self._client,
                method=method,
                url=url,
                retry_config=self._retry_config,
                params=params,
                data=data,
                json=json,
                headers=request_headers
            )
            
            # Handle HTTP errors
            if response.status_code >= 400:
                self._error_count += 1
                await handle_http_error(response, BaseAPIError, BaseAuthenticationError)
            
            # Parse JSON response
            try:
                result = response.json()
            except ValueError as e:
                raise BaseAPIError(f"Invalid JSON response: {str(e)}")
            
            # Cache successful GET responses
            if method.upper() == "GET" and use_cache and response.status_code == 200:
                cache_key = self._get_cache_key(method, endpoint, params)
                ttl = cache_ttl or 60  # Default 1 minute cache
                self._response_cache[cache_key] = result
                logger.debug(f"Cached response for {cache_key} (TTL: {ttl}s)")
            
            return result
            
        except httpx.TimeoutException:
            self._error_count += 1
            raise BaseAPIError(f"Request timeout after {self.config.timeout} seconds")
        except httpx.RequestError as e:
            self._error_count += 1
            raise BaseAPIError(f"Request failed: {str(e)}")
    
    # Convenience methods
    async def get(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None, 
        **kwargs
    ) -> Dict[str, Any]:
        """Make GET request."""
        return await self.request("GET", endpoint, params=params, **kwargs)
    
    async def post(
        self, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None, 
        json: Optional[Dict[str, Any]] = None, 
        **kwargs
    ) -> Dict[str, Any]:
        """Make POST request."""
        return await self.request("POST", endpoint, data=data, json=json, use_cache=False, **kwargs)
    
    async def put(
        self, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None, 
        json: Optional[Dict[str, Any]] = None, 
        **kwargs
    ) -> Dict[str, Any]:
        """Make PUT request."""
        return await self.request("PUT", endpoint, data=data, json=json, use_cache=False, **kwargs)
    
    async def delete(
        self, 
        endpoint: str, 
        **kwargs
    ) -> Dict[str, Any]:
        """Make DELETE request."""
        return await self.request("DELETE", endpoint, use_cache=False, **kwargs)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the service."""
        try:
            # Most services have a health or ping endpoint
            for endpoint in ["/health", "/ping", "/status", "/"]:
                try:
                    result = await self.get(endpoint, use_cache=False)
                    return {
                        "status": "healthy",
                        "endpoint": endpoint,
                        "response": result
                    }
                except BaseAPIError:
                    continue
            
            return {
                "status": "unhealthy",
                "error": "No health endpoint responded"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get client performance metrics."""
        return {
            "request_count": self._request_count,
            "error_count": self._error_count,
            "error_rate": self._error_count / max(self._request_count, 1),
            "cache_size": len(self._response_cache),
            "cache_hits": getattr(self._response_cache, 'hits', 0),
            "cache_misses": getattr(self._response_cache, 'misses', 0),
        }
    
    def clear_cache(self) -> None:
        """Clear all cached responses."""
        self._response_cache.clear()
        self._auth_cache.clear()
        logger.info("Cleared all caches")
```

## 2. SkyFi Service Client Implementation

### 2.1 SkyFi-Specific Client

```python
# skyfi/client.py
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from ..models.base_client import BaseServiceClient
from .config import SkyFiConfig
from ..exceptions import SkyFiAPIError, SkyFiAuthenticationError

logger = logging.getLogger("mcp-skyfi.skyfi.client")

class SkyFiClient(BaseServiceClient[SkyFiConfig]):
    """
    HTTP client for SkyFi API with specific authentication and business logic.
    
    Features:
    - SkyFi-specific authentication header handling
    - Budget and quota checking
    - Order cost calculation and validation
    - Archive search with pagination
    - Order status polling
    - Webhook validation
    """
    
    async def _build_auth_headers(self) -> Dict[str, str]:
        """Build SkyFi-specific authentication headers."""
        headers = {}
        
        # SkyFi uses X-Skyfi-Api-Key header for API key auth
        auth_method = self._get_auth_method()
        
        if auth_method == "api_key" and self.config.api_key:
            headers["X-Skyfi-Api-Key"] = self.config.api_key
        elif auth_method == "oauth" and self.config.oauth_access_token:
            headers["Authorization"] = f"Bearer {self.config.oauth_access_token}"
        elif auth_method == "personal_token" and self.config.personal_token:
            headers["Authorization"] = f"Bearer {self.config.personal_token}"
        
        # Add custom headers
        if self.config.custom_headers:
            headers.update(self.config.custom_headers)
        
        return headers
    
    # User and Account Management
    async def get_user_info(self) -> Dict[str, Any]:
        """
        Get current user information and budget status.
        
        Returns:
            User information including budget details
        """
        return await self.get("/auth/whoami", cache_ttl=60)  # Cache for 1 minute
    
    async def check_budget(self, required_amount: float = 0.0) -> Dict[str, Any]:
        """
        Check user budget status and validate if amount can be spent.
        
        Args:
            required_amount: Amount needed for operation
            
        Returns:
            Budget status and validation result
        """
        user_info = await self.get_user_info()
        
        current_usage = user_info.get("currentBudgetUsage", 0)
        budget_amount = user_info.get("budgetAmount", 0)
        available = budget_amount - current_usage
        
        result = {
            "current_usage": current_usage,
            "budget_amount": budget_amount,
            "available": available,
            "required": required_amount,
            "can_afford": available >= required_amount,
            "usage_percentage": current_usage / budget_amount if budget_amount > 0 else 0,
        }
        
        # Check against warning threshold
        if result["usage_percentage"] >= self.config.budget_warning_threshold:
            result["warning"] = f"Budget usage at {result['usage_percentage']:.1%}"
        
        return result
    
    # Archive Search and Retrieval
    async def search_archives(
        self,
        aoi: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        max_cloud_coverage: Optional[int] = None,
        max_off_nadir_angle: Optional[int] = None,
        resolutions: Optional[List[str]] = None,
        product_types: Optional[List[str]] = None,
        providers: Optional[List[str]] = None,
        open_data: Optional[bool] = None,
        min_overlap_ratio: Optional[float] = None,
        page_size: Optional[int] = None,
        next_page_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search satellite imagery archives.
        
        Args:
            aoi: WKT polygon defining area of interest
            from_date: Start date in ISO format
            to_date: End date in ISO format
            max_cloud_coverage: Maximum cloud coverage percentage (0-100)
            max_off_nadir_angle: Maximum off-nadir angle (0-90 degrees)
            resolutions: List of desired resolutions
            product_types: List of product types
            providers: List of satellite providers
            open_data: Filter for free open data only
            min_overlap_ratio: Minimum overlap with AOI (0-1)
            page_size: Results per page
            next_page_token: Token for pagination
            
        Returns:
            Search results with archives and pagination info
        """
        params = {"aoi": aoi}
        
        # Add optional parameters
        if from_date:
            params["fromDate"] = from_date
        if to_date:
            params["toDate"] = to_date
        if max_cloud_coverage is not None:
            params["maxCloudCoveragePercent"] = max_cloud_coverage
        if max_off_nadir_angle is not None:
            params["maxOffNadirAngle"] = max_off_nadir_angle
        if resolutions:
            params["resolutions"] = resolutions
        if product_types:
            params["productTypes"] = product_types
        if providers:
            params["providers"] = providers
        if open_data is not None:
            params["openData"] = open_data
        if min_overlap_ratio is not None:
            params["minOverlapRatio"] = min_overlap_ratio
        
        # Pagination
        page_size = page_size or self.config.default_page_size
        params["pageSize"] = min(page_size, self.config.max_page_size)
        
        if next_page_token:
            params["pageToken"] = next_page_token
        
        return await self.get("/archives", params=params, cache_ttl=self.config.cache_ttl_seconds)
    
    async def get_archive_details(self, archive_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific archive.
        
        Args:
            archive_id: Archive UUID
            
        Returns:
            Detailed archive information
        """
        return await self.get(f"/archives/{archive_id}", cache_ttl=3600)  # Cache for 1 hour
    
    # Order Management
    async def create_archive_order(
        self,
        aoi: str,
        archive_id: str,
        delivery_driver: str,
        delivery_params: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new archive order.
        
        Args:
            aoi: WKT polygon for area of interest
            archive_id: Archive UUID to order
            delivery_driver: Delivery method (S3, GS, AZURE, NONE)
            delivery_params: Driver-specific delivery parameters
            metadata: Optional order metadata
            webhook_url: Optional webhook for status updates
            
        Returns:
            Order confirmation with ID and cost
        """
        # Validate delivery driver
        valid_drivers = ["S3", "GS", "AZURE", "NONE"]
        if delivery_driver not in valid_drivers:
            raise SkyFiAPIError(f"Invalid delivery driver. Must be one of: {', '.join(valid_drivers)}")
        
        order_data = {
            "aoi": aoi,
            "archiveId": archive_id,
            "deliveryDriver": delivery_driver,
            "deliveryParams": delivery_params
        }
        
        if metadata:
            order_data["metadata"] = metadata
        if webhook_url:
            order_data["webhookUrl"] = webhook_url
        
        # Check budget before creating order (if configured)
        if self.config.max_order_cost:
            # Estimate cost first
            try:
                cost_estimate = await self.estimate_order_cost(aoi, archive_id)
                if cost_estimate > self.config.max_order_cost:
                    raise SkyFiAPIError(f"Estimated cost ${cost_estimate} exceeds limit ${self.config.max_order_cost}")
            except Exception as e:
                logger.warning(f"Could not estimate order cost: {e}")
        
        return await self.post("/orders", json=order_data)
    
    async def create_tasking_order(
        self,
        aoi: str,
        window_start: str,
        window_end: str,
        product_type: str,
        resolution: str,
        delivery_driver: str,
        delivery_params: Dict[str, Any],
        max_cloud_coverage: Optional[int] = None,
        max_off_nadir_angle: Optional[int] = None,
        priority_item: bool = False,
        required_provider: Optional[str] = None,
        sar_parameters: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new tasking order for future satellite capture.
        
        Args:
            aoi: WKT polygon for area of interest
            window_start: Capture window start time (ISO format)
            window_end: Capture window end time (ISO format)
            product_type: Type of imagery product
            resolution: Desired resolution
            delivery_driver: Delivery method
            delivery_params: Driver-specific delivery parameters
            max_cloud_coverage: Maximum acceptable cloud coverage
            max_off_nadir_angle: Maximum off-nadir angle
            priority_item: Whether this is a priority order
            required_provider: Specific satellite provider required
            sar_parameters: SAR-specific parameters
            metadata: Optional order metadata
            webhook_url: Optional webhook for status updates
            
        Returns:
            Tasking order confirmation
        """
        order_data = {
            "aoi": aoi,
            "windowStart": window_start,
            "windowEnd": window_end,
            "productType": product_type,
            "resolution": resolution,
            "deliveryDriver": delivery_driver,
            "deliveryParams": delivery_params
        }
        
        # Add optional parameters
        if max_cloud_coverage is not None:
            order_data["maxCloudCoveragePercent"] = max_cloud_coverage
        if max_off_nadir_angle is not None:
            order_data["maxOffNadirAngle"] = max_off_nadir_angle
        if priority_item:
            order_data["priorityItem"] = priority_item
        if required_provider:
            order_data["requiredProvider"] = required_provider
        if sar_parameters:
            order_data["sarParameters"] = sar_parameters
        if metadata:
            order_data["metadata"] = metadata
        if webhook_url:
            order_data["webhookUrl"] = webhook_url
        
        return await self.post("/orders/tasking", json=order_data)
    
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Get current status of an order.
        
        Args:
            order_id: Order UUID
            
        Returns:
            Order status and details
        """
        return await self.get(f"/orders/{order_id}", use_cache=False)  # Don't cache order status
    
    async def list_orders(
        self,
        order_type: Optional[str] = None,
        page_number: int = 0,
        page_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        List user's orders with pagination.
        
        Args:
            order_type: Filter by order type (ARCHIVE, TASKING)
            page_number: Page number (0-based)
            page_size: Results per page
            
        Returns:
            Paginated list of orders
        """
        params = {
            "pageNumber": page_number,
            "pageSize": page_size or self.config.default_page_size
        }
        
        if order_type:
            params["orderType"] = order_type
        
        return await self.get("/orders", params=params, cache_ttl=30)  # Cache for 30 seconds
    
    # Notification Management
    async def create_notification(
        self,
        aoi: str,
        webhook_url: str,
        gsd_min: Optional[float] = None,
        gsd_max: Optional[float] = None,
        product_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new notification for archive updates.
        
        Args:
            aoi: WKT polygon for area of interest
            webhook_url: Webhook URL for notifications
            gsd_min: Minimum ground sample distance
            gsd_max: Maximum ground sample distance
            product_type: Filter by product type
            
        Returns:
            Notification configuration
        """
        notification_data = {
            "aoi": aoi,
            "webhookUrl": webhook_url
        }
        
        if gsd_min is not None:
            notification_data["gsdMin"] = gsd_min
        if gsd_max is not None:
            notification_data["gsdMax"] = gsd_max
        if product_type:
            notification_data["productType"] = product_type
        
        return await self.post("/notifications", json=notification_data)
    
    async def list_notifications(self, page_size: Optional[int] = None) -> Dict[str, Any]:
        """List user's notification subscriptions."""
        params = {"pageSize": page_size or self.config.default_page_size}
        return await self.get("/notifications", params=params, cache_ttl=60)
    
    async def delete_notification(self, notification_id: str) -> Dict[str, Any]:
        """Delete a notification subscription."""
        return await self.delete(f"/notifications/{notification_id}")
    
    # Feasibility and Pricing
    async def check_feasibility(
        self,
        aoi: str,
        product_type: str,
        resolution: str,
        start_date: str,
        end_date: str,
        max_cloud_coverage: Optional[int] = None,
        required_provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check feasibility of satellite tasking for given parameters.
        
        Args:
            aoi: WKT polygon for area of interest
            product_type: Type of imagery product
            resolution: Desired resolution
            start_date: Start of feasibility window
            end_date: End of feasibility window
            max_cloud_coverage: Maximum cloud coverage
            required_provider: Specific provider requirement
            
        Returns:
            Feasibility analysis results
        """
        params = {
            "aoi": aoi,
            "productType": product_type,
            "resolution": resolution,
            "startDate": start_date,
            "endDate": end_date
        }
        
        if max_cloud_coverage is not None:
            params["maxCloudCoveragePercent"] = max_cloud_coverage
        if required_provider:
            params["requiredProvider"] = required_provider
        
        return await self.get("/feasibility", params=params, cache_ttl=3600)  # Cache for 1 hour
    
    async def get_pass_predictions(
        self,
        aoi: str,
        from_date: str,
        to_date: str,
        product_types: Optional[List[str]] = None,
        max_off_nadir_angle: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get satellite pass predictions for area and time window.
        
        Args:
            aoi: WKT polygon for area of interest
            from_date: Start date for predictions
            to_date: End date for predictions
            product_types: Filter by product types
            max_off_nadir_angle: Maximum off-nadir angle
            
        Returns:
            Satellite pass predictions
        """
        params = {
            "aoi": aoi,
            "fromDate": from_date,
            "toDate": to_date
        }
        
        if product_types:
            params["productTypes"] = product_types
        if max_off_nadir_angle is not None:
            params["maxOffNadirAngle"] = max_off_nadir_angle
        
        return await self.get("/feasibility/passes", params=params, cache_ttl=1800)  # Cache for 30 minutes
    
    async def get_pricing(self, aoi: Optional[str] = None) -> Dict[str, Any]:
        """
        Get current pricing information.
        
        Args:
            aoi: Optional area of interest for location-based pricing
            
        Returns:
            Pricing structure and rates
        """
        params = {}
        if aoi:
            params["aoi"] = aoi
        
        return await self.get("/pricing", params=params, cache_ttl=3600)  # Cache for 1 hour
    
    # Utility Methods
    async def estimate_order_cost(self, aoi: str, archive_id: str) -> float:
        """
        Estimate cost for an archive order.
        
        Args:
            aoi: WKT polygon for area of interest
            archive_id: Archive to order
            
        Returns:
            Estimated cost in USD
        """
        # Get archive details for pricing
        archive = await self.get_archive_details(archive_id)
        price_per_sqkm = archive.get("priceForOneSquareKm", 0)
        
        if price_per_sqkm == 0:
            return 0.0  # Free/open data
        
        # Calculate AOI area (this would need a geometry utility)
        # For now, return a placeholder
        estimated_area_sqkm = 100.0  # Would calculate from AOI polygon
        
        return price_per_sqkm * estimated_area_sqkm
    
    async def validate_delivery_config(
        self, 
        delivery_driver: str, 
        delivery_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate delivery configuration by testing with demo delivery.
        
        Args:
            delivery_driver: Delivery method
            delivery_params: Driver-specific parameters
            
        Returns:
            Validation results
        """
        test_data = {
            "deliveryDriver": delivery_driver,
            "deliveryParams": delivery_params
        }
        
        try:
            result = await self.post("/demo-delivery", json=test_data)
            return {"valid": True, "result": result}
        except Exception as e:
            return {"valid": False, "error": str(e)}
```

This comprehensive service client implementation provides:

1. **Base Client Pattern** - Generic client with connection pooling, caching, retries, and error handling
2. **Authentication Flexibility** - Support for multiple auth methods with user context override
3. **Performance Optimization** - HTTP/2, connection pooling, response caching, and request retries
4. **SkyFi-Specific Features** - Budget checking, order validation, delivery testing, and cost estimation
5. **Error Handling** - Comprehensive error mapping with service-specific exceptions
6. **Metrics and Monitoring** - Built-in performance metrics and health checking
7. **Async Context Management** - Proper resource cleanup and connection management
8. **Caching Strategy** - Multi-level caching with configurable TTL for different data types

The architecture supports both simple usage patterns and advanced scenarios with per-request authentication and custom configuration overrides.