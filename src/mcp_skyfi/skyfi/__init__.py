"""
SkyFi Service Module

This module provides integration with the SkyFi Platform API for satellite
imagery search, ordering, and management through the MCP protocol.

Features:
- Archive image search with geospatial filters
- Image ordering with delivery to cloud storage
- Order status tracking and management  
- Pricing and feasibility checks
- Webhook notifications for new imagery
- Multi-authentication support (API key, OAuth)
"""


import logging
from typing import TYPE_CHECKING
from fastmcp import FastMCP

if TYPE_CHECKING:
    from ..servers.context import MainAppContext

logger = logging.getLogger("mcp-skyfi.skyfi")

# Initialize SkyFi service MCP instance
skyfi_mcp = FastMCP(name="SkyFi Platform API")

# Import and register tools after MCP instance creation
from . import archives      # Archive search and management tools
from . import ordering      # Order creation and management tools
from . import notifications # Webhook and notification tools
from . import pricing       # Pricing and cost estimation tools
from . import feasibility   # Satellite pass predictions
# from . import factory_integration_example  # Factory pattern examples - disabled to avoid circular imports
from .config import SkyFiConfig
from .factory import SkyFiClientFactory, get_client_factory, create_skyfi_client
from .dependencies import get_skyfi_client, SkyFiContext

logger.info("SkyFi service module initialized with factory and dependencies")

__all__ = [
    "skyfi_mcp",
    "SkyFiConfig",
    "SkyFiClientFactory",
    "get_client_factory", 
    "create_skyfi_client",
    "get_skyfi_client",
    "SkyFiContext"
]