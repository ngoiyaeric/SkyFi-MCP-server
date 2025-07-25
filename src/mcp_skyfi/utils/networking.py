
import logging
from typing import Any, Dict, Optional, Type

import httpx

logger = logging.getLogger("mcp-skyfi.utils.networking")

def create_http_client(
    base_url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 30.0,
    verify: bool = True,
    limits: Optional[httpx.Limits] = None,
    **kwargs: Any
) -> httpx.AsyncClient:
    """
    Create an optimized HTTP client for MCP server use.
    
    Args:
        base_url: Base URL for requests
        headers: Default headers
        timeout: Request timeout in seconds
        verify: SSL certificate verification
        limits: Connection limits
        **kwargs: Additional httpx.AsyncClient arguments
        
    Returns:
        Configured httpx.AsyncClient instance
    """
    # Default connection limits for performance
    if limits is None:
        limits = httpx.Limits(
            max_keepalive_connections=20,  # Keep connections alive
            max_connections=100,           # Total connection pool size
            keepalive_expiry=30,          # 30 seconds keepalive
        )
    
    # Default timeout configuration
    if isinstance(timeout, (int, float)):
        timeout = httpx.Timeout(
            connect=min(10.0, timeout),    # Connection timeout
            read=timeout,                  # Read timeout
            write=min(10.0, timeout),      # Write timeout
            pool=timeout + 30.0            # Pool timeout
        )
    
    # Default headers
    if headers is None:
        headers = {}
    
    # Ensure User-Agent is set
    if "User-Agent" not in headers:
        headers["User-Agent"] = "MCP-SkyFi/1.0"
    
    client_kwargs = {
        "base_url": base_url,
        "headers": headers,
        "timeout": timeout,
        "verify": verify,
        "limits": limits,
        "http2": True,  # Enable HTTP/2 if available
        "follow_redirects": True,
        **kwargs
    }
    
    logger.debug(f"Creating HTTP client for {base_url}")
    return httpx.AsyncClient(**client_kwargs)

async def handle_http_error(
    response: httpx.Response,
    api_error_class: Type[Exception],
    auth_error_class: Type[Exception]
) -> None:
    """
    Handle HTTP error responses with appropriate exception types.
    
    Args:
        response: HTTP response with error status
        api_error_class: Exception class for general API errors
        auth_error_class: Exception class for authentication errors
        
    Raises:
        auth_error_class: For authentication errors (401, 403)
        api_error_class: For other API errors
    """
    try:
        error_data = response.json()
        error_message = error_data.get("message", "Unknown error")
        error_details = error_data.get("details", [])
    except (ValueError, KeyError):
        error_message = response.text or f"HTTP {response.status_code}"
        error_details = []
    
    # Authentication errors
    if response.status_code in (401, 403):
        logger.error(f"Authentication error {response.status_code}: {error_message}")
        raise auth_error_class(error_message)
    
    # Build detailed error message
    if error_details:
        detailed_message = f"{error_message} - Details: {', '.join(map(str, error_details))}"
    else:
        detailed_message = error_message
    
    logger.error(f"API error {response.status_code}: {detailed_message}")
    raise api_error_class(f"HTTP {response.status_code}: {detailed_message}")

def format_url(base_url: str, endpoint: str) -> str:
    """
    Format URL by combining base URL and endpoint.
    
    Args:
        base_url: Base URL (may or may not end with /)
        endpoint: API endpoint (may or may not start with /)
        
    Returns:
        Properly formatted URL
    """
    base = base_url.rstrip('/')
    endpoint = endpoint.lstrip('/')
    return f"{base}/{endpoint}" if endpoint else base

def format_headers(headers: Dict[str, Any]) -> Dict[str, str]:
    """
    Format headers dictionary to ensure all values are strings.
    
    Args:
        headers: Raw headers dictionary
        
    Returns:
        Headers with string values
    """
    formatted = {}
    for key, value in headers.items():
        if value is not None:
            formatted[str(key)] = str(value)
    return formatted

def is_json_response(response: httpx.Response) -> bool:
    """
    Check if response contains JSON data.
    
    Args:
        response: HTTP response
        
    Returns:
        True if response appears to contain JSON
    """
    content_type = response.headers.get("Content-Type", "")
    return "application/json" in content_type.lower()

def extract_error_message(response: httpx.Response) -> str:
    """
    Extract error message from HTTP response.
    
    Args:
        response: HTTP response with error status
        
    Returns:
        Human-readable error message
    """
    try:
        if is_json_response(response):
            error_data = response.json()
            # Try common error message fields
            for field in ["message", "error", "detail", "msg"]:
                if field in error_data:
                    return str(error_data[field])
            
            # If no standard field, return the whole JSON as string
            return str(error_data)
        else:
            # Non-JSON response, return text content
            text = response.text.strip()
            return text if text else f"HTTP {response.status_code}"
            
    except Exception:
        # Fallback to status code if all else fails
        return f"HTTP {response.status_code}"

class RequestRetry:
    """Helper class for implementing request retry logic with exponential backoff."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def should_retry(self, attempt: int, response: Optional[httpx.Response] = None, exception: Optional[Exception] = None) -> bool:
        """
        Determine if request should be retried.
        
        Args:
            attempt: Current attempt number (0-indexed)
            response: HTTP response (if available)
            exception: Exception that occurred (if any)
            
        Returns:
            True if request should be retried
        """
        if attempt >= self.max_retries:
            return False
        
        # Retry on timeout or connection errors
        if exception and isinstance(exception, (httpx.TimeoutException, httpx.RequestError)):
            return True
        
        # Retry on specific HTTP status codes
        if response:
            retry_status_codes = {429, 500, 502, 503, 504}
            return response.status_code in retry_status_codes
        
        return False
    
    def get_delay(self, attempt: int, response: Optional[httpx.Response] = None) -> float:
        """
        Calculate delay before next retry.
        
        Args:
            attempt: Current attempt number (0-indexed)
            response: HTTP response (if available)
            
        Returns:
            Delay in seconds
        """
        # Check for Retry-After header
        if response and "Retry-After" in response.headers:
            try:
                return min(float(response.headers["Retry-After"]), self.max_delay)
            except ValueError:
                pass
        
        # Exponential backoff with jitter
        import random
        delay = self.base_delay * (2 ** attempt)
        jitter = random.uniform(0, 0.1) * delay
        return min(delay + jitter, self.max_delay)