# Tool Organization by Feature Domains

## Overview

This document defines how tools are organized by feature domains rather than CRUD operations, following enterprise patterns for maintainable and discoverable API design. Tools are grouped by business functionality and user workflows rather than technical operations.

## 1. Feature Domain Organization Principle

### 1.1 Domain-First vs CRUD-First

**✅ CORRECT: Feature-domain organization**
```python
skyfi/
├── archives.py          # archive_search, archive_get_details, archive_get_thumbnail
├── orders.py            # order_create_archive, order_create_tasking, order_get_status, order_list
├── notifications.py     # notification_create, notification_list, notification_delete
├── feasibility.py       # feasibility_check, feasibility_get_passes
├── pricing.py           # pricing_get, pricing_calculate_cost
├── auth.py             # auth_get_user_info, auth_verify_budget
└── delivery.py         # delivery_validate_config, delivery_test_connection

osm/
├── geocoding.py        # geocode_address, geocode_reverse, geocode_batch
├── places.py           # places_search_pois, places_get_details, places_find_nearby
├── geometry.py         # geometry_generate_aoi, geometry_calculate_area, geometry_buffer
└── routing.py          # routing_get_directions, routing_calculate_distance

weather/
├── current.py          # weather_get_current, weather_get_conditions
├── forecast.py         # weather_get_forecast, weather_get_hourly, weather_get_daily
├── historical.py       # weather_get_historical, weather_get_statistics
└── alerts.py          # weather_get_alerts, weather_subscribe_alerts
```

**❌ WRONG: CRUD-based organization**
```python
skyfi/
├── create.py            # Mixed create operations across different domains
├── read.py              # Mixed read operations across different domains
├── update.py            # Mixed update operations across different domains
└── delete.py            # Mixed delete operations across different domains
```

### 1.2 Domain Definition Criteria

Each feature domain should be:

1. **User-Workflow Focused** - Represents a complete user workflow or business process
2. **Cohesively Related** - All tools in the domain work with the same type of data/concepts
3. **Independently Functional** - Domain can function without tight coupling to other domains
4. **Discoverable** - Users can easily find related functionality
5. **Maintainable** - Clear boundaries for code changes and testing

## 2. SkyFi Service Domain Structure

### 2.1 Archive Search and Discovery Domain

```python
# skyfi/archives.py
"""
Archive search and discovery tools for satellite imagery.

This domain handles:
- Searching satellite imagery archives
- Retrieving archive metadata
- Getting preview thumbnails
- Browsing available datasets
"""

from fastmcp import FastMCP
from typing import Annotated, Optional, List
from ..models.context import SkyFiContext
from ..utils.validation import validate_wkt_polygon, validate_date_range
from ..utils.formatting import format_archive_list, format_archive_details

skyfi_archives_mcp = FastMCP("SkyFi Archive Tools")

@skyfi_archives_mcp.tool(
    name="skyfi_archive_search",
    description="Search satellite imagery archives by location, time, and quality criteria",
    tags=["skyfi", "read", "archives", "search", "discovery"]
)
def archive_search_tool(
    aoi: Annotated[str, "WKT polygon defining area of interest. Must be a valid POLYGON geometry"],
    from_date: Annotated[Optional[str], "Start date for search in ISO format (YYYY-MM-DDTHH:MM:SSZ)"] = None,
    to_date: Annotated[Optional[str], "End date for search in ISO format (YYYY-MM-DDTHH:MM:SSZ)"] = None,
    max_cloud_coverage: Annotated[Optional[int], "Maximum cloud coverage percentage (0-100)"] = None,
    resolutions: Annotated[Optional[List[str]], "List of resolutions: LOW, MEDIUM, HIGH, VERY_HIGH, SUPER_HIGH, ULTRA_HIGH"] = None,
    product_types: Annotated[Optional[List[str]], "Product types: DAY, NIGHT, VIDEO, MULTISPECTRAL, SAR, HYPERSPECTRAL"] = None,
    open_data_only: Annotated[bool, "Filter for free open data (Sentinel-2, etc.) only"] = False,
    page_size: Annotated[int, "Number of results per page (1-100)"] = 20,
    context: Annotated[SkyFiContext, Context]
) -> str:
    """Search satellite imagery archives with comprehensive filtering."""
    # Implementation details...
    pass

@skyfi_archives_mcp.tool(
    name="skyfi_archive_get_details",
    description="Get detailed metadata for a specific satellite imagery archive",
    tags=["skyfi", "read", "archives", "details"]
)
def archive_get_details_tool(
    archive_id: Annotated[str, "UUID of the archive to retrieve details for"],
    include_thumbnails: Annotated[bool, "Include thumbnail URLs in response"] = True,
    context: Annotated[SkyFiContext, Context]
) -> str:
    """Get comprehensive details about a specific archive."""
    # Implementation details...
    pass

@skyfi_archives_mcp.tool(
    name="skyfi_archive_get_thumbnail",
    description="Get preview thumbnail URL for satellite imagery archive",
    tags=["skyfi", "read", "archives", "thumbnail", "preview"]
)
def archive_get_thumbnail_tool(
    archive_id: Annotated[str, "UUID of the archive to get thumbnail for"],
    thumbnail_type: Annotated[str, "Thumbnail type: small, medium, large"] = "medium",
    context: Annotated[SkyFiContext, Context]
) -> str:
    """Get preview thumbnail for visual inspection of archive quality."""
    # Implementation details...
    pass
```

### 2.2 Order Management Domain

```python
# skyfi/orders.py
"""
Order creation and management tools for satellite imagery.

This domain handles:
- Creating archive orders for existing imagery
- Creating tasking orders for future captures
- Tracking order status and progress
- Managing order history
- Handling delivery configuration
"""

from fastmcp import FastMCP
from typing import Annotated, Optional, Dict, Any

skyfi_orders_mcp = FastMCP("SkyFi Order Management Tools")

@skyfi_orders_mcp.tool(
    name="skyfi_order_create_archive",
    description="Create an order for existing satellite imagery from archives",
    tags=["skyfi", "write", "orders", "archive", "purchase"]
)
def order_create_archive_tool(
    aoi: Annotated[str, "WKT polygon defining area to order"],
    archive_id: Annotated[str, "UUID of archive to order"],
    delivery_driver: Annotated[str, "Delivery method: S3, GS (Google Cloud), AZURE, or NONE"],
    delivery_params: Annotated[Dict[str, Any], "Delivery configuration parameters specific to the chosen driver"],
    metadata: Annotated[Optional[Dict[str, Any]], "Optional metadata to attach to order"] = None,
    webhook_url: Annotated[Optional[str], "Optional webhook URL for order status updates"] = None,
    context: Annotated[SkyFiContext, Context]
) -> str:
    """Create an order for existing satellite imagery."""
    # Implementation details...
    pass

@skyfi_orders_mcp.tool(
    name="skyfi_order_create_tasking",
    description="Create a tasking order for future satellite image capture",
    tags=["skyfi", "write", "orders", "tasking", "future"]
)
def order_create_tasking_tool(
    aoi: Annotated[str, "WKT polygon defining area to capture"],
    window_start: Annotated[str, "Start of capture window in ISO format"],
    window_end: Annotated[str, "End of capture window in ISO format"],
    product_type: Annotated[str, "Product type: DAY, NIGHT, VIDEO, MULTISPECTRAL, SAR"],
    resolution: Annotated[str, "Desired resolution level"],
    delivery_driver: Annotated[str, "Delivery method: S3, GS, AZURE, or NONE"],
    delivery_params: Annotated[Dict[str, Any], "Delivery configuration parameters"],
    max_cloud_coverage: Annotated[int, "Maximum acceptable cloud coverage percentage"] = 20,
    priority_item: Annotated[bool, "Mark as priority order for faster processing"] = False,
    context: Annotated[SkyFiContext, Context]
) -> str:
    """Create a tasking order for future satellite capture."""
    # Implementation details...
    pass

@skyfi_orders_mcp.tool(
    name="skyfi_order_get_status",
    description="Get current status and details of a specific order",
    tags=["skyfi", "read", "orders", "status", "tracking"]
)
def order_get_status_tool(
    order_id: Annotated[str, "UUID of the order to check"],
    include_history: Annotated[bool, "Include full status change history"] = True,
    context: Annotated[SkyFiContext, Context]
) -> str:
    """Get detailed status information for an order."""
    # Implementation details...
    pass

@skyfi_orders_mcp.tool(
    name="skyfi_order_list",
    description="List orders with optional filtering and pagination",
    tags=["skyfi", "read", "orders", "list", "history"]
)
def order_list_tool(
    order_type: Annotated[Optional[str], "Filter by order type: ARCHIVE or TASKING"] = None,
    status: Annotated[Optional[str], "Filter by status: CREATED, PROCESSING, DELIVERED, FAILED"] = None,
    page_size: Annotated[int, "Number of orders per page (1-100)"] = 20,
    page_number: Annotated[int, "Page number (0-based)"] = 0,
    context: Annotated[SkyFiContext, Context]
) -> str:
    """List user's orders with filtering options."""
    # Implementation details...
    pass
```

### 2.3 Notification and Monitoring Domain

```python
# skyfi/notifications.py
"""
Notification and monitoring tools for archive updates.

This domain handles:
- Creating notification subscriptions for new imagery
- Managing webhook configurations
- Monitoring notification delivery
- Filtering notification criteria
"""

@skyfi_notifications_mcp.tool(
    name="skyfi_notification_create",
    description="Create notification subscription for new satellite imagery in area of interest",
    tags=["skyfi", "write", "notifications", "webhook", "monitoring"]
)
def notification_create_tool(
    aoi: Annotated[str, "WKT polygon for area to monitor"],
    webhook_url: Annotated[str, "Webhook URL to receive notifications"],
    product_types: Annotated[Optional[List[str]], "Filter by product types"] = None,
    min_gsd: Annotated[Optional[float], "Minimum ground sample distance in meters"] = None,
    max_gsd: Annotated[Optional[float], "Maximum ground sample distance in meters"] = None,
    context: Annotated[SkyFiContext, Context]
) -> str:
    """Create subscription for new imagery notifications."""
    # Implementation details...
    pass
```

### 2.4 Feasibility and Planning Domain

```python
# skyfi/feasibility.py
"""
Feasibility analysis and satellite pass prediction tools.

This domain handles:
- Checking feasibility of satellite tasking requests
- Getting satellite pass predictions
- Analyzing capture probability
- Weather impact assessment
"""

@skyfi_feasibility_mcp.tool(
    name="skyfi_feasibility_check",
    description="Check feasibility of satellite image capture for given parameters",
    tags=["skyfi", "read", "feasibility", "planning", "analysis"]
)
def feasibility_check_tool(
    aoi: Annotated[str, "WKT polygon for area of interest"],
    start_date: Annotated[str, "Start of feasibility window in ISO format"],
    end_date: Annotated[str, "End of feasibility window in ISO format"],
    product_type: Annotated[str, "Desired product type"],
    resolution: Annotated[str, "Desired resolution"],
    max_cloud_coverage: Annotated[int, "Maximum acceptable cloud coverage"] = 20,
    context: Annotated[SkyFiContext, Context]
) -> str:
    """Analyze feasibility of satellite capture request."""
    # Implementation details...
    pass

@skyfi_feasibility_mcp.tool(
    name="skyfi_feasibility_get_passes",
    description="Get satellite pass predictions for area and time window",
    tags=["skyfi", "read", "feasibility", "passes", "schedule"]
)
def feasibility_get_passes_tool(
    aoi: Annotated[str, "WKT polygon for area of interest"],
    from_date: Annotated[str, "Start date for pass predictions"],
    to_date: Annotated[str, "End date for pass predictions"],
    product_types: Annotated[Optional[List[str]], "Filter by product types"] = None,
    context: Annotated[SkyFiContext, Context]
) -> str:
    """Get detailed satellite pass predictions."""
    # Implementation details...
    pass
```

## 3. OpenStreetMap Service Domain Structure

### 3.1 Geocoding and Address Resolution Domain

```python
# osm/geocoding.py
"""
Geocoding and address resolution tools.

This domain handles:
- Forward geocoding (address to coordinates)
- Reverse geocoding (coordinates to address)
- Batch geocoding operations
- Address validation and normalization
"""

osm_geocoding_mcp = FastMCP("OSM Geocoding Tools")

@osm_geocoding_mcp.tool(
    name="osm_geocode_address",
    description="Convert address or place name to geographic coordinates",
    tags=["osm", "read", "geocoding", "address", "coordinates"]
)
def geocode_address_tool(
    address: Annotated[str, "Address or place name to geocode"],
    country_codes: Annotated[Optional[List[str]], "Limit search to specific countries (ISO 3166-1 alpha-2)"] = None,
    limit: Annotated[int, "Maximum number of results to return (1-10)"] = 5,
    include_details: Annotated[bool, "Include detailed address components"] = True,
    context: Annotated[OSMContext, Context]
) -> str:
    """Convert address to coordinates with confidence scoring."""
    # Implementation details...
    pass

@osm_geocoding_mcp.tool(
    name="osm_geocode_reverse",
    description="Convert geographic coordinates to nearest address",
    tags=["osm", "read", "geocoding", "reverse", "address"]
)
def geocode_reverse_tool(
    latitude: Annotated[float, "Latitude in decimal degrees (-90 to 90)"],
    longitude: Annotated[float, "Longitude in decimal degrees (-180 to 180)"],
    zoom: Annotated[int, "Detail level: 1-18 (higher = more detailed address)"] = 14,
    include_address_components: Annotated[bool, "Include structured address components"] = True,
    context: Annotated[OSMContext, Context]
) -> str:
    """Convert coordinates to structured address information."""
    # Implementation details...
    pass
```

### 3.2 Places and Points of Interest Domain

```python
# osm/places.py
"""
Places and points of interest search tools.

This domain handles:
- Searching for POIs by category
- Finding nearby amenities and services
- Getting place details and metadata
- Discovering local businesses and landmarks
"""

@osm_places_mcp.tool(
    name="osm_places_search_pois",
    description="Search for points of interest near a location",
    tags=["osm", "read", "places", "poi", "search"]
)
def places_search_pois_tool(
    latitude: Annotated[float, "Center latitude for search"],
    longitude: Annotated[float, "Center longitude for search"],
    radius: Annotated[float, "Search radius in meters (max 50000)"],
    categories: Annotated[Optional[List[str]], "POI categories: restaurant, hotel, hospital, etc."] = None,
    limit: Annotated[int, "Maximum results to return (1-100)"] = 20,
    context: Annotated[OSMContext, Context]
) -> str:
    """Find points of interest within radius of location."""
    # Implementation details...
    pass
```

### 3.3 Geometry and Spatial Operations Domain

```python
# osm/geometry.py
"""
Geometric operations and AOI generation tools.

This domain handles:
- Generating Areas of Interest (AOI) polygons
- Calculating areas and distances
- Creating buffers around points
- Geometric validation and conversion
"""

@osm_geometry_mcp.tool(
    name="osm_geometry_generate_aoi",
    description="Generate WKT polygon for area of interest around a center point",
    tags=["osm", "utility", "geometry", "aoi", "polygon"]
)
def geometry_generate_aoi_tool(
    center_latitude: Annotated[float, "Center latitude for AOI"],
    center_longitude: Annotated[float, "Center longitude for AOI"],
    size_km2: Annotated[float, "Area size in square kilometers"],
    shape: Annotated[str, "Shape type: square, circle, or rectangle"] = "square",
    orientation: Annotated[float, "Rotation angle in degrees (0-360)"] = 0,
    context: Annotated[OSMContext, Context]
) -> str:
    """Generate geometric AOI polygon for satellite imagery search."""
    # Implementation details...
    pass

@osm_geometry_mcp.tool(
    name="osm_geometry_calculate_area",
    description="Calculate area of WKT polygon in square kilometers",
    tags=["osm", "utility", "geometry", "area", "calculation"]
)
def geometry_calculate_area_tool(
    wkt_polygon: Annotated[str, "WKT polygon to calculate area for"],
    context: Annotated[OSMContext, Context]
) -> str:
    """Calculate precise area of polygon using geodetic calculations."""
    # Implementation details...
    pass
```

## 4. Weather Service Domain Structure

### 4.1 Current Weather Domain

```python
# weather/current.py
"""
Current weather conditions and real-time data.

This domain handles:
- Current weather conditions
- Real-time atmospheric data
- Cloud coverage for satellite planning
- Visibility and atmospheric clarity
"""

weather_current_mcp = FastMCP("Weather Current Conditions")

@weather_current_mcp.tool(
    name="weather_get_current",
    description="Get current weather conditions for a location",
    tags=["weather", "read", "current", "conditions"]
)
def weather_get_current_tool(
    latitude: Annotated[float, "Latitude in decimal degrees"],
    longitude: Annotated[float, "Longitude in decimal degrees"],
    units: Annotated[str, "Temperature units: metric, imperial, or kelvin"] = "metric",
    include_details: Annotated[bool, "Include detailed atmospheric data"] = True,
    context: Annotated[WeatherContext, Context]
) -> str:
    """Get current weather with satellite-relevant metrics."""
    # Implementation details...
    pass
```

### 4.2 Weather Forecast Domain

```python
# weather/forecast.py
"""
Weather forecasting and future conditions.

This domain handles:
- Multi-day weather forecasts
- Hourly weather predictions
- Cloud coverage forecasts for satellite planning
- Optimal capture window identification
"""

@weather_forecast_mcp.tool(
    name="weather_get_forecast",
    description="Get weather forecast for optimal satellite capture planning",
    tags=["weather", "read", "forecast", "planning"]
)
def weather_get_forecast_tool(
    latitude: Annotated[float, "Latitude for forecast location"],
    longitude: Annotated[float, "Longitude for forecast location"],
    days: Annotated[int, "Number of forecast days (1-7)"] = 7,
    include_hourly: Annotated[bool, "Include hourly breakdown"] = True,
    satellite_planning: Annotated[bool, "Focus on satellite-relevant conditions"] = True,
    context: Annotated[WeatherContext, Context]
) -> str:
    """Get weather forecast optimized for satellite imagery planning."""
    # Implementation details...
    pass
```

## 5. Tool Definition Standards and Patterns

### 5.1 Tool Naming Convention

```python
# Pattern: {service}_{domain}_{action}
# Examples:
skyfi_archive_search        # SkyFi service, Archive domain, Search action
skyfi_order_create_archive  # SkyFi service, Order domain, Create Archive action
osm_geocode_address         # OSM service, Geocoding domain, Address action
weather_get_current         # Weather service, Current domain, Get action
```

### 5.2 Tool Metadata Standards

```python
@service_domain_mcp.tool(
    name="{service}_{domain}_{action}",
    description="{Action verb} {object/concept} {additional context}",
    tags=[
        "{service}",           # Service identifier
        "{read|write}",        # Operation level
        "{domain}",           # Feature domain
        "{specific_tags}",    # Domain-specific functionality
        "{capability_tags}"   # Special capabilities (batch, paginated, etc.)
    ]
)
```

### 5.3 Tool Parameter Patterns

```python
def domain_action_tool(
    # 1. Required parameters (business entities)
    primary_id: Annotated[str, "Primary entity identifier with validation rules"],
    
    # 2. Required parameters (user input)
    user_input: Annotated[str, "User-provided data with clear examples"],
    
    # 3. Optional parameters (filters and options)
    filter_param: Annotated[Optional[type], "Filter description with defaults"] = None,
    
    # 4. Optional parameters (behavior control)
    include_details: Annotated[bool, "Control response verbosity"] = True,
    page_size: Annotated[int, "Pagination control with limits"] = 20,
    
    # 5. Context injection (always last)
    context: Annotated[ServiceContext, Context]
) -> str:
```

### 5.4 Error Handling Patterns

```python
def domain_tool_implementation():
    """Standard error handling pattern for all tools."""
    try:
        # 1. Input validation
        if not required_param or not required_param.strip():
            raise ValueError("Required parameter cannot be empty")
        
        validate_domain_specific_input(required_param)
        
        # 2. Business logic validation
        if not context.has_permission_for_operation():
            raise MCPError("Insufficient permissions for this operation")
        
        # 3. Read-only mode check for write operations
        if context.read_only and "write" in get_current_tool_tags():
            raise MCPError("Cannot perform write operation in read-only mode")
        
        # 4. Execute business logic
        async with context.service_client as client:
            result = await client.domain_specific_operation(params)
        
        # 5. Format response consistently
        return format_domain_response(result)
        
    except ServiceAuthenticationError:
        raise MCPError(f"Authentication failed for {context.service_name}")
    except ServiceNotFoundError as e:
        raise MCPError(f"Resource not found: {str(e)}")
    except ServicePermissionError as e:
        raise MCPError(f"Access denied: {str(e)}")
    except ServiceValidationError as e:
        raise MCPError(f"Invalid request: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in {tool_name}: {e}", exc_info=True)
        raise MCPError(f"Operation failed: {str(e)}")
```

## 6. Domain Integration and Cross-Cutting Concerns

### 6.1 Service Registration Pattern

```python
# services/__init__.py
"""Service registration and domain mounting."""

from ..skyfi.archives import skyfi_archives_mcp
from ..skyfi.orders import skyfi_orders_mcp
from ..skyfi.notifications import skyfi_notifications_mcp
from ..skyfi.feasibility import skyfi_feasibility_mcp
from ..skyfi.pricing import skyfi_pricing_mcp

from ..osm.geocoding import osm_geocoding_mcp
from ..osm.places import osm_places_mcp
from ..osm.geometry import osm_geometry_mcp

from ..weather.current import weather_current_mcp
from ..weather.forecast import weather_forecast_mcp
from ..weather.historical import weather_historical_mcp

# Domain registry for dynamic service discovery
DOMAIN_REGISTRY = {
    "skyfi": {
        "archives": skyfi_archives_mcp,
        "orders": skyfi_orders_mcp,
        "notifications": skyfi_notifications_mcp,
        "feasibility": skyfi_feasibility_mcp,
        "pricing": skyfi_pricing_mcp,
    },
    "osm": {
        "geocoding": osm_geocoding_mcp,
        "places": osm_places_mcp,
        "geometry": osm_geometry_mcp,
    },
    "weather": {
        "current": weather_current_mcp,
        "forecast": weather_forecast_mcp,
        "historical": weather_historical_mcp,
    }
}

def get_available_domains(service_name: str) -> Dict[str, FastMCP]:
    """Get available domains for a service."""
    return DOMAIN_REGISTRY.get(service_name, {})

def get_all_mcps() -> List[FastMCP]:
    """Get all MCP instances for mounting."""
    mcps = []
    for service_domains in DOMAIN_REGISTRY.values():
        mcps.extend(service_domains.values())
    return mcps
```

This domain-based organization provides:

1. **User-Centric Grouping** - Tools grouped by user workflows and business processes
2. **Logical Discoverability** - Related functionality is co-located and easy to find
3. **Maintainable Architecture** - Clear boundaries for testing, changes, and documentation
4. **Consistent Patterns** - Standardized naming, parameter ordering, and error handling
5. **Service Independence** - Each domain can evolve independently while maintaining consistent patterns
6. **Cross-Domain Integration** - Clear interfaces for tools that span multiple domains
7. **Dynamic Service Discovery** - Runtime detection of available domains and tools

The architecture supports both simple single-domain operations and complex cross-domain workflows while maintaining clear separation of concerns.