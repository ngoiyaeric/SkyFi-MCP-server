
import logging
from typing import Annotated, Any, Dict

from fastmcp import Context

from ..exceptions import SkyFiAPIError, SkyFiAuthenticationError
from ..models.skyfi import SkyFiUser
from ..skyfi import skyfi_mcp
from .client import SkyFiClient
from .constants import MCPToolTags

logger = logging.getLogger("mcp-skyfi.skyfi.authentication")

# Context dependency for SkyFi client
SkyFiContext = Annotated[Dict[str, Any], Context]

@skyfi_mcp.tool(
    name="skyfi_authentication_whoami",
    description="Get current user information and validate SkyFi API authentication",
    tags=[
        MCPToolTags.SERVICE_SKYFI,
        MCPToolTags.OPERATION_READ,
        MCPToolTags.FEATURE_AUTHENTICATION
    ]
)
async def whoami_tool(
    context: SkyFiContext
) -> str:
    """
    Get current user information and validate SkyFi API authentication.
    
    This tool validates your SkyFi API key and returns comprehensive user information including:
    - Account details (email, name, type, status)
    - Organization membership and tier
    - Budget and usage information
    - Permissions and quotas
    - API access details
    
    Use this tool to:
    - Verify your API key is working correctly
    - Check your account permissions and limits
    - Monitor budget usage and quotas
    - Confirm organization settings
    
    Returns:
        Formatted string with user information and account status
        
    Raises:
        MCPError: If authentication fails or API request fails
    """
    try:
        logger.info("Validating SkyFi authentication and getting user info")
        
        # Get SkyFi client from context
        skyfi_client = context.get("skyfi_client")
        if not skyfi_client:
            logger.error("SkyFi client not available in context")
            raise SkyFiAPIError("SkyFi service is not properly configured")
        
        # Call the whoami endpoint
        response_data = await skyfi_client.validate_auth()
        
        # Convert response to user model
        user = SkyFiUser.from_api_response(response_data)
        
        logger.info(f"Authentication validated for user: {user.email}")
        
        # Return formatted user information
        return user.to_formatted_string()
        
    except SkyFiAuthenticationError as e:
        logger.error(f"Authentication failed: {e}")
        error_msg = """
❌ SkyFi Authentication Failed

**Cause**: Invalid or expired API key

**Solutions**:
1. Check your SKYFI_API_KEY environment variable is set correctly
2. Generate a new API key at: https://app.skyfi.com/platform/settings/api-keys
3. Ensure your API key has the required permissions
4. Verify your account is active and in good standing

**Current Configuration**:
- Check that your .env file contains: SKYFI_API_KEY=your_actual_key_here
- Ensure the MCP server has access to environment variables
- Verify no extra spaces or quotes around the API key

**Get Help**:
- Visit: https://app.skyfi.com/platform/settings/api-keys
- Documentation: https://docs.skyfi.com/platform-api/authentication
        """.strip()
        raise SkyFiAPIError(error_msg)
        
    except SkyFiAPIError as e:
        # Re-raise API errors with additional context
        logger.error(f"API error during authentication: {e}")
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error during authentication: {e}", exc_info=True)
        error_msg = f"""
❌ Authentication check failed - Unexpected Error

**Error**: {str(e)}

**Troubleshooting**:
1. Check your network connection to app.skyfi.com
2. Verify the SkyFi API service is accessible
3. Try again after a few moments
4. Check server logs for more detailed error information

**Need Help?**
Contact SkyFi support if the issue persists.
        """.strip()
        raise SkyFiAPIError(error_msg)

@skyfi_mcp.tool(
    name="skyfi_authentication_health_check",
    description="Check SkyFi API service health and connectivity",
    tags=[
        MCPToolTags.SERVICE_SKYFI,
        MCPToolTags.OPERATION_READ,
        MCPToolTags.FEATURE_AUTHENTICATION
    ]
)
async def health_check_tool(
    context: SkyFiContext
) -> str:
    """
    Check SkyFi API service health and connectivity.
    
    This tool performs a basic connectivity test to the SkyFi Platform API without
    requiring authentication. Use this to:
    - Verify network connectivity to SkyFi services
    - Check if the API is operational
    - Test basic HTTP client configuration
    - Diagnose connection issues
    
    Returns:
        Service health status and connection information
        
    Raises:
        MCPError: If health check fails or service is unreachable
    """
    try:
        logger.info("Performing SkyFi API health check")
        
        # Get SkyFi client from context
        skyfi_client = context.get("skyfi_client")
        if not skyfi_client:
            logger.error("SkyFi client not available in context")
            raise SkyFiAPIError("SkyFi service is not properly configured")
        
        # Perform health check
        response_data = await skyfi_client.health_check()
        
        logger.info("SkyFi API health check passed")
        
        # Format health check response
        lines = [
            "# SkyFi API Health Check ✅",
            "",
            f"**Status**: Service Operational",
            f"**Endpoint**: {skyfi_client.config.url}",
            f"**Response Time**: {response_data.get('response_time', 'N/A')}",
            f"**Timestamp**: {response_data.get('timestamp', 'N/A')}",
            "",
        ]
        
        if "version" in response_data:
            lines.extend([
                "## API Information",
                f"**Version**: {response_data['version']}",
                f"**Environment**: {response_data.get('environment', 'production')}",
                "",
            ])
        
        if "features" in response_data:
            lines.extend([
                "## Available Features",
                *[f"- {feature}" for feature in response_data['features']],
                "",
            ])
        
        lines.extend([
            "## Connection Details",
            f"**Base URL**: {skyfi_client.config.url}",
            f"**SSL Verification**: {'Enabled' if skyfi_client.config.ssl_verify else 'Disabled'}",
            f"**Timeout**: {skyfi_client.config.timeout} seconds",
            f"**Max Retries**: {skyfi_client.config.max_retries}",
            "",
            "✅ **Ready for API calls** - Your connection to SkyFi is working properly.",
        ])
        
        return "\n".join(lines)
        
    except SkyFiAPIError as e:
        logger.error(f"Health check API error: {e}")
        error_msg = f"""
❌ SkyFi API Health Check Failed

**Error**: {str(e)}

**Possible Causes**:
1. Network connectivity issues
2. SkyFi API service temporarily unavailable
3. Firewall or proxy blocking connections
4. DNS resolution problems

**Troubleshooting**:
1. Check your internet connection
2. Try accessing https://app.skyfi.com in a web browser
3. Verify proxy settings if behind corporate firewall
4. Check if other API calls are working

**Status Page**: Check https://status.skyfi.com for service updates
        """.strip()
        raise SkyFiAPIError(error_msg)
        
    except Exception as e:
        logger.error(f"Unexpected error during health check: {e}", exc_info=True)
        error_msg = f"""
❌ Health check failed - Connection Error

**Error**: {str(e)}

**This usually indicates**:
- Network connectivity problems
- DNS resolution issues  
- Firewall or proxy blocking requests
- Invalid API endpoint configuration

**Check Your Configuration**:
- SKYFI_URL should be: https://app.skyfi.com/platform-api
- Verify network access to app.skyfi.com
- Check firewall settings for outbound HTTPS
        """.strip()
        raise SkyFiAPIError(error_msg)

# Export tool functions for testing
__all__ = [
    "whoami_tool",
    "health_check_tool"
]