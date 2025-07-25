"""
Weather Service Module

This module provides integration with weather data services through
the MCP protocol for mission planning and environmental context.

Features:
- Current weather conditions for locations
- Weather forecasts for planning missions
- Historical weather data analysis
- Severe weather alerts and warnings
- Weather-based mission feasibility assessment
- Cloud cover analysis for optical missions

The weather service requires API key authentication and provides
valuable environmental context for satellite imagery missions.
"""


import logging
from typing import TYPE_CHECKING
from fastmcp import FastMCP

if TYPE_CHECKING:
    from ..servers.context import MainAppContext

logger = logging.getLogger("mcp-skyfi.weather")

# Initialize Weather service MCP instance
weather_mcp = FastMCP(name="Weather Data Integration")

# Import and register tools after MCP instance creation
from . import forecasts    # Weather forecast tools
from . import conditions   # Current weather conditions
from . import alerts       # Weather alerts and warnings
from . import config       # Weather service configuration

logger.info("Weather service module initialized with all tool categories")

__all__ = [
    "weather_mcp",
]