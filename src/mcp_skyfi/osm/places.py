"""
OSM Places Tools

This module implements MCP tools for Point of Interest (POI) search and
business discovery using OpenStreetMap data, enabling AI applications to
find locations, amenities, and businesses around specific areas.

Features:
- POI search by category (restaurants, hotels, gas stations, etc.)
- Business discovery and details lookup
- Amenity search with filtering and ranking
- Nearby places search around coordinates or addresses
- Multi-category search with distance-based results
"""


import logging
import asyncio
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from fastmcp import FastMCP
from pydantic import BaseModel, Field, validator
import httpx

from . import osm_mcp
from ..exceptions import SkyFiMCPError

logger = logging.getLogger("mcp-skyfi.osm.places")


class SearchMethod(str, Enum):
    """POI search methods"""
    NEARBY = "nearby"           # Search around a point
    BBOX = "bbox"              # Search within bounding box
    OVERPASS = "overpass"      # Advanced Overpass API search


class POICategory(str, Enum):
    """Common POI categories"""
    RESTAURANT = "restaurant"
    HOTEL = "hotel"
    GAS_STATION = "fuel"
    HOSPITAL = "hospital"
    SCHOOL = "school"
    BANK = "bank"
    ATM = "atm"
    PHARMACY = "pharmacy"
    SUPERMARKET = "supermarket"
    AIRPORT = "aerodrome"
    TRAIN_STATION = "railway"
    BUS_STATION = "bus_station"
    PARKING = "parking"
    POLICE = "police"
    FIRE_STATION = "fire_station"
    LIBRARY = "library"
    MUSEUM = "museum"
    PARK = "park"
    CHURCH = "place_of_worship"
    CEMETERY = "grave_yard"


class NearbySearchParams(BaseModel):
    """Parameters for nearby POI search"""
    
    center_point: Union[List[float], str] = Field(
        description="Center point as [lon, lat] or address string"
    )
    
    categories: List[str] = Field(
        description="List of POI categories to search for"
    )
    
    radius_meters: float = Field(
        1000,
        gt=0,
        le=50000,
        description="Search radius in meters (max 50km)"
    )
    
    limit: int = Field(
        20,
        ge=1,
        le=100,
        description="Maximum number of results per category"
    )
    
    language: str = Field(
        "en",
        description="Preferred language for results"
    )
    
    include_details: bool = Field(
        True,
        description="Include detailed POI information"
    )


class BusinessSearchParams(BaseModel):
    """Parameters for business search"""
    
    query: str = Field(
        description="Business name or search query"
    )
    
    location: Optional[Union[List[float], str]] = Field(
        None,
        description="Location to search near (coordinates or address)"
    )
    
    radius_meters: Optional[float] = Field(
        None,
        gt=0,
        le=100000,
        description="Search radius in meters"
    )
    
    category_filter: Optional[List[str]] = Field(
        None,
        description="Filter by business categories"
    )
    
    limit: int = Field(
        10,
        ge=1,
        le=50,
        description="Maximum number of results"
    )


@osm_mcp.tool(
    name="osm_search_nearby_pois",
    description="Search for Points of Interest (POIs) near a specific location"
)
async def search_nearby_pois(
    center_point: Union[List[float], str],
    categories: List[str],
    radius_meters: float = 1000,
    limit: int = 20,
    language: str = "en",
    include_details: bool = True
) -> Dict[str, Any]:
    """
    Search for Points of Interest (POIs) near a specific location.
    
    This tool finds restaurants, hotels, gas stations, and other amenities
    within a specified radius of a center point. Useful for travel planning,
    location analysis, and contextual information gathering for satellite
    imagery analysis.
    
    Args:
        center_point: Center location as [longitude, latitude] or address
        categories: POI categories to search (restaurant, hotel, fuel, etc.)
        radius_meters: Search radius in meters (1-50000)
        limit: Maximum results per category (1-100)
        language: Preferred language for results (ISO 639-1 code)
        include_details: Include detailed POI information (hours, contact, etc.)
        
    Returns:
        Dictionary containing:
        - results: List of POIs grouped by category
        - search_metadata: Information about search parameters
        - location_context: Context about the search area
        - summary: Summary statistics and insights
        
    Raises:
        SkyFiMCPError: If POI search fails
    """
    
    try:
        logger.info(f"Searching for POIs near {center_point} in categories: {categories}")
        
        # Validate parameters
        params = NearbySearchParams(
            center_point=center_point,
            categories=categories,
            radius_meters=radius_meters,
            limit=limit,
            language=language,
            include_details=include_details
        )
        
        # Get OSM configuration
        app_context = osm_mcp._mcp_server.request_context.lifespan_context.get("app_lifespan_context")
        if not app_context or not hasattr(app_context, 'osm_config'):
            raise SkyFiMCPError("OSM service not configured")
        
        config = app_context.osm_config
        
        if not config.enable_places_search:
            raise SkyFiMCPError("Places search is disabled in current configuration")
        
        # Resolve center point if it's an address
        if isinstance(params.center_point, str):
            from .geocoding import forward_geocode
            
            geocode_result = await forward_geocode(
                query=params.center_point,
                limit=1,
                include_geometry=False
            )
            
            if not geocode_result["results"]:
                raise SkyFiMCPError(f"Unable to geocode center point: {params.center_point}")
            
            center_coords = [
                geocode_result["results"][0]["coordinates"]["longitude"],
                geocode_result["results"][0]["coordinates"]["latitude"]
            ]
            resolved_address = geocode_result["results"][0]["display_name"]
        else:
            center_coords = params.center_point
            resolved_address = f"{center_coords[1]}, {center_coords[0]}"
        
        headers = config.get_effective_headers()
        
        # Search for each category
        category_results = {}
        total_found = 0
        
        for category in params.categories:
            try:
                # Build search query for this category
                search_query = f"[out:json][timeout:25]; (node[amenity={category}](around:{params.radius_meters},{center_coords[1]},{center_coords[0]}); way[amenity={category}](around:{params.radius_meters},{center_coords[1]},{center_coords[0]});); out center meta {params.limit};"
                
                # Execute Overpass API query if enabled, otherwise use Nominatim
                if config.enable_overpass_queries:
                    pois = await _search_overpass_pois(config, search_query, headers)
                else:
                    pois = await _search_nominatim_pois(
                        config, headers, category, center_coords, params.radius_meters, params.limit, params.language
                    )
                
                # Process and format results
                processed_pois = []
                for poi in pois:
                    processed_poi = await _process_poi_result(poi, center_coords, params.include_details)
                    processed_pois.append(processed_poi)
                
                category_results[category] = processed_pois
                total_found += len(processed_pois)
                
                # Rate limiting
                await asyncio.sleep(1.0 / config.rate_limit)
                
            except Exception as e:
                logger.warning(f"Failed to search category '{category}': {e}")
                category_results[category] = []
        
        # Create summary and context
        all_pois = []
        for cat_pois in category_results.values():
            all_pois.extend(cat_pois)
        
        # Sort all POIs by distance
        all_pois.sort(key=lambda poi: poi.get("distance_meters", float('inf')))
        
        result = {
            "results": {
                "by_category": category_results,
                "all_pois": all_pois[:params.limit * 2],  # Return top overall results
                "nearest": all_pois[:10] if all_pois else []
            },
            "search_metadata": {
                "center_point": {
                    "coordinates": center_coords,
                    "resolved_address": resolved_address,
                    "original_input": params.center_point
                },
                "search_radius_meters": params.radius_meters,
                "categories_searched": params.categories,
                "language": params.language,
                "search_method": "overpass" if config.enable_overpass_queries else "nominatim"
            },
            "location_context": await _get_location_context(center_coords, config, headers),
            "summary": {
                "total_pois_found": total_found,
                "categories_with_results": len([cat for cat, pois in category_results.items() if pois]),
                "nearest_poi_distance_m": all_pois[0]["distance_meters"] if all_pois else None,
                "farthest_poi_distance_m": all_pois[-1]["distance_meters"] if all_pois else None,
                "average_distance_m": sum(poi.get("distance_meters", 0) for poi in all_pois) / len(all_pois) if all_pois else 0,
                "density_per_km2": total_found / (3.14159 * (params.radius_meters / 1000) ** 2) if params.radius_meters > 0 else 0
            }
        }
        
        logger.info(f"POI search completed: {total_found} POIs found in {len(params.categories)} categories")
        return result
        
    except Exception as e:
        logger.error(f"POI search failed: {e}", exc_info=True)
        if isinstance(e, SkyFiMCPError):
            raise
        raise SkyFiMCPError(f"POI search error: {str(e)}")


@osm_mcp.tool(
    name="osm_search_businesses",
    description="Search for specific businesses by name or type in a given area"
)
async def search_businesses(
    query: str,
    location: Optional[Union[List[float], str]] = None,
    radius_meters: Optional[float] = None,
    category_filter: Optional[List[str]] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Search for specific businesses by name or business type.
    
    This tool performs targeted business searches using names, brands,
    or business types. Can search globally or within a specific area.
    Useful for finding specific establishments, chains, or business types.
    
    Args:
        query: Business name, brand, or search term
        location: Location to search near (coordinates or address)
        radius_meters: Search radius in meters (if location provided)
        category_filter: Filter by business categories (optional)
        limit: Maximum number of results (1-50)
        
    Returns:
        Dictionary containing:
        - results: List of matching businesses with details
        - search_info: Information about search parameters and scope
        - geographic_distribution: Geographic spread of results
        - business_insights: Analysis of found businesses
        
    Raises:
        SkyFiMCPError: If business search fails
    """
    
    try:
        logger.info(f"Searching businesses for query: '{query}'")
        
        # Validate parameters
        params = BusinessSearchParams(
            query=query,
            location=location,
            radius_meters=radius_meters,
            category_filter=category_filter,
            limit=limit
        )
        
        # Get OSM configuration
        app_context = osm_mcp._mcp_server.request_context.lifespan_context.get("app_lifespan_context")
        if not app_context or not hasattr(app_context, 'osm_config'):
            raise SkyFiMCPError("OSM service not configured")
        
        config = app_context.osm_config
        
        if not config.enable_places_search:
            raise SkyFiMCPError("Places search is disabled")
        
        headers = config.get_effective_headers()
        
        # Resolve location if provided
        center_coords = None
        resolved_location = None
        
        if params.location:
            if isinstance(params.location, str):
                from .geocoding import forward_geocode
                
                geocode_result = await forward_geocode(
                    query=params.location,
                    limit=1,
                    include_geometry=False
                )
                
                if geocode_result["results"]:
                    center_coords = [
                        geocode_result["results"][0]["coordinates"]["longitude"],
                        geocode_result["results"][0]["coordinates"]["latitude"]
                    ]
                    resolved_location = geocode_result["results"][0]["display_name"]
            else:
                center_coords = params.location
                resolved_location = f"{center_coords[1]}, {center_coords[0]}"
        
        # Build search parameters for Nominatim
        search_params = config.get_nominatim_params()
        search_params.update({
            "q": params.query,
            "limit": params.limit
        })
        
        # Add location restriction if provided
        if center_coords and params.radius_meters:
            # Use viewbox for location bias
            radius_deg = params.radius_meters / 111320  # Rough conversion to degrees
            viewbox = [
                center_coords[0] - radius_deg,  # left (west)
                center_coords[1] + radius_deg,  # top (north)
                center_coords[0] + radius_deg,  # right (east)
                center_coords[1] - radius_deg   # bottom (south)
            ]
            search_params["viewbox"] = ",".join(map(str, viewbox))
            search_params["bounded"] = 1
        
        # Execute search
        async with httpx.AsyncClient(
            timeout=config.timeout,
            verify=True
        ) as client:
            
            response = await client.get(
                f"{config.nominatim_url}/search",
                params=search_params,
                headers=headers
            )
            
            if response.status_code == 429:
                raise SkyFiMCPError("Rate limit exceeded")
            elif response.status_code != 200:
                raise SkyFiMCPError(f"Business search failed: HTTP {response.status_code}")
            
            search_results = response.json()
        
        # Process results
        businesses = []
        for result in search_results:
            # Filter by category if specified
            if params.category_filter:
                result_class = result.get("class", "").lower()
                result_type = result.get("type", "").lower()
                if not any(cat.lower() in [result_class, result_type] for cat in params.category_filter):
                    continue
            
            business = await _process_business_result(result, center_coords)
            businesses.append(business)
        
        # Calculate geographic distribution
        if businesses:
            lats = [b["coordinates"]["latitude"] for b in businesses]
            lons = [b["coordinates"]["longitude"] for b in businesses]
            
            geographic_distribution = {
                "bounding_box": {
                    "north": max(lats),
                    "south": min(lats),
                    "east": max(lons),
                    "west": min(lons)
                },
                "center_point": [sum(lons) / len(lons), sum(lats) / len(lats)],
                "span_km": {
                    "latitude": (max(lats) - min(lats)) * 111.32,
                    "longitude": (max(lons) - min(lons)) * 111.32 * math.cos(math.radians(sum(lats) / len(lats)))
                }
            }
        else:
            geographic_distribution = None
        
        # Analyze business types
        business_types = {}
        for business in businesses:
            btype = business.get("type", "unknown")
            business_types[btype] = business_types.get(btype, 0) + 1
        
        result = {
            "results": businesses,
            "search_info": {
                "query": params.query,
                "location_filter": {
                    "coordinates": center_coords,
                    "resolved_location": resolved_location,
                    "radius_meters": params.radius_meters
                } if center_coords else None,
                "category_filter": params.category_filter,
                "limit": params.limit,
                "total_found": len(businesses)
            },
            "geographic_distribution": geographic_distribution,
            "business_insights": {
                "types_found": business_types,
                "most_common_type": max(business_types.items(), key=lambda x: x[1])[0] if business_types else None,
                "unique_types": len(business_types),
                "has_contact_info": len([b for b in businesses if b.get("contact", {}).get("phone")]),
                "has_website": len([b for b in businesses if b.get("contact", {}).get("website")]),
                "average_importance": sum(b.get("importance", 0) for b in businesses) / len(businesses) if businesses else 0
            }
        }
        
        logger.info(f"Business search completed: {len(businesses)} businesses found for '{query}'")
        return result
        
    except Exception as e:
        logger.error(f"Business search failed: {e}", exc_info=True)
        if isinstance(e, SkyFiMCPError):
            raise
        raise SkyFiMCPError(f"Business search error: {str(e)}")


async def _search_overpass_pois(config, query: str, headers: Dict[str, str]) -> List[Dict[str, Any]]:
    """Search POIs using Overpass API"""
    
    async with httpx.AsyncClient(
        timeout=config.timeout * 2,  # Overpass queries can be slower
        verify=True
    ) as client:
        
        response = await client.post(
            f"{config.overpass_url}/interpreter",
            data=query,
            headers={**headers, "Content-Type": "text/plain"}
        )
        
        if response.status_code != 200:
            raise SkyFiMCPError(f"Overpass query failed: HTTP {response.status_code}")
        
        overpass_data = response.json()
        return overpass_data.get("elements", [])


async def _search_nominatim_pois(
    config, 
    headers: Dict[str, str], 
    category: str, 
    center_coords: List[float], 
    radius_meters: float,
    limit: int,
    language: str
) -> List[Dict[str, Any]]:
    """Search POIs using Nominatim API"""
    
    # Build search query
    search_params = config.get_nominatim_params()
    search_params.update({
        "q": f"[amenity={category}]",
        "limit": limit,
        "accept-language": language
    })
    
    # Use viewbox for location restriction
    radius_deg = radius_meters / 111320
    viewbox = [
        center_coords[0] - radius_deg,
        center_coords[1] + radius_deg,
        center_coords[0] + radius_deg,
        center_coords[1] - radius_deg
    ]
    search_params["viewbox"] = ",".join(map(str, viewbox))
    search_params["bounded"] = 1
    
    async with httpx.AsyncClient(
        timeout=config.timeout,
        verify=True
    ) as client:
        
        response = await client.get(
            f"{config.nominatim_url}/search",
            params=search_params,
            headers=headers
        )
        
        if response.status_code != 200:
            return []  # Return empty list on error rather than failing
        
        return response.json()


async def _process_poi_result(poi: Dict[str, Any], center_coords: List[float], include_details: bool) -> Dict[str, Any]:
    """Process and format a POI result"""
    
    # Extract coordinates
    if "lat" in poi and "lon" in poi:
        poi_coords = [float(poi["lon"]), float(poi["lat"])]
    elif "center" in poi:
        poi_coords = [poi["center"]["lon"], poi["center"]["lat"]]
    else:
        poi_coords = [0, 0]  # Fallback
    
    # Calculate distance from center
    from .geometry import _haversine_distance
    distance_km = _haversine_distance(center_coords, poi_coords)
    distance_meters = distance_km * 1000
    
    # Basic POI information
    processed = {
        "name": poi.get("name") or poi.get("tags", {}).get("name") or "Unnamed",
        "category": poi.get("amenity") or poi.get("tags", {}).get("amenity"),
        "type": poi.get("type"),
        "coordinates": {
            "longitude": poi_coords[0],
            "latitude": poi_coords[1]
        },
        "distance_meters": round(distance_meters),
        "distance_km": round(distance_km, 3),
        "display_name": poi.get("display_name"),
        "importance": poi.get("importance", 0)
    }
    
    # Add detailed information if requested
    if include_details:
        tags = poi.get("tags", {})
        processed.update({
            "address": poi.get("address", {}),
            "contact": {
                "phone": tags.get("phone"),
                "website": tags.get("website"),
                "email": tags.get("email"),
                "facebook": tags.get("facebook"),
                "instagram": tags.get("instagram")
            },
            "hours": {
                "opening_hours": tags.get("opening_hours"),
                "24_7": tags.get("opening_hours") == "24/7"
            },
            "features": {
                "wheelchair_accessible": tags.get("wheelchair") == "yes",
                "wifi": tags.get("internet_access") == "wlan",
                "parking": bool(tags.get("parking")),
                "outdoor_seating": tags.get("outdoor_seating") == "yes",
                "takeaway": tags.get("takeaway") == "yes",
                "delivery": tags.get("delivery") == "yes"
            },
            "rating": {
                "stars": tags.get("stars"),
                "review_count": tags.get("review_count")
            },
            "additional_info": {
                "brand": tags.get("brand"),
                "cuisine": tags.get("cuisine"),
                "capacity": tags.get("capacity"),
                "fee": tags.get("fee"),
                "payment_methods": tags.get("payment")
            }
        })
    
    return processed


async def _process_business_result(result: Dict[str, Any], center_coords: Optional[List[float]]) -> Dict[str, Any]:
    """Process and format a business search result"""
    
    coordinates = [float(result.get("lon", 0)), float(result.get("lat", 0))]
    
    # Calculate distance if center point provided
    distance_info = {}
    if center_coords:
        from .geometry import _haversine_distance
        distance_km = _haversine_distance(center_coords, coordinates)
        distance_info = {
            "distance_meters": round(distance_km * 1000),
            "distance_km": round(distance_km, 3)
        }
    
    return {
        "place_id": result.get("place_id"),
        "name": result.get("name") or result.get("display_name", "").split(",")[0],
        "display_name": result.get("display_name"),
        "category": result.get("class"),
        "type": result.get("type"),
        "coordinates": {
            "longitude": coordinates[0],
            "latitude": coordinates[1]
        },
        "address": result.get("address", {}),
        "importance": result.get("importance", 0),
        "bounding_box": result.get("boundingbox"),
        **distance_info
    }


async def _get_location_context(center_coords: List[float], config, headers: Dict[str, str]) -> Dict[str, Any]:
    """Get contextual information about the search location"""
    
    try:
        # Get reverse geocoding for context
        from .geocoding import reverse_geocode
        
        location_info = await reverse_geocode(
            latitude=center_coords[1],
            longitude=center_coords[0],
            zoom=14,
            include_geometry=False
        )
        
        address = location_info["address"]
        
        return {
            "neighborhood": address.get("neighborhood"),
            "city": address.get("city"),
            "state": address.get("state"),
            "country": address.get("country"),
            "area_type": location_info["location"]["type"],
            "context_description": f"Search area in {address.get('city', 'unknown city')}, {address.get('country', 'unknown country')}"
        }
        
    except Exception as e:
        logger.warning(f"Failed to get location context: {e}")
        return {
            "context_description": f"Search area around coordinates {center_coords[1]:.4f}, {center_coords[0]:.4f}"
        }


# Import math for calculations
import math

logger.info("OSM Places tools loaded successfully")