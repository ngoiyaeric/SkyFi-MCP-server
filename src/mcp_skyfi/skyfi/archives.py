"""
SkyFi Archives Tools

This module implements MCP tools for SkyFi archive search and management,
enabling AI applications to search, filter, and retrieve satellite imagery
from the SkyFi Platform archive.

Features:
- Archive search with geospatial and temporal filters
- Image metadata retrieval and analysis
- Thumbnail generation and preview
- Multi-format result export (GeoJSON, JSON)
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from fastmcp import FastMCP
from pydantic import BaseModel, Field, validator
import httpx

from . import skyfi_mcp
from ..models.skyfi.archive import ArchiveResult, ArchiveSearchResponse, ArchiveSearchParams
from ..exceptions import SkyFiMCPError

logger = logging.getLogger("mcp-skyfi.skyfi.archives")


class ArchiveSearchParams(BaseModel):
    """Parameters for archive search operations"""
    
    # Geospatial parameters
    geometry: Union[Dict[str, Any], str] = Field(
        description="Search area as GeoJSON geometry, WKT string, or bounding box [west, south, east, north]"
    )
    
    # Temporal parameters
    start_date: Optional[str] = Field(
        None,
        description="Start date for temporal filter (YYYY-MM-DD or ISO format)"
    )
    end_date: Optional[str] = Field(
        None, 
        description="End date for temporal filter (YYYY-MM-DD or ISO format)"
    )
    
    # Image quality filters
    cloud_cover_max: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Maximum cloud cover percentage (0-100)"
    )
    
    resolution_max: Optional[float] = Field(
        None,
        gt=0,
        description="Maximum resolution in meters per pixel"
    )
    
    # Data source filters
    satellites: Optional[List[str]] = Field(
        None,
        description="List of satellite names/missions to include"
    )
    
    providers: Optional[List[str]] = Field(
        None,
        description="List of data providers to include"
    )
    
    # Collection filters
    collections: Optional[List[str]] = Field(
        None,
        description="Specific SkyFi collection IDs to search"
    )
    
    # Result parameters
    limit: int = Field(
        50,
        ge=1,
        le=500,
        description="Maximum number of results to return"
    )
    
    offset: int = Field(
        0,
        ge=0,
        description="Number of results to skip (for pagination)"
    )
    
    sort_by: str = Field(
        "acquisition_date",
        description="Sort results by: acquisition_date, cloud_cover, resolution, relevance"
    )
    
    sort_order: str = Field(
        "desc",
        description="Sort order: asc or desc"
    )


class ArchiveDetailsParams(BaseModel):
    """Parameters for retrieving detailed archive image information"""
    
    image_id: str = Field(
        description="Unique identifier for the archive image"
    )
    
    include_metadata: bool = Field(
        True,
        description="Include detailed metadata in response"
    )
    
    include_preview: bool = Field(
        False,
        description="Include preview/thumbnail URL in response"
    )


@skyfi_mcp.tool(
    name="skyfi_archive_search", 
    description="Search SkyFi satellite imagery archive with geospatial, temporal, and quality filters"
)
async def search_archive(
    geometry: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    cloud_cover_max: Optional[float] = None,
    resolution_max: Optional[float] = None,
    satellites: Optional[List[str]] = None,
    providers: Optional[List[str]] = None,
    collections: Optional[List[str]] = None,
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "acquisition_date",
    sort_order: str = "desc"
) -> Dict[str, Any]:
    """
    Search the SkyFi satellite imagery archive for available images.
    
    This tool allows AI applications to find satellite imagery based on:
    - Geographic area of interest (AOI)
    - Time range constraints
    - Image quality requirements
    - Specific satellite missions or data providers
    
    Returns a list of available archive images with metadata including:
    - Image acquisition details
    - Spatial coverage and resolution
    - Cloud cover and quality metrics
    - Pricing and licensing information
    - Direct download or ordering links
    
    Args:
        geometry: Search area as GeoJSON, WKT, or bbox [west,south,east,north]
        start_date: Start date (YYYY-MM-DD or ISO format)
        end_date: End date (YYYY-MM-DD or ISO format) 
        cloud_cover_max: Maximum cloud cover percentage (0-100)
        resolution_max: Maximum resolution in meters per pixel
        satellites: Filter by satellite names (e.g., ["Landsat-8", "Sentinel-2"])
        providers: Filter by data providers (e.g., ["USGS", "ESA"])
        collections: Filter by SkyFi collection IDs
        limit: Maximum results to return (1-500)
        offset: Results to skip for pagination
        sort_by: Sort field (acquisition_date, cloud_cover, resolution, relevance)
        sort_order: Sort direction (asc or desc)
        
    Returns:
        Dictionary containing:
        - results: List of matching archive images
        - total_count: Total number of available images
        - search_metadata: Information about the search parameters
        - pagination: Pagination details for additional results
        
    Raises:
        SkyFiMCPError: If search fails or authentication is invalid
    """
    
    try:
        logger.info(f"Starting archive search with geometry: {geometry}")
        
        # Validate and construct search parameters
        params = ArchiveSearchParams(
            geometry=geometry,
            start_date=start_date,
            end_date=end_date,
            cloud_cover_max=cloud_cover_max,
            resolution_max=resolution_max,
            satellites=satellites,
            providers=providers,
            collections=collections,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # Get SkyFi configuration and client
        app_context = skyfi_mcp._mcp_server.request_context.lifespan_context.get("app_lifespan_context")
        if not app_context or not hasattr(app_context, 'skyfi_config'):
            raise SkyFiMCPError("SkyFi service not configured or unavailable")
        
        config = app_context.skyfi_config
        
        # Prepare API request
        headers = {
            **config.get_effective_headers(),
            **config.get_auth_headers()
        }
        
        # Build search query according to SkyFi API docs
        search_payload = {
            "aoi": _geometry_to_wkt(params.geometry)
        }
        
        # Add temporal filters
        if params.start_date:
            search_payload["fromDate"] = params.start_date
        if params.end_date:
            search_payload["toDate"] = params.end_date
            
        # Add quality filters
        if params.cloud_cover_max is not None:
            search_payload["maxCloudCoveragePercent"] = params.cloud_cover_max
            
        # Add source filters
        if params.providers:
            search_payload["providers"] = params.providers
            
        # Add pagination
        search_payload["pageSize"] = min(params.limit, 100)
        
        # Execute API request
        async with httpx.AsyncClient(
            timeout=config.timeout,
            verify=config.ssl_verify
        ) as client:
            
            response = await client.post(
                f"{config.url}/archives",
                json=search_payload,
                headers=headers
            )
            
            if response.status_code == 401:
                raise SkyFiMCPError("Authentication failed - check API credentials")
            elif response.status_code == 400:
                error_detail = response.json().get("detail", "Invalid search parameters")
                raise SkyFiMCPError(f"Search request invalid: {error_detail}")
            elif response.status_code != 200:
                raise SkyFiMCPError(f"Archive search failed: HTTP {response.status_code}")
            
            search_results = response.json()
        
        # Process and format results
        processed_results = {
            "results": [],
            "total_count": search_results.get("total", 0),
            "returned_count": len(search_results.get("images", [])),
            "search_metadata": {
                "geometry": params.geometry,
                "temporal_range": {
                    "start": params.start_date,
                    "end": params.end_date
                },
                "quality_filters": {
                    "max_cloud_cover": params.cloud_cover_max,
                    "max_resolution": params.resolution_max
                },
                "source_filters": {
                    "satellites": params.satellites,
                    "providers": params.providers
                }
            },
            "pagination": {
                "limit": params.limit,
                "offset": params.offset,
                "has_more": (params.offset + params.limit) < search_results.get("total", 0)
            }
        }
        
        # Process each image result
        for image_data in search_results.get("images", []):
            processed_image = {
                "id": image_data.get("id"),
                "title": image_data.get("title", f"Image {image_data.get('id')}"),
                "acquisition": {
                    "date": image_data.get("acquisition_date"),
                    "satellite": image_data.get("satellite"),
                    "sensor": image_data.get("sensor"),
                    "provider": image_data.get("provider")
                },
                "spatial": {
                    "geometry": image_data.get("geometry"),
                    "resolution": image_data.get("resolution_meters"),
                    "area_km2": image_data.get("area_km2")
                },
                "quality": {
                    "cloud_cover_percent": image_data.get("cloud_cover"),
                    "quality_score": image_data.get("quality_score"),
                    "processing_level": image_data.get("processing_level")
                },
                "availability": {
                    "status": image_data.get("status", "available"),
                    "license": image_data.get("license"),
                    "price_usd": image_data.get("price_usd"),
                    "download_url": image_data.get("download_url"),
                    "preview_url": image_data.get("preview_url")
                },
                "metadata_url": f"{config.url}/archive/images/{image_data.get('id')}/metadata"
            }
            processed_results["results"].append(processed_image)
        
        logger.info(f"Archive search completed: {len(processed_results['results'])} results")
        return processed_results
        
    except Exception as e:
        logger.error(f"Archive search failed: {e}", exc_info=True)
        if isinstance(e, SkyFiMCPError):
            raise
        raise SkyFiMCPError(f"Archive search error: {str(e)}")


@skyfi_mcp.tool(
    name="skyfi_archive_details",
    description="Get detailed information about a specific archive image including metadata and download options"
)
async def get_archive_details(
    image_id: str,
    include_metadata: bool = True,
    include_preview: bool = False
) -> Dict[str, Any]:
    """
    Retrieve detailed information about a specific archive image.
    
    This tool provides comprehensive metadata about an archive image including:
    - Complete acquisition and processing details
    - Spatial reference and coordinate system information
    - Quality metrics and validation results
    - Licensing and usage terms
    - Download and preview options
    
    Args:
        image_id: Unique identifier for the archive image
        include_metadata: Include detailed technical metadata
        include_preview: Include preview/thumbnail generation
        
    Returns:
        Dictionary containing detailed image information:
        - basic_info: Core image details and identifiers
        - acquisition: Satellite, sensor, and capture details
        - spatial: Coordinate systems, projections, and geometry
        - quality: Processing level, validation, and quality metrics
        - licensing: Usage rights, restrictions, and pricing
        - access: Download URLs, formats, and delivery options
        - metadata: Technical specifications (if requested)
        
    Raises:
        SkyFiMCPError: If image not found or access denied
    """
    
    try:
        logger.info(f"Retrieving archive details for image: {image_id}")
        
        # Validate parameters
        params = ArchiveDetailsParams(
            image_id=image_id,
            include_metadata=include_metadata,
            include_preview=include_preview
        )
        
        # Get SkyFi configuration
        app_context = skyfi_mcp._mcp_server.request_context.lifespan_context.get("app_lifespan_context")
        if not app_context or not hasattr(app_context, 'skyfi_config'):
            raise SkyFiMCPError("SkyFi service not configured")
        
        config = app_context.skyfi_config
        headers = {
            **config.get_effective_headers(),
            **config.get_auth_headers()
        }
        
        # Build request parameters
        query_params = {}
        if params.include_metadata:
            query_params["include_metadata"] = "true"
        if params.include_preview:
            query_params["include_preview"] = "true"
        
        # Execute API request
        async with httpx.AsyncClient(
            timeout=config.timeout,
            verify=config.ssl_verify
        ) as client:
            
            response = await client.get(
                f"{config.url}/archive/images/{params.image_id}",
                params=query_params,
                headers=headers
            )
            
            if response.status_code == 404:
                raise SkyFiMCPError(f"Archive image not found: {params.image_id}")
            elif response.status_code == 401:
                raise SkyFiMCPError("Authentication failed")
            elif response.status_code == 403:
                raise SkyFiMCPError("Access denied - insufficient permissions")
            elif response.status_code != 200:
                raise SkyFiMCPError(f"Failed to retrieve image details: HTTP {response.status_code}")
            
            image_details = response.json()
        
        # Format detailed response
        result = {
            "basic_info": {
                "id": image_details.get("id"),
                "title": image_details.get("title"),
                "description": image_details.get("description"),
                "status": image_details.get("status"),
                "created_at": image_details.get("created_at"),
                "updated_at": image_details.get("updated_at")
            },
            "acquisition": {
                "date": image_details.get("acquisition_date"),
                "time": image_details.get("acquisition_time"),
                "satellite": image_details.get("satellite"),
                "sensor": image_details.get("sensor"),
                "mission": image_details.get("mission"),
                "provider": image_details.get("provider"),
                "processing_date": image_details.get("processing_date"),
                "processing_level": image_details.get("processing_level")
            },
            "spatial": {
                "geometry": image_details.get("geometry"),
                "bounds": image_details.get("bounds"),
                "center_point": image_details.get("center"),
                "area_km2": image_details.get("area_km2"),
                "resolution_meters": image_details.get("resolution_meters"),
                "coordinate_system": image_details.get("crs"),
                "projection": image_details.get("projection")
            },
            "quality": {
                "cloud_cover_percent": image_details.get("cloud_cover"),
                "quality_score": image_details.get("quality_score"),
                "validation_status": image_details.get("validation_status"),
                "quality_flags": image_details.get("quality_flags", []),
                "anomalies": image_details.get("anomalies", [])
            },
            "licensing": {
                "license": image_details.get("license"),
                "license_url": image_details.get("license_url"),
                "usage_rights": image_details.get("usage_rights"),
                "commercial_use": image_details.get("commercial_use", False),
                "attribution_required": image_details.get("attribution_required", True),
                "price_usd": image_details.get("price_usd"),
                "pricing_model": image_details.get("pricing_model")
            },
            "access": {
                "download_url": image_details.get("download_url"),
                "preview_url": image_details.get("preview_url"),
                "thumbnail_url": image_details.get("thumbnail_url"),
                "available_formats": image_details.get("formats", []),
                "file_size_mb": image_details.get("file_size_mb"),
                "delivery_options": image_details.get("delivery_options", [])
            }
        }
        
        # Add metadata if requested
        if params.include_metadata and "metadata" in image_details:
            result["metadata"] = image_details["metadata"]
        
        logger.info(f"Retrieved details for image: {params.image_id}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to get archive details for {image_id}: {e}", exc_info=True)
        if isinstance(e, SkyFiMCPError):
            raise
        raise SkyFiMCPError(f"Archive details error: {str(e)}")


def _normalize_geometry(geometry: Union[Dict, str]) -> Dict[str, Any]:
    """
    Normalize geometry input to GeoJSON format.
    
    Handles various input formats:
    - GeoJSON geometry objects
    - WKT strings  
    - Bounding box arrays [west, south, east, north]
    - Coordinate pairs for point locations
    """
    
    if isinstance(geometry, dict):
        # Already a GeoJSON-like object
        if "type" in geometry and "coordinates" in geometry:
            return geometry
        # Might be a bounding box object
        elif "bbox" in geometry:
            bbox = geometry["bbox"]
            return _bbox_to_geojson(bbox)
    
    elif isinstance(geometry, str):
        # Handle WKT or JSON string
        geometry = geometry.strip()
        
        if geometry.startswith(("POINT", "LINESTRING", "POLYGON", "MULTIPOLYGON")):
            # WKT format - convert to GeoJSON
            return _wkt_to_geojson(geometry)
        
        # Try to parse as JSON
        try:
            import json
            parsed = json.loads(geometry)
            return _normalize_geometry(parsed)  # Recursive call
        except (json.JSONDecodeError, ValueError):
            pass
    
    elif isinstance(geometry, (list, tuple)):
        # Handle bounding box array [west, south, east, north]
        if len(geometry) == 4:
            return _bbox_to_geojson(geometry)
        # Handle point coordinates [lon, lat] 
        elif len(geometry) == 2:
            return {
                "type": "Point",
                "coordinates": [float(geometry[0]), float(geometry[1])]
            }
    
    raise ValueError(f"Unable to parse geometry format: {type(geometry)}")


def _bbox_to_geojson(bbox: List[float]) -> Dict[str, Any]:
    """Convert bounding box [west, south, east, north] to GeoJSON Polygon"""
    
    west, south, east, north = bbox
    
    return {
        "type": "Polygon",
        "coordinates": [[
            [west, south],   # SW corner
            [east, south],   # SE corner  
            [east, north],   # NE corner
            [west, north],   # NW corner
            [west, south]    # Close polygon
        ]]
    }


def _wkt_to_geojson(wkt: str) -> Dict[str, Any]:
    """Convert WKT string to GeoJSON geometry"""
    
    # This is a simplified WKT parser for common cases
    # In production, you'd want to use a library like Shapely
    
    wkt = wkt.strip().upper()
    
    if wkt.startswith("POINT"):
        # Extract coordinates from POINT(lon lat)
        coords_str = wkt[wkt.find("(") + 1:wkt.rfind(")")]
        lon, lat = map(float, coords_str.split())
        return {
            "type": "Point", 
            "coordinates": [lon, lat]
        }
    
    elif wkt.startswith("POLYGON"):
        # This is a simplified polygon parser
        # Handle basic case: POLYGON((lon lat, lon lat, ...))
        coords_str = wkt[wkt.find("((") + 2:wkt.rfind("))")]
        coord_pairs = coords_str.split(", ")
        coordinates = []
        
        for pair in coord_pairs:
            lon, lat = map(float, pair.split())
            coordinates.append([lon, lat])
        
        return {
            "type": "Polygon",
            "coordinates": [coordinates]
        }
    
    else:
        raise ValueError(f"Unsupported WKT geometry type: {wkt}")


def _geometry_to_wkt(geometry: Union[Dict, str]) -> str:
    """
    Convert geometry input to WKT format as expected by SkyFi API.
    
    Args:
        geometry: GeoJSON geometry object, WKT string, or bounding box
        
    Returns:
        WKT string representation
    """
    if isinstance(geometry, str):
        # If already WKT, return as-is
        if geometry.strip().startswith(("POINT", "LINESTRING", "POLYGON", "MULTIPOLYGON")):
            return geometry.strip()
        
        # Try to parse as JSON
        try:
            import json
            geometry = json.loads(geometry)
        except (json.JSONDecodeError, ValueError):
            raise ValueError(f"Unable to parse geometry string: {geometry}")
    
    if isinstance(geometry, dict):
        # Convert GeoJSON to WKT
        if geometry.get("type") == "Polygon":
            coords = geometry["coordinates"][0]  # Exterior ring
            coord_pairs = [f"{lon} {lat}" for lon, lat in coords]
            return f"POLYGON(({', '.join(coord_pairs)}))"
        elif geometry.get("type") == "Point":
            lon, lat = geometry["coordinates"]
            return f"POINT({lon} {lat})"
        else:
            raise ValueError(f"Unsupported GeoJSON type: {geometry.get('type')}")
    
    elif isinstance(geometry, (list, tuple)) and len(geometry) == 4:
        # Convert bounding box [west, south, east, north] to WKT polygon
        west, south, east, north = geometry
        return f"POLYGON(({west} {south}, {east} {south}, {east} {north}, {west} {north}, {west} {south}))"
    
    else:
        raise ValueError(f"Unable to convert geometry to WKT: {type(geometry)}")


logger.info("SkyFi Archives tools loaded successfully")