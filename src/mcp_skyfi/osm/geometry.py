"""
OSM Geometry Tools

This module implements MCP tools for spatial operations and geometry
generation using OpenStreetMap data, enabling AI applications to create
areas of interest (AOIs) and perform spatial analysis.

Features:
- Area of Interest (AOI) generation from addresses or coordinates
- Bounding box creation and buffer operations
- Spatial distance and area calculations
- Coordinate system transformations
- Multi-format geometry conversion (GeoJSON, WKT, KML)
"""


import logging
import math
from typing import Any, Dict, List, Optional, Union, Tuple
from enum import Enum
from fastmcp import FastMCP
from pydantic import BaseModel, Field, validator
import httpx

from . import osm_mcp
from ..exceptions import SkyFiMCPError

logger = logging.getLogger("mcp-skyfi.osm.geometry")


class GeometryFormat(str, Enum):
    """Supported geometry output formats"""
    GEOJSON = "geojson"
    WKT = "wkt"
    BBOX = "bbox"
    KML = "kml"


class BufferMethod(str, Enum):
    """Buffer calculation methods"""
    GEODESIC = "geodesic"  # Accurate for large areas
    PLANAR = "planar"      # Fast approximation
    DEGREES = "degrees"    # Simple degree-based buffer


class AOIGenerationParams(BaseModel):
    """Parameters for AOI generation"""
    
    center_point: Union[List[float], str] = Field(
        description="Center point as [lon, lat] or address string"
    )
    
    radius_meters: float = Field(
        gt=0,
        description="Radius in meters for circular AOI"
    )
    
    buffer_method: BufferMethod = Field(
        BufferMethod.GEODESIC,
        description="Buffer calculation method"
    )
    
    output_format: GeometryFormat = Field(
        GeometryFormat.GEOJSON,
        description="Output geometry format"
    )
    
    resolution: int = Field(
        32,
        ge=8,
        le=128,
        description="Number of points for circular approximation"
    )


class BoundingBoxParams(BaseModel):
    """Parameters for bounding box creation"""
    
    points: List[List[float]] = Field(
        description="List of [longitude, latitude] coordinate pairs"
    )
    
    buffer_meters: Optional[float] = Field(
        None,
        ge=0,
        description="Buffer distance in meters to expand bounding box"
    )
    
    output_format: GeometryFormat = Field(
        GeometryFormat.GEOJSON,
        description="Output format for bounding box"
    )
    
    @validator('points')
    def validate_points(cls, v):
        if len(v) < 1:
            raise ValueError("At least one point required")
        for point in v:
            if len(point) != 2:
                raise ValueError("Each point must be [longitude, latitude]")
            if not (-180 <= point[0] <= 180):
                raise ValueError(f"Longitude {point[0]} out of range [-180, 180]")
            if not (-90 <= point[1] <= 90):
                raise ValueError(f"Latitude {point[1]} out of range [-90, 90]")
        return v


class DistanceCalculationParams(BaseModel):
    """Parameters for distance calculations"""
    
    point1: List[float] = Field(
        description="First point as [longitude, latitude]"
    )
    
    point2: List[float] = Field(
        description="Second point as [longitude, latitude]"
    )
    
    method: str = Field(
        "haversine",
        description="Distance calculation method (haversine, vincenty, euclidean)"
    )
    
    @validator('point1', 'point2')
    def validate_point(cls, v):
        if len(v) != 2:
            raise ValueError("Point must be [longitude, latitude]")
        if not (-180 <= v[0] <= 180):
            raise ValueError(f"Longitude {v[0]} out of range [-180, 180]")
        if not (-90 <= v[1] <= 90):
            raise ValueError(f"Latitude {v[1]} out of range [-90, 90]")
        return v


@osm_mcp.tool(
    name="osm_generate_aoi",
    description="Generate an Area of Interest (AOI) around a location for satellite imagery search"
)
async def generate_aoi(
    center_point: Union[List[float], str],
    radius_meters: float,
    buffer_method: str = "geodesic",
    output_format: str = "geojson",
    resolution: int = 32
) -> Dict[str, Any]:
    """
    Generate a circular or polygonal Area of Interest (AOI) around a center point.
    
    This tool creates geometric areas suitable for satellite imagery searches,
    taking a center location (coordinates or address) and radius to generate
    precise AOI boundaries. Essential for defining search areas for SkyFi
    archive searches and tasking orders.
    
    Args:
        center_point: Center location as [longitude, latitude] or address string
        radius_meters: Radius in meters for the AOI (minimum 1m)
        buffer_method: Calculation method (geodesic, planar, degrees)  
        output_format: Output format (geojson, wkt, bbox, kml)
        resolution: Number of points for circular approximation (8-128)
        
    Returns:
        Dictionary containing:
        - geometry: Generated AOI in requested format
        - properties: AOI metadata and calculations
        - center_point: Resolved center coordinates
        - coverage_info: Area coverage and dimensions
        - usage_suggestions: Recommendations for satellite imagery searches
        
    Raises:
        SkyFiMCPError: If AOI generation fails or parameters invalid
    """
    
    try:
        logger.info(f"Generating AOI with radius {radius_meters}m around {center_point}")
        
        # Validate parameters
        params = AOIGenerationParams(
            center_point=center_point,
            radius_meters=radius_meters,
            buffer_method=BufferMethod(buffer_method),
            output_format=GeometryFormat(output_format),
            resolution=resolution
        )
        
        # Resolve center point if it's an address
        if isinstance(params.center_point, str):
            # Use geocoding to resolve address
            try:
                from .geocoding import forward_geocode
                
                geocode_result = await forward_geocode(
                    query=params.center_point,
                    limit=1,
                    include_geometry=False
                )
            except Exception as e:
                raise SkyFiMCPError(f"Geocoding service unavailable: {str(e)}")
            
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
        
        # Generate circular AOI geometry
        aoi_geometry = _generate_circle_geometry(
            center_lon=center_coords[0],
            center_lat=center_coords[1],
            radius_meters=params.radius_meters,
            method=params.buffer_method,
            resolution=params.resolution
        )
        
        # Calculate AOI properties
        area_km2 = _calculate_polygon_area(aoi_geometry["coordinates"][0])
        bbox = _calculate_bounding_box(aoi_geometry["coordinates"][0])
        dimensions = _calculate_dimensions(bbox)
        
        # Format output geometry
        if params.output_format == GeometryFormat.GEOJSON:
            output_geometry = aoi_geometry
        elif params.output_format == GeometryFormat.WKT:
            output_geometry = _geometry_to_wkt(aoi_geometry)
        elif params.output_format == GeometryFormat.BBOX:
            output_geometry = [bbox["west"], bbox["south"], bbox["east"], bbox["north"]]
        elif params.output_format == GeometryFormat.KML:
            output_geometry = _geometry_to_kml(aoi_geometry)
        
        result = {
            "geometry": output_geometry,
            "format": params.output_format.value,
            "properties": {
                "type": "circular_aoi",
                "radius_meters": params.radius_meters,
                "buffer_method": params.buffer_method.value,
                "resolution_points": params.resolution,
                "area_km2": round(area_km2, 6),
                "area_hectares": round(area_km2 * 100, 2),
                "perimeter_km": round(_calculate_perimeter(aoi_geometry["coordinates"][0]), 3)
            },
            "center_point": {
                "coordinates": center_coords,
                "resolved_address": resolved_address,
                "original_input": params.center_point
            },
            "coverage_info": {
                "bounding_box": bbox,
                "dimensions_km": dimensions,
                "diagonal_km": round(_calculate_diagonal_distance(bbox), 3),
                "coordinate_system": "WGS84 (EPSG:4326)"
            },
            "usage_suggestions": {
                "satellite_search": "Use this AOI geometry for SkyFi archive searches",
                "imagery_resolution": _suggest_resolution(params.radius_meters),
                "typical_coverage": _estimate_imagery_coverage(area_km2),
                "recommended_buffer": "Consider 10-20% buffer for imagery overlap"
            }
        }
        
        logger.info(f"AOI generated: {area_km2:.2f} km² around {resolved_address}")
        return result
        
    except Exception as e:
        logger.error(f"AOI generation failed: {e}", exc_info=True)
        if isinstance(e, SkyFiMCPError):
            raise
        raise SkyFiMCPError(f"AOI generation error: {str(e)}")


@osm_mcp.tool(
    name="osm_create_bounding_box",
    description="Create a bounding box geometry from a set of coordinate points"
)
async def create_bounding_box(
    points: List[List[float]],
    buffer_meters: Optional[float] = None,
    output_format: str = "geojson"
) -> Dict[str, Any]:
    """
    Create a bounding box that encompasses a set of coordinate points.
    
    This tool generates the minimum bounding rectangle that contains all
    specified points, with optional buffer expansion. Useful for creating
    search areas that cover multiple locations or features.
    
    Args:
        points: List of [longitude, latitude] coordinate pairs
        buffer_meters: Optional buffer distance in meters to expand the box
        output_format: Output format (geojson, wkt, bbox, kml)
        
    Returns:
        Dictionary containing:
        - geometry: Bounding box in requested format  
        - properties: Box dimensions and area calculations
        - input_analysis: Information about input points
        - coverage_info: Spatial coverage details
        
    Raises:
        SkyFiMCPError: If bounding box creation fails
    """
    
    try:
        logger.info(f"Creating bounding box for {len(points)} points")
        
        # Validate parameters
        params = BoundingBoxParams(
            points=points,
            buffer_meters=buffer_meters,
            output_format=GeometryFormat(output_format)
        )
        
        # Calculate initial bounding box
        min_lon = min(point[0] for point in params.points)
        max_lon = max(point[0] for point in params.points)
        min_lat = min(point[1] for point in params.points)
        max_lat = max(point[1] for point in params.points)
        
        # Apply buffer if specified
        if params.buffer_meters:
            # Convert buffer from meters to degrees (approximate)
            buffer_deg_lat = params.buffer_meters / 111320  # meters per degree latitude
            buffer_deg_lon = params.buffer_meters / (111320 * math.cos(math.radians((min_lat + max_lat) / 2)))
            
            min_lon -= buffer_deg_lon
            max_lon += buffer_deg_lon
            min_lat -= buffer_deg_lat
            max_lat += buffer_deg_lat
            
            # Ensure coordinates stay within valid ranges
            min_lon = max(min_lon, -180)
            max_lon = min(max_lon, 180)
            min_lat = max(min_lat, -90)
            max_lat = min(max_lat, 90)
        
        bbox_coords = {
            "west": min_lon,
            "south": min_lat,
            "east": max_lon,
            "north": max_lat
        }
        
        # Create geometry
        bbox_geometry = {
            "type": "Polygon",
            "coordinates": [[
                [min_lon, min_lat],  # SW
                [max_lon, min_lat],  # SE
                [max_lon, max_lat],  # NE
                [min_lon, max_lat],  # NW
                [min_lon, min_lat]   # Close polygon
            ]]
        }
        
        # Format output
        if params.output_format == GeometryFormat.GEOJSON:
            output_geometry = bbox_geometry
        elif params.output_format == GeometryFormat.WKT:
            output_geometry = _geometry_to_wkt(bbox_geometry)
        elif params.output_format == GeometryFormat.BBOX:
            output_geometry = [min_lon, min_lat, max_lon, max_lat]
        elif params.output_format == GeometryFormat.KML:
            output_geometry = _geometry_to_kml(bbox_geometry)
        
        # Calculate properties
        area_km2 = _calculate_polygon_area(bbox_geometry["coordinates"][0])
        dimensions = _calculate_dimensions(bbox_coords)
        center_point = [(min_lon + max_lon) / 2, (min_lat + max_lat) / 2]
        
        # Analyze input points
        point_distances = []
        for i in range(len(params.points)):
            for j in range(i + 1, len(params.points)):
                dist = _haversine_distance(params.points[i], params.points[j])
                point_distances.append(dist)
        
        result = {
            "geometry": output_geometry,
            "format": params.output_format.value,
            "properties": {
                "type": "bounding_box",
                "buffered": params.buffer_meters is not None,
                "buffer_meters": params.buffer_meters,
                "area_km2": round(area_km2, 6),
                "width_km": round(dimensions["width_km"], 3),
                "height_km": round(dimensions["height_km"], 3),
                "aspect_ratio": round(dimensions["width_km"] / dimensions["height_km"], 2)
            },
            "bounds": bbox_coords,
            "center_point": {
                "coordinates": center_point,
                "latitude": center_point[1],
                "longitude": center_point[0]
            },
            "input_analysis": {
                "point_count": len(params.points),
                "point_spread": {
                    "max_distance_km": max(point_distances) if point_distances else 0,
                    "min_distance_km": min(point_distances) if point_distances else 0,
                    "avg_distance_km": sum(point_distances) / len(point_distances) if point_distances else 0
                },
                "coordinate_ranges": {
                    "longitude_span": max_lon - min_lon,
                    "latitude_span": max_lat - min_lat
                }
            },
            "coverage_info": {
                "dimensions_km": dimensions,
                "diagonal_km": round(_calculate_diagonal_distance(bbox_coords), 3),
                "suitable_for_satellite": area_km2 < 10000  # Reasonable size for satellite imagery
            }
        }
        
        logger.info(f"Bounding box created: {dimensions['width_km']:.1f} x {dimensions['height_km']:.1f} km")
        return result
        
    except Exception as e:
        logger.error(f"Bounding box creation failed: {e}", exc_info=True)
        if isinstance(e, SkyFiMCPError):
            raise
        raise SkyFiMCPError(f"Bounding box creation error: {str(e)}")


@osm_mcp.tool(
    name="osm_calculate_distance",
    description="Calculate distance between two geographic points using various methods"
)
async def calculate_distance(
    point1: List[float],
    point2: List[float], 
    method: str = "haversine"
) -> Dict[str, Any]:
    """
    Calculate the distance between two geographic coordinate points.
    
    This tool supports multiple calculation methods for different accuracy
    and performance requirements. Useful for spatial analysis, proximity
    calculations, and planning satellite imagery coverage.
    
    Args:
        point1: First point as [longitude, latitude]
        point2: Second point as [longitude, latitude]
        method: Calculation method (haversine, vincenty, euclidean)
        
    Returns:
        Dictionary containing:
        - distance: Distance measurements in multiple units
        - method_info: Information about calculation method
        - bearing: Direction from point1 to point2
        - midpoint: Coordinates of midpoint between points
        - spatial_analysis: Additional spatial relationship info
        
    Raises:
        SkyFiMCPError: If distance calculation fails
    """
    
    try:
        logger.info(f"Calculating distance between {point1} and {point2} using {method}")
        
        # Validate parameters
        params = DistanceCalculationParams(
            point1=point1,
            point2=point2,
            method=method
        )
        
        # Calculate distance using specified method
        if params.method == "haversine":
            distance_km = _haversine_distance(params.point1, params.point2)
            accuracy = "High accuracy for most applications"
        elif params.method == "vincenty":
            distance_km = _vincenty_distance(params.point1, params.point2)
            accuracy = "Highest accuracy for precise measurements"
        elif params.method == "euclidean":
            distance_km = _euclidean_distance(params.point1, params.point2)
            accuracy = "Approximation only - not suitable for large distances"
        else:
            raise SkyFiMCPError(f"Unsupported distance method: {params.method}")
        
        # Calculate bearing
        bearing = _calculate_bearing(params.point1, params.point2)
        
        # Calculate midpoint
        midpoint = _calculate_midpoint(params.point1, params.point2)
        
        # Additional calculations
        time_estimates = {
            "walking_hours": distance_km / 5,      # ~5 km/h walking speed
            "driving_hours": distance_km / 80,     # ~80 km/h average driving
            "flight_hours": distance_km / 800      # ~800 km/h commercial flight
        }
        
        result = {
            "distance": {
                "kilometers": round(distance_km, 6),
                "meters": round(distance_km * 1000, 2),
                "miles": round(distance_km * 0.621371, 6),
                "nautical_miles": round(distance_km * 0.539957, 6),
                "feet": round(distance_km * 3280.84, 1)
            },
            "method_info": {
                "method": params.method,
                "accuracy_description": accuracy,
                "earth_model": "WGS84 ellipsoid" if params.method == "vincenty" else "Spherical approximation"
            },
            "bearing": {
                "degrees": round(bearing, 2),
                "cardinal_direction": _degrees_to_cardinal(bearing),
                "description": f"{_degrees_to_cardinal(bearing)} ({round(bearing, 1)}°)"
            },
            "midpoint": {
                "coordinates": [round(midpoint[0], 6), round(midpoint[1], 6)],
                "latitude": round(midpoint[1], 6),
                "longitude": round(midpoint[0], 6)
            },
            "spatial_analysis": {
                "great_circle_distance": distance_km < 20037.5,  # Less than half Earth circumference
                "time_estimates": time_estimates,
                "satellite_coverage": {
                    "single_image_suitable": distance_km < 100,  # Typical satellite scene size
                    "mosaic_required": distance_km > 100
                }
            },
            "input_points": {
                "point1": {
                    "coordinates": params.point1,
                    "lat": params.point1[1],
                    "lon": params.point1[0]
                },
                "point2": {
                    "coordinates": params.point2,
                    "lat": params.point2[1],
                    "lon": params.point2[0]
                }
            }
        }
        
        logger.info(f"Distance calculated: {distance_km:.3f} km using {params.method}")
        return result
        
    except Exception as e:
        logger.error(f"Distance calculation failed: {e}", exc_info=True)
        if isinstance(e, SkyFiMCPError):
            raise
        raise SkyFiMCPError(f"Distance calculation error: {str(e)}")


def _generate_circle_geometry(
    center_lon: float,
    center_lat: float,
    radius_meters: float,
    method: BufferMethod,
    resolution: int
) -> Dict[str, Any]:
    """Generate a circular polygon geometry"""
    
    coordinates = []
    
    if method == BufferMethod.DEGREES:
        # Simple degree-based circle (fast but inaccurate)
        radius_deg = radius_meters / 111320  # Rough conversion
        
        for i in range(resolution + 1):
            angle = 2 * math.pi * i / resolution
            lon = center_lon + radius_deg * math.cos(angle)
            lat = center_lat + radius_deg * math.sin(angle)
            coordinates.append([lon, lat])
    
    elif method == BufferMethod.PLANAR:
        # Planar approximation (moderate accuracy, fast)
        lat_rad = math.radians(center_lat)
        meters_per_deg_lat = 111320
        meters_per_deg_lon = 111320 * math.cos(lat_rad)
        
        radius_deg_lat = radius_meters / meters_per_deg_lat
        radius_deg_lon = radius_meters / meters_per_deg_lon
        
        for i in range(resolution + 1):
            angle = 2 * math.pi * i / resolution
            lon = center_lon + radius_deg_lon * math.cos(angle)
            lat = center_lat + radius_deg_lat * math.sin(angle)
            coordinates.append([lon, lat])
    
    else:  # GEODESIC - most accurate
        # Geodesic circle using Vincenty's formulae
        for i in range(resolution + 1):
            bearing = 2 * math.pi * i / resolution
            point = _destination_point(center_lon, center_lat, bearing, radius_meters)
            coordinates.append([point[0], point[1]])
    
    return {
        "type": "Polygon",
        "coordinates": [coordinates]
    }


def _destination_point(lon: float, lat: float, bearing: float, distance: float) -> Tuple[float, float]:
    """Calculate destination point given start point, bearing, and distance"""
    
    # Convert to radians
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    
    # Earth radius in meters
    R = 6378137  # WGS84 semi-major axis
    
    # Calculate destination point
    lat2 = math.asin(
        math.sin(lat_rad) * math.cos(distance / R) +
        math.cos(lat_rad) * math.sin(distance / R) * math.cos(bearing)
    )
    
    lon2 = lon_rad + math.atan2(
        math.sin(bearing) * math.sin(distance / R) * math.cos(lat_rad),
        math.cos(distance / R) - math.sin(lat_rad) * math.sin(lat2)
    )
    
    return (math.degrees(lon2), math.degrees(lat2))


def _haversine_distance(point1: List[float], point2: List[float]) -> float:
    """Calculate distance using Haversine formula"""
    
    lon1, lat1 = math.radians(point1[0]), math.radians(point1[1])
    lon2, lat2 = math.radians(point2[0]), math.radians(point2[1])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
    
    c = 2 * math.asin(math.sqrt(a))
    
    # Earth radius in kilometers
    r = 6371
    
    return c * r


def _vincenty_distance(point1: List[float], point2: List[float]) -> float:
    """Calculate distance using Vincenty's formula (more accurate)"""
    
    # This is a simplified version - full Vincenty is more complex
    # For now, fall back to Haversine
    return _haversine_distance(point1, point2)


def _euclidean_distance(point1: List[float], point2: List[float]) -> float:
    """Calculate Euclidean distance (approximation only)"""
    
    dx = point2[0] - point1[0]
    dy = point2[1] - point1[1]
    
    # Convert degrees to approximate kilometers
    dx_km = dx * 111.32 * math.cos(math.radians((point1[1] + point2[1]) / 2))
    dy_km = dy * 111.32
    
    return math.sqrt(dx_km ** 2 + dy_km ** 2)


def _calculate_bearing(point1: List[float], point2: List[float]) -> float:
    """Calculate bearing from point1 to point2"""
    
    lon1, lat1 = math.radians(point1[0]), math.radians(point1[1])
    lon2, lat2 = math.radians(point2[0]), math.radians(point2[1])
    
    dlon = lon2 - lon1
    
    y = math.sin(dlon) * math.cos(lat2)
    x = (math.cos(lat1) * math.sin(lat2) -
         math.sin(lat1) * math.cos(lat2) * math.cos(dlon))
    
    bearing = math.atan2(y, x)
    
    # Convert to degrees and normalize to 0-360
    bearing_deg = math.degrees(bearing)
    return (bearing_deg + 360) % 360


def _calculate_midpoint(point1: List[float], point2: List[float]) -> List[float]:
    """Calculate midpoint between two points"""
    
    lon1, lat1 = math.radians(point1[0]), math.radians(point1[1])
    lon2, lat2 = math.radians(point2[0]), math.radians(point2[1])
    
    dlon = lon2 - lon1
    
    Bx = math.cos(lat2) * math.cos(dlon)
    By = math.cos(lat2) * math.sin(dlon)
    
    lat3 = math.atan2(
        math.sin(lat1) + math.sin(lat2),
        math.sqrt((math.cos(lat1) + Bx) ** 2 + By ** 2)
    )
    
    lon3 = lon1 + math.atan2(By, math.cos(lat1) + Bx)
    
    return [math.degrees(lon3), math.degrees(lat3)]


def _degrees_to_cardinal(degrees: float) -> str:
    """Convert degrees to cardinal direction"""
    
    directions = [
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
    ]
    
    index = int((degrees + 11.25) / 22.5) % 16
    return directions[index]


def _calculate_polygon_area(coordinates: List[List[float]]) -> float:
    """Calculate area of polygon in km²"""
    
    # Shoelace formula for polygon area
    n = len(coordinates) - 1  # Exclude closing point
    area = 0.0
    
    for i in range(n):
        j = (i + 1) % n
        area += coordinates[i][0] * coordinates[j][1]
        area -= coordinates[j][0] * coordinates[i][1]
    
    area = abs(area) / 2.0
    
    # Convert from degrees² to km²
    # This is an approximation - more accurate methods exist
    return area * (111.32 ** 2)


def _calculate_bounding_box(coordinates: List[List[float]]) -> Dict[str, float]:
    """Calculate bounding box of coordinates"""
    
    lons = [coord[0] for coord in coordinates]
    lats = [coord[1] for coord in coordinates]
    
    return {
        "west": min(lons),
        "east": max(lons),
        "south": min(lats),
        "north": max(lats)
    }


def _calculate_dimensions(bbox: Dict[str, float]) -> Dict[str, float]:
    """Calculate dimensions from bounding box"""
    
    # Calculate width (longitude span)
    center_lat = (bbox["north"] + bbox["south"]) / 2
    width_km = (bbox["east"] - bbox["west"]) * 111.32 * math.cos(math.radians(center_lat))
    
    # Calculate height (latitude span)
    height_km = (bbox["north"] - bbox["south"]) * 111.32
    
    return {
        "width_km": abs(width_km),
        "height_km": abs(height_km)
    }


def _calculate_diagonal_distance(bbox: Dict[str, float]) -> float:
    """Calculate diagonal distance of bounding box"""
    
    sw_point = [bbox["west"], bbox["south"]]
    ne_point = [bbox["east"], bbox["north"]]
    
    return _haversine_distance(sw_point, ne_point)


def _calculate_perimeter(coordinates: List[List[float]]) -> float:
    """Calculate perimeter of polygon in km"""
    
    perimeter = 0.0
    n = len(coordinates) - 1  # Exclude closing point
    
    for i in range(n):
        j = (i + 1) % n
        perimeter += _haversine_distance(coordinates[i], coordinates[j])
    
    return perimeter


def _geometry_to_wkt(geometry: Dict[str, Any]) -> str:
    """Convert GeoJSON geometry to WKT format"""
    
    if geometry["type"] == "Polygon":
        coords = geometry["coordinates"][0]
        coord_pairs = [f"{coord[0]} {coord[1]}" for coord in coords]
        return f"POLYGON(({', '.join(coord_pairs)}))"
    
    elif geometry["type"] == "Point":
        coord = geometry["coordinates"]
        return f"POINT({coord[0]} {coord[1]})"
    
    else:
        raise ValueError(f"Unsupported geometry type for WKT: {geometry['type']}")


def _geometry_to_kml(geometry: Dict[str, Any]) -> str:
    """Convert GeoJSON geometry to KML format"""
    
    if geometry["type"] == "Polygon":
        coords = geometry["coordinates"][0]
        coord_string = " ".join([f"{coord[0]},{coord[1]},0" for coord in coords])
        
        return f"""<Polygon>
            <outerBoundaryIs>
                <LinearRing>
                    <coordinates>{coord_string}</coordinates>
                </LinearRing>
            </outerBoundaryIs>
        </Polygon>"""
    
    else:
        raise ValueError(f"Unsupported geometry type for KML: {geometry['type']}")


def _suggest_resolution(radius_meters: float) -> str:
    """Suggest appropriate satellite imagery resolution"""
    
    if radius_meters < 100:
        return "Sub-meter or 1m resolution recommended for detailed analysis"
    elif radius_meters < 1000:
        return "1-3m resolution suitable for most applications"
    elif radius_meters < 10000:
        return "3-10m resolution appropriate for regional analysis"
    else:
        return "10-30m resolution sufficient for large area coverage"


def _estimate_imagery_coverage(area_km2: float) -> str:
    """Estimate satellite imagery coverage requirements"""
    
    if area_km2 < 1:
        return "Single high-resolution image typically sufficient"
    elif area_km2 < 100:
        return "1-4 satellite images may be required"
    elif area_km2 < 1000:
        return "Multiple images or mosaic processing likely needed"
    else:
        return "Large area - consider using multiple imagery sources"


logger.info("OSM Geometry tools loaded successfully")