"""
OpenStreetMap (OSM) Service Module

This module provides integration with OpenStreetMap and related geocoding
services through the MCP protocol, enabling AI applications to:

Features:
- Forward and reverse geocoding using Nominatim API
- Point of Interest (POI) search and discovery  
- Area of Interest (AOI) generation from addresses/locations
- Spatial operations and geometry utilities
- Business and amenity search capabilities
- Multi-format coordinate conversion

The OSM service requires no authentication and is freely available,
making it an ideal complement to paid satellite imagery services.
"""


import logging
from typing import TYPE_CHECKING
from fastmcp import FastMCP

if TYPE_CHECKING:
    from ..servers.context import MainAppContext

logger = logging.getLogger("mcp-skyfi.osm")

# Initialize OSM service MCP instance
osm_mcp = FastMCP(name="OpenStreetMap Integration")

# Import and register tools after MCP instance creation
from . import geocoding    # Forward/reverse geocoding tools
from . import places      # POI search and discovery tools  
from . import geometry    # AOI generation and spatial operations
from . import config      # OSM service configuration

logger.info("OSM service module initialized with all tool categories")