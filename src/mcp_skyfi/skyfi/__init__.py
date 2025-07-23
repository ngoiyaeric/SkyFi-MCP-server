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

from __future__ import annotations

import logging
from fastmcp import FastMCP
from ..servers.context import MainAppContext

logger = logging.getLogger("mcp-skyfi.skyfi")

# Initialize SkyFi service MCP instance
skyfi_mcp = FastMCP[MainAppContext](name="SkyFi Platform API")

# Import and register tools after MCP instance creation
from . import archives  # Archive search and management tools
from . import ordering   # Order creation and management tools
from . import notifications  # Webhook and notification tools
from . import pricing    # Pricing and cost estimation tools
from . import feasibility  # Satellite pass predictions

logger.info("SkyFi service module initialized with all tool categories")