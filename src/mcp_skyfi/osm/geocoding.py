"""
OSM Geocoding Tools

This module implements MCP tools for forward and reverse geocoding using
the OpenStreetMap Nominatim service, enabling AI applications to convert
between addresses and coordinates.

Features:
- Forward geocoding: Address/place name to coordinates
- Reverse geocoding: Coordinates to address/place details
- Batch geocoding for multiple locations
- Structured address parsing and formatting
- Multi-language support and country filtering
"""


import logging
import asyncio
from typing import Any, Dict, List, Optional, Union, Tuple
from fastmcp import FastMCP
from pydantic import BaseModel, Field, validator
import httpx

from . import osm_mcp
from ..exceptions import SkyFiMCPError

logger = logging.getLogger("mcp-skyfi.osm.geocoding")


class ForwardGeocodingParams(BaseModel):
    """Parameters for forward geocoding (address to coordinates)"""
    
    query: str = Field(
        description="Address, place name, or search query to geocode"
    )
    
    limit: int = Field(
        10,
        ge=1,
        le=50,
        description="Maximum number of results to return"
    )
    
    country_codes: Optional[List[str]] = Field(
        None,
        description="Restrict results to specific countries (ISO 3166-1 alpha-2 codes)"
    )
    
    language: str = Field(
        "en",
        description="Preferred language for results (ISO 639-1 code)"
    )
    
    include_geometry: bool = Field(
        True,
        description="Include geometry information in results"
    )
    
    structured: bool = Field(
        False,
        description="Return structured address components"
    )


class ReverseGeocodingParams(BaseModel):
    """Parameters for reverse geocoding (coordinates to address)"""
    
    latitude: float = Field(
        ge=-90,
        le=90,
        description="Latitude coordinate"
    )
    
    longitude: float = Field(
        ge=-180,
        le=180,
        description="Longitude coordinate"
    )
    
    zoom: int = Field(
        18,
        ge=1,
        le=18,
        description="Detail level (1=country, 18=building)"
    )
    
    language: str = Field(
        "en", 
        description="Preferred language for results"
    )
    
    include_geometry: bool = Field(
        True,
        description="Include geometry information in results"
    )


class BatchGeocodingParams(BaseModel):
    """Parameters for batch geocoding multiple locations"""
    
    queries: List[str] = Field(
        description="List of addresses or place names to geocode"
    )
    
    limit_per_query: int = Field(
        5,
        ge=1,
        le=10,
        description="Maximum results per query"
    )
    
    country_codes: Optional[List[str]] = Field(
        None,
        description="Restrict all results to specific countries"
    )
    
    language: str = Field(
        "en",
        description="Preferred language for all results"
    )
    
    @validator('queries')
    def validate_queries(cls, v):
        if len(v) > 20:
            raise ValueError("Maximum 20 queries allowed in batch request")
        return v


@osm_mcp.tool(
    name="osm_forward_geocode",
    description="Convert address or place name to coordinates using OpenStreetMap geocoding"
)
async def forward_geocode(
    query: str,
    limit: int = 10,
    country_codes: Optional[List[str]] = None,
    language: str = "en",
    include_geometry: bool = True,
    structured: bool = False
) -> Dict[str, Any]:
    """
    Convert an address, place name, or search query to geographic coordinates.
    
    This tool uses the OpenStreetMap Nominatim service to find coordinates
    for addresses, landmarks, businesses, or other geographic features.
    Results include detailed location information and optional geometry data.
    
    Args:
        query: Address, place name, or search query (e.g., "Times Square, NYC")
        limit: Maximum number of results to return (1-50)
        country_codes: Restrict to specific countries (e.g., ["US", "CA"])
        language: Preferred language for results (ISO 639-1 code)
        include_geometry: Include boundary/geometry information
        structured: Return structured address components
        
    Returns:
        Dictionary containing:
        - results: List of matching locations with coordinates
        - query_info: Information about the search query
        - total_found: Number of results found
        - geocoding_metadata: Service and performance information
        
    Raises:
        SkyFiMCPError: If geocoding request fails
    """
    
    try:
        logger.info(f"Forward geocoding query: {query}")
        
        # Validate parameters
        params = ForwardGeocodingParams(
            query=query,
            limit=limit,
            country_codes=country_codes,
            language=language,
            include_geometry=include_geometry,
            structured=structured
        )
        
        # Get OSM configuration
        app_context = osm_mcp._mcp_server.request_context.lifespan_context.get("app_lifespan_context")
        if not app_context or not hasattr(app_context, 'osm_config'):
            raise SkyFiMCPError("OSM service not configured")
        
        config = app_context.osm_config
        
        if not config.enable_geocoding:
            raise SkyFiMCPError("Geocoding is disabled in current configuration")
        
        headers = config.get_effective_headers()
        
        # Build request parameters
        request_params = config.get_nominatim_params()
        request_params.update({
            "q": params.query,
            "limit": params.limit,
            "accept-language": params.language
        })
        
        # Override geometry settings if specified
        if params.include_geometry:
            request_params["polygon_geojson"] = 1
        
        # Add country restriction if specified
        if params.country_codes:
            request_params["countrycodes"] = ",".join(params.country_codes)
        
        # Execute geocoding request
        async with httpx.AsyncClient(
            timeout=config.timeout,
            verify=True
        ) as client:
            
            response = await client.get(
                f"{config.nominatim_url}/search",
                params=request_params,
                headers=headers
            )
            
            if response.status_code == 429:
                raise SkyFiMCPError("Rate limit exceeded - please slow down requests")
            elif response.status_code != 200:
                raise SkyFiMCPError(f"Geocoding request failed: HTTP {response.status_code}")
            
            geocoding_results = response.json()
        
        # Process and format results
        processed_results = []
        
        for result in geocoding_results:
            processed_result = {
                "place_id": result.get("place_id"),
                "display_name": result.get("display_name"),
                "coordinates": {
                    "latitude": float(result.get("lat", 0)),
                    "longitude": float(result.get("lon", 0))
                },
                "bounding_box": _parse_bounding_box(result.get("boundingbox", [])),
                "class": result.get("class"),
                "type": result.get("type"),
                "importance": result.get("importance"),
                "confidence": _calculate_confidence(result.get("importance", 0)),
                "address": _parse_address_components(result.get("address", {})),
                "geometry": result.get("geojson") if params.include_geometry else None
            }
            
            # Add structured address if requested
            if params.structured:
                processed_result["structured_address"] = _structure_address(result.get("address", {}))
            
            processed_results.append(processed_result)
        
        # Create response
        result = {
            "results": processed_results,
            "query_info": {
                "original_query": params.query,
                "language": params.language,
                "country_filter": params.country_codes,
                "include_geometry": params.include_geometry
            },
            "total_found": len(processed_results),
            "geocoding_metadata": {
                "service": "OpenStreetMap Nominatim",
                "attribution": "© OpenStreetMap contributors",
                "response_time_ms": response.elapsed.total_seconds() * 1000,
                "cached": "cache-control" in response.headers
            }
        }
        
        logger.info(f"Forward geocoding completed: {len(processed_results)} results")
        return result
        
    except Exception as e:
        logger.error(f"Forward geocoding failed for '{query}': {e}", exc_info=True)
        if isinstance(e, SkyFiMCPError):
            raise
        raise SkyFiMCPError(f"Forward geocoding error: {str(e)}")


@osm_mcp.tool(
    name="osm_reverse_geocode", 
    description="Convert coordinates to address and location information using OpenStreetMap"
)
async def reverse_geocode(
    latitude: float,
    longitude: float,
    zoom: int = 18,
    language: str = "en",
    include_geometry: bool = True
) -> Dict[str, Any]:
    """
    Convert geographic coordinates to address and location information.
    
    This tool performs reverse geocoding to find the address, place name,
    or location details for a given set of coordinates. Results include
    hierarchical address components and contextual information.
    
    Args:
        latitude: Latitude coordinate (-90 to 90)
        longitude: Longitude coordinate (-180 to 180)  
        zoom: Detail level (1=country level, 18=building level)
        language: Preferred language for results
        include_geometry: Include geometry information in results
        
    Returns:
        Dictionary containing:
        - location: Primary location information and coordinates
        - address: Hierarchical address components
        - place_details: Additional place information and context
        - nearby: Information about nearby features
        - geocoding_metadata: Service information
        
    Raises:
        SkyFiMCPError: If reverse geocoding fails or coordinates invalid
    """
    
    try:
        logger.info(f"Reverse geocoding coordinates: {latitude}, {longitude}")
        
        # Validate parameters
        params = ReverseGeocodingParams(
            latitude=latitude,
            longitude=longitude,
            zoom=zoom,
            language=language,
            include_geometry=include_geometry
        )
        
        # Get OSM configuration
        app_context = osm_mcp._mcp_server.request_context.lifespan_context.get("app_lifespan_context")
        if not app_context or not hasattr(app_context, 'osm_config'):
            raise SkyFiMCPError("OSM service not configured")
        
        config = app_context.osm_config
        
        if not config.enable_geocoding:
            raise SkyFiMCPError("Geocoding is disabled in current configuration")
        
        headers = config.get_effective_headers()
        
        # Build request parameters
        request_params = {
            "lat": params.latitude,
            "lon": params.longitude,
            "zoom": params.zoom,
            "format": "json",
            "addressdetails": 1,
            "extratags": 1,
            "namedetails": 1,
            "accept-language": params.language
        }
        
        if params.include_geometry:
            request_params["polygon_geojson"] = 1
        
        # Execute reverse geocoding request
        async with httpx.AsyncClient(
            timeout=config.timeout,
            verify=True
        ) as client:
            
            response = await client.get(
                f"{config.nominatim_url}/reverse",
                params=request_params,
                headers=headers
            )
            
            if response.status_code == 429:
                raise SkyFiMCPError("Rate limit exceeded")
            elif response.status_code == 404:
                raise SkyFiMCPError("No location found for coordinates")
            elif response.status_code != 200:
                raise SkyFiMCPError(f"Reverse geocoding failed: HTTP {response.status_code}")
            
            location_data = response.json()
        
        # Process result
        result = {
            "location": {
                "place_id": location_data.get("place_id"),
                "display_name": location_data.get("display_name"),
                "coordinates": {
                    "latitude": params.latitude,
                    "longitude": params.longitude
                },
                "class": location_data.get("class"),
                "type": location_data.get("type"),
                "importance": location_data.get("importance")
            },
            "address": _parse_address_components(location_data.get("address", {})),
            "place_details": {
                "name": location_data.get("name"),
                "name_details": location_data.get("namedetails", {}),
                "extra_tags": location_data.get("extratags", {}),
                "bounding_box": _parse_bounding_box(location_data.get("boundingbox", [])),
                "geometry": location_data.get("geojson") if params.include_geometry else None
            },
            "context": {
                "zoom_level": params.zoom,
                "language": params.language,
                "detail_level": _get_detail_level_description(params.zoom)
            },
            "geocoding_metadata": {
                "service": "OpenStreetMap Nominatim",
                "attribution": "© OpenStreetMap contributors",
                "response_time_ms": response.elapsed.total_seconds() * 1000,
                "osm_id": location_data.get("osm_id"),
                "osm_type": location_data.get("osm_type")
            }
        }
        
        logger.info(f"Reverse geocoding completed for {latitude}, {longitude}")
        return result
        
    except Exception as e:
        logger.error(f"Reverse geocoding failed for {latitude}, {longitude}: {e}", exc_info=True)
        if isinstance(e, SkyFiMCPError):
            raise
        raise SkyFiMCPError(f"Reverse geocoding error: {str(e)}")


@osm_mcp.tool(
    name="osm_batch_geocode",
    description="Geocode multiple addresses or place names in a single request"
)
async def batch_geocode(
    queries: List[str],
    limit_per_query: int = 5,
    country_codes: Optional[List[str]] = None,
    language: str = "en"
) -> Dict[str, Any]:
    """
    Geocode multiple addresses or place names efficiently in batch.
    
    This tool processes multiple geocoding requests concurrently while
    respecting rate limits and service usage policies. Ideal for
    processing lists of addresses or locations.
    
    Args:
        queries: List of addresses or place names to geocode
        limit_per_query: Maximum results per individual query
        country_codes: Restrict all results to specific countries  
        language: Preferred language for all results
        
    Returns:
        Dictionary containing:
        - results: List of geocoding results for each query
        - summary: Batch processing summary and statistics
        - failed_queries: List of queries that failed to process
        - geocoding_metadata: Batch processing information
        
    Raises:
        SkyFiMCPError: If batch processing fails
    """
    
    try:
        logger.info(f"Batch geocoding {len(queries)} queries")
        
        # Validate parameters
        params = BatchGeocodingParams(
            queries=queries,
            limit_per_query=limit_per_query,
            country_codes=country_codes,
            language=language
        )
        
        # Get OSM configuration
        app_context = osm_mcp._mcp_server.request_context.lifespan_context.get("app_lifespan_context")
        if not app_context or not hasattr(app_context, 'osm_config'):
            raise SkyFiMCPError("OSM service not configured")
        
        config = app_context.osm_config
        
        if not config.enable_geocoding:
            raise SkyFiMCPError("Geocoding is disabled")
        
        # Process queries with rate limiting
        results = []
        failed_queries = []
        total_results = 0
        
        # Create semaphore for rate limiting
        semaphore = asyncio.Semaphore(config.rate_limit)
        
        async def geocode_single_query(query: str, index: int) -> Dict[str, Any]:
            """Geocode a single query with rate limiting"""
            
            async with semaphore:
                try:
                    # Use the forward_geocode function
                    geocode_result = await forward_geocode(
                        query=query,
                        limit=params.limit_per_query,
                        country_codes=params.country_codes,
                        language=params.language,
                        include_geometry=True,
                        structured=False
                    )
                    
                    # Wait to respect rate limit
                    await asyncio.sleep(1.0 / config.rate_limit)
                    
                    return {
                        "index": index,
                        "query": query,
                        "status": "success",
                        "result": geocode_result,
                        "result_count": len(geocode_result.get("results", []))
                    }
                    
                except Exception as e:
                    logger.warning(f"Failed to geocode query '{query}': {e}")
                    return {
                        "index": index,
                        "query": query,
                        "status": "failed",
                        "error": str(e),
                        "result_count": 0
                    }
        
        # Execute batch geocoding with concurrency control
        tasks = [
            geocode_single_query(query, i) 
            for i, query in enumerate(params.queries)
        ]
        
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for batch_result in batch_results:
            if isinstance(batch_result, Exception):
                failed_queries.append({
                    "query": "unknown",
                    "error": str(batch_result)
                })
            elif batch_result["status"] == "success":
                results.append(batch_result)
                total_results += batch_result["result_count"]
            else:
                failed_queries.append({
                    "query": batch_result["query"],
                    "error": batch_result["error"]
                })
        
        # Create summary
        summary = {
            "total_queries": len(params.queries),
            "successful_queries": len(results),
            "failed_queries": len(failed_queries),
            "total_results_found": total_results,
            "success_rate": len(results) / len(params.queries) * 100,
            "average_results_per_query": total_results / len(results) if results else 0
        }
        
        result = {
            "results": results,
            "summary": summary,
            "failed_queries": failed_queries,
            "batch_metadata": {
                "queries_processed": len(params.queries),
                "limit_per_query": params.limit_per_query,
                "country_filter": params.country_codes,
                "language": params.language,
                "service": "OpenStreetMap Nominatim"
            }
        }
        
        logger.info(f"Batch geocoding completed: {len(results)}/{len(params.queries)} successful")
        return result
        
    except Exception as e:
        logger.error(f"Batch geocoding failed: {e}", exc_info=True)
        if isinstance(e, SkyFiMCPError):
            raise
        raise SkyFiMCPError(f"Batch geocoding error: {str(e)}")


def _parse_bounding_box(bbox_list: List[str]) -> Optional[Dict[str, float]]:
    """Parse bounding box from Nominatim format to structured dict"""
    
    if not bbox_list or len(bbox_list) != 4:
        return None
    
    try:
        return {
            "south": float(bbox_list[0]),
            "north": float(bbox_list[1]), 
            "west": float(bbox_list[2]),
            "east": float(bbox_list[3])
        }
    except (ValueError, IndexError):
        return None


def _parse_address_components(address_dict: Dict[str, str]) -> Dict[str, Any]:
    """Parse and structure address components from Nominatim response"""
    
    return {
        "house_number": address_dict.get("house_number"),
        "street": address_dict.get("road") or address_dict.get("street"),
        "neighborhood": address_dict.get("neighbourhood") or address_dict.get("suburb"),
        "city": address_dict.get("city") or address_dict.get("town") or address_dict.get("village"),
        "municipality": address_dict.get("municipality"),
        "county": address_dict.get("county"),
        "state": address_dict.get("state"),
        "country": address_dict.get("country"),
        "postcode": address_dict.get("postcode"),
        "country_code": address_dict.get("country_code")
    }


def _structure_address(address_dict: Dict[str, str]) -> Dict[str, str]:
    """Create structured address format"""
    
    components = []
    
    # Street address
    if address_dict.get("house_number") and address_dict.get("road"):
        components.append(f"{address_dict['house_number']} {address_dict['road']}")
    elif address_dict.get("road"):
        components.append(address_dict["road"])
    
    # City, State ZIP
    city_line = []
    if address_dict.get("city") or address_dict.get("town"):
        city_line.append(address_dict.get("city") or address_dict.get("town"))
    if address_dict.get("state"):
        city_line.append(address_dict["state"])
    if address_dict.get("postcode"):
        city_line.append(address_dict["postcode"])
    
    if city_line:
        components.append(" ".join(city_line))
    
    # Country
    if address_dict.get("country"):
        components.append(address_dict["country"])
    
    return {
        "formatted": "\n".join(components),
        "single_line": ", ".join(components)
    }


def _calculate_confidence(importance: float) -> str:
    """Convert Nominatim importance score to confidence level"""
    
    if importance >= 0.8:
        return "very_high"
    elif importance >= 0.6:
        return "high"
    elif importance >= 0.4:
        return "medium"
    elif importance >= 0.2:
        return "low"
    else:
        return "very_low"


def _get_detail_level_description(zoom: int) -> str:
    """Get human-readable description of zoom/detail level"""
    
    if zoom <= 3:
        return "country/continent level"
    elif zoom <= 6:
        return "state/province level"
    elif zoom <= 10:
        return "city level"
    elif zoom <= 14:
        return "neighborhood level"
    elif zoom <= 16:
        return "street level"
    else:
        return "building level"


logger.info("OSM Geocoding tools loaded successfully")