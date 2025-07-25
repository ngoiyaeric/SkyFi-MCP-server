"""
SkyFi Factory Integration Example

This module demonstrates how to integrate the SkyFiClientFactory with MCP tools
for efficient, cached, and pooled client creation based on collective intelligence patterns.

This serves as both documentation and a working example of the factory integration.
"""


import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from . import skyfi_mcp
from .dependencies import get_skyfi_client, SkyFiContext
from .constants import MCPToolTags
from ..exceptions import SkyFiAPIError, SkyFiMCPError

logger = logging.getLogger("mcp-skyfi.skyfi.factory_integration_example")


class ArchiveSearchRequest(BaseModel):
    """Request model for archive search with validation."""
    
    geometry: Dict[str, Any] = Field(
        description="GeoJSON geometry object defining the area of interest"
    )
    start_date: Optional[str] = Field(
        None,
        description="Start date in YYYY-MM-DD format"
    )
    end_date: Optional[str] = Field(
        None,
        description="End date in YYYY-MM-DD format"
    )
    max_cloud_cover: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="Maximum cloud cover percentage (0-100)"
    )
    limit: int = Field(
        50,
        ge=1,
        le=500,
        description="Maximum number of results to return"
    )


@skyfi_mcp.tool(
    name="skyfi_archive_search_with_factory",
    description="Search SkyFi archive using client factory for optimized performance",
    tags=[
        MCPToolTags.SERVICE_SKYFI,
        MCPToolTags.OPERATION_READ,
        MCPToolTags.FEATURE_AUTHENTICATION
    ]
)
async def search_archives_with_factory(
    context: SkyFiContext,
    geometry: Dict[str, Any],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_cloud_cover: Optional[float] = None,
    limit: int = 50
) -> str:
    """
    Search SkyFi satellite archive using the client factory for optimized performance.
    
    This tool demonstrates the collective intelligence factory pattern with:
    - Credential caching (5-minute TTL)
    - HTTP connection pooling
    - Thread-safe operations
    - Fallback authentication strategies
    - Performance monitoring
    
    The factory automatically:
    1. Determines best authentication method (user context > OAuth > API key > personal token)
    2. Checks credential cache for validation results
    3. Reuses HTTP connections from pool
    4. Handles authentication failures with fallback strategies
    5. Logs performance metrics for optimization
    
    Args:
        context: MCP request context with user authentication
        geometry: GeoJSON geometry defining search area
        start_date: Optional start date filter (YYYY-MM-DD)
        end_date: Optional end date filter (YYYY-MM-DD)
        max_cloud_cover: Optional maximum cloud cover percentage
        limit: Maximum number of results (1-500)
        
    Returns:
        Formatted string with search results and factory performance info
        
    Raises:
        SkyFiMCPError: If search fails or authentication invalid
    """
    try:
        logger.info(f"Archive search request with factory - limit: {limit}")
        
        # Validate request parameters
        request = ArchiveSearchRequest(
            geometry=geometry,
            start_date=start_date,
            end_date=end_date,
            max_cloud_cover=max_cloud_cover,
            limit=limit
        )
        
        # Get SkyFi client using factory pattern
        # This automatically handles:
        # - Credential precedence and caching
        # - HTTP connection pooling
        # - Authentication validation
        # - Fallback strategies
        client = await get_skyfi_client(context)
        
        # Execute search using factory-optimized client
        async with client:
            # Log factory metadata from client context
            user_context = getattr(client, 'user_context', {})
            factory_info = {
                "factory_created": user_context.get("factory_created", False),
                "credential_cached": user_context.get("credential_cached", False),
                "validation_status": user_context.get("validation_status", "unknown"),
                "auth_type": user_context.get("auth_type", "config")
            }
            
            logger.info(f"Using factory-optimized client: {factory_info}")
            
            # Execute archive search
            search_results = await client.search_archives(
                geometry=request.geometry,
                start_date=request.start_date,
                end_date=request.end_date,
                max_cloud_cover=request.max_cloud_cover,
                limit=request.limit
            )
            
            # Format response with factory performance info
            result_count = len(search_results.get("results", []))
            total_available = search_results.get("total_count", result_count)
            
            response_lines = [
                "# SkyFi Archive Search Results (Factory-Optimized)",
                "",
                f"**Search Status**: ✅ Completed successfully",
                f"**Results Found**: {result_count} of {total_available} available",
                f"**Factory Optimizations**: {'✅' if factory_info['factory_created'] else '❌'} Client Factory",
                "",
                "## Factory Performance Info",
                f"- **Authentication**: {factory_info['auth_type']} ({'cached' if factory_info['credential_cached'] else 'fresh'})",
                f"- **Validation Status**: {factory_info['validation_status']}",
                f"- **Connection**: {'pooled' if factory_info['factory_created'] else 'direct'}",
                "",
                "## Search Parameters",
                f"- **Area**: {_describe_geometry(request.geometry)}",
                f"- **Date Range**: {request.start_date or 'Any'} to {request.end_date or 'Any'}",
                f"- **Max Cloud Cover**: {request.max_cloud_cover}%" if request.max_cloud_cover else "- **Max Cloud Cover**: Any",
                f"- **Result Limit**: {request.limit}",
                "",
                "## Results Summary"
            ]
            
            # Add result summaries
            for i, result in enumerate(search_results.get("results", [])[:5], 1):
                acquisition_date = result.get("acquisition_date", "Unknown")
                cloud_cover = result.get("cloud_cover", "N/A")
                resolution = result.get("resolution", "N/A")
                satellite = result.get("satellite", "Unknown")
                
                response_lines.append(
                    f"{i}. **{satellite}** - {acquisition_date} "
                    f"(Cloud: {cloud_cover}%, Resolution: {resolution}m)"
                )
            
            if result_count > 5:
                response_lines.append(f"... and {result_count - 5} more results")
            
            # Add pagination info if applicable
            if total_available > result_count:
                response_lines.extend([
                    "",
                    "## Pagination",
                    f"Showing results 1-{result_count} of {total_available} total.",
                    "Use offset parameter to retrieve additional results."
                ])
            
            # Add performance note
            response_lines.extend([
                "",
                "---",
                "*🚀 This search used SkyFi Client Factory optimizations including credential caching, connection pooling, and performance monitoring.*"
            ])
            
            logger.info(f"Archive search completed successfully: {result_count} results")
            return "\n".join(response_lines)
            
    except Exception as e:
        logger.error(f"Archive search failed: {e}", exc_info=True)
        
        # Provide helpful error information
        error_response = [
            "# SkyFi Archive Search Error",
            "",
            f"**Error**: {str(e)}",
            "",
            "## Troubleshooting",
            "1. Check your SkyFi API authentication",
            "2. Verify the geometry is valid GeoJSON",
            "3. Ensure date formats are YYYY-MM-DD",
            "4. Check network connectivity to SkyFi API",
            "",
            "## Factory Status",
            "The client factory handles authentication and connection optimization automatically.",
            "If this error persists, the factory will attempt fallback authentication methods."
        ]
        
        if isinstance(e, SkyFiAPIError):
            raise SkyFiMCPError("\n".join(error_response))
        else:
            raise SkyFiMCPError(f"Archive search failed: {str(e)}")


@skyfi_mcp.tool(
    name="skyfi_factory_stats",
    description="Get SkyFi client factory performance statistics and monitoring info",
    tags=[
        MCPToolTags.SERVICE_SKYFI,
        MCPToolTags.OPERATION_READ,
        MCPToolTags.FEATURE_MONITORING
    ]
)
async def get_factory_statistics(context: SkyFiContext) -> str:
    """
    Get comprehensive SkyFi client factory statistics for performance monitoring.
    
    Returns detailed information about:
    - Client creation metrics
    - Credential cache performance (hit rates, validation counts)
    - HTTP connection pool statistics
    - Authentication method usage
    - Error rates and performance trends
    
    This is useful for:
    - Monitoring factory performance
    - Debugging authentication issues
    - Optimizing cache settings
    - Understanding usage patterns
    
    Args:
        context: MCP request context
        
    Returns:
        Formatted statistics report
    """
    try:
        logger.info("Retrieving factory statistics")
        
        # Import here to avoid circular imports
        from .factory import get_client_factory
        
        factory = get_client_factory()
        stats = factory.get_factory_stats()
        
        # Format comprehensive statistics report
        response_lines = [
            "# SkyFi Client Factory Statistics",
            "",
            f"**Report Generated**: {_format_timestamp(stats['timestamp'])}",
            "",
            "## Factory Performance",
            f"- **Total Clients Created**: {stats['factory']['clients_created']:,}",
            f"- **Cache Hit Rate**: {stats['cache']['cache_hit_rate']:.1%}",
            f"- **Cache Hits**: {stats['factory']['cache_hits']:,}",
            f"- **Cache Misses**: {stats['factory']['cache_misses']:,}",
            "",
            "## Credential Validation",
            f"- **Validation Attempts**: {stats['factory']['validation_attempts']:,}",
            f"- **Successful Validations**: {stats['factory']['validation_successes']:,}",
            f"- **Failed Validations**: {stats['factory']['validation_failures']:,}",
            f"- **Fallback Attempts**: {stats['factory']['fallback_attempts']:,}",
            "",
            "## Credential Cache",
            f"- **Current Cache Size**: {stats['cache']['cache_size']:,} entries",
            f"- **Maximum Cache Size**: {stats['cache']['cache_maxsize']:,} entries",
            f"- **Cache TTL**: {stats['cache']['cache_ttl']:,} seconds",
            f"- **Cache Utilization**: {(stats['cache']['cache_size'] / stats['cache']['cache_maxsize']):.1%}",
            "",
            "## HTTP Connection Pool",
            f"- **Active Connections**: {stats['connections']['active_clients']:,}",
            f"- **Total Created**: {stats['connections']['total_created']:,}",
            f"- **Pool Size**: {stats['connections']['total_in_pool']:,}",
            f"- **Cleaned Up**: {stats['connections']['cleaned_up']:,}",
            f"- **Max Connections**: {stats['connections']['max_connections']:,}",
            f"- **Max Keep-Alive**: {stats['connections']['max_keepalive']:,}",
            "",
            "## Performance Insights"
        ]
        
        # Add performance insights based on statistics
        hit_rate = stats['cache']['cache_hit_rate']
        if hit_rate > 0.8:
            response_lines.append("✅ **Excellent cache performance** - High hit rate reduces API calls")
        elif hit_rate > 0.5:
            response_lines.append("⚠️ **Good cache performance** - Consider increasing cache TTL if appropriate")
        else:
            response_lines.append("❌ **Low cache performance** - Check for credential rotation or short TTL")
        
        validation_success_rate = (
            stats['factory']['validation_successes'] / 
            max(stats['factory']['validation_attempts'], 1)
        )
        
        if validation_success_rate > 0.95:
            response_lines.append("✅ **Authentication is stable** - Very few validation failures")
        elif validation_success_rate > 0.8:
            response_lines.append("⚠️ **Some authentication issues** - Monitor credential expiration")
        else:
            response_lines.append("❌ **Authentication problems** - Check API keys and network connectivity")
        
        # Connection pool efficiency
        pool_utilization = stats['connections']['active_clients'] / max(stats['connections']['max_connections'], 1)
        if pool_utilization < 0.5:
            response_lines.append("✅ **Connection pool has capacity** - Good for handling traffic spikes")
        elif pool_utilization < 0.8:
            response_lines.append("⚠️ **Moderate connection usage** - Monitor for potential bottlenecks")
        else:
            response_lines.append("🔥 **High connection usage** - Consider increasing pool size")
        
        response_lines.extend([
            "",
            "---",
            "*💡 Use this information to optimize factory settings and monitor performance trends.*"
        ])
        
        logger.info("Factory statistics retrieved successfully")
        return "\n".join(response_lines)
        
    except Exception as e:
        logger.error(f"Failed to get factory statistics: {e}")
        return f"❌ **Error retrieving factory statistics**: {str(e)}"


def _describe_geometry(geometry: Dict[str, Any]) -> str:
    """Create human-readable description of GeoJSON geometry."""
    geom_type = geometry.get("type", "Unknown")
    
    if geom_type == "Point":
        coords = geometry.get("coordinates", [])
        if len(coords) >= 2:
            return f"Point ({coords[1]:.4f}, {coords[0]:.4f})"
    elif geom_type == "Polygon":
        return "Polygon area"
    elif geom_type == "MultiPolygon":
        return "Multi-polygon area"
    elif geom_type == "LineString":
        return "Line string"
    
    return f"{geom_type} geometry"


def _format_timestamp(timestamp: float) -> str:
    """Format Unix timestamp to human-readable string."""
    from datetime import datetime
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S UTC")


# Export tools for registration
__all__ = [
    "search_archives_with_factory",
    "get_factory_statistics"
]