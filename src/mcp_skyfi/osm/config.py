"""
OSM Configuration

Configuration management for OpenStreetMap and geocoding service integration.
OSM services are generally public and require no authentication, but this
configuration allows for customization of endpoints, rate limits, and features.
"""


import os
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

from ..utils.environment import (
    get_env_bool, get_env_int, get_env_list, validate_env_url
)


@dataclass
class OSMConfig:
    """
    Configuration for OpenStreetMap and geocoding service integration.
    
    OSM services are public and require no authentication, but this configuration
    allows customization of service endpoints, rate limits, caching, and features.
    """
    
    # Service endpoints
    nominatim_url: str = "https://nominatim.openstreetmap.org"
    """Nominatim geocoding service URL"""
    
    overpass_url: str = "https://overpass-api.de/api"
    """Overpass API URL for advanced OSM queries"""
    
    # Network configuration
    timeout: int = 15
    """HTTP request timeout in seconds"""
    
    max_retries: int = 2
    """Maximum number of retry attempts"""
    
    rate_limit: int = 1
    """Rate limit in requests per second (respect OSM usage policy)"""
    
    # Service configuration
    user_agent: str = "SkyFi-MCP-Server/1.0.0"
    """User agent string for OSM API requests"""
    
    language: str = "en"
    """Preferred language for results (ISO 639-1 code)"""
    
    country_codes: Optional[List[str]] = None
    """Restrict results to specific countries (ISO 3166-1 alpha-2)"""
    
    # Feature toggles
    enable_geocoding: bool = True
    """Enable forward and reverse geocoding tools"""
    
    enable_places_search: bool = True
    """Enable POI and business search tools"""
    
    enable_geometry_tools: bool = True
    """Enable AOI generation and spatial tools"""
    
    enable_overpass_queries: bool = False
    """Enable advanced Overpass API queries (higher complexity)"""
    
    # Result limits and formatting
    max_results: int = 50
    """Default maximum number of results per query"""
    
    include_geometry: bool = True
    """Include geometry in results by default"""
    
    geometry_format: str = "geojson"
    """Geometry format: geojson, wkt, or bbox"""
    
    # Caching configuration  
    cache_enabled: bool = True
    """Enable response caching for read operations"""
    
    cache_ttl: int = 3600
    """Cache time-to-live in seconds (1 hour default)"""
    
    # Advanced options
    custom_headers: Optional[Dict[str, str]] = None
    """Custom HTTP headers for requests"""
    
    proxy_url: Optional[str] = None
    """HTTP proxy URL if required"""

    @classmethod
    def from_env(cls) -> 'OSMConfig':
        """
        Create configuration from environment variables.
        
        Environment Variables:
            OSM_NOMINATIM_URL: Custom Nominatim endpoint (default: OSM public)
            OSM_OVERPASS_URL: Custom Overpass API endpoint  
            OSM_TIMEOUT: Request timeout in seconds (default: 15)
            OSM_MAX_RETRIES: Maximum retry attempts (default: 2)
            OSM_RATE_LIMIT: Rate limit per second (default: 1)
            OSM_USER_AGENT: Custom user agent string
            OSM_LANGUAGE: Preferred language code (default: en)
            OSM_COUNTRY_CODES: Comma-separated country codes
            OSM_ENABLE_GEOCODING: Enable geocoding tools (default: true)
            OSM_ENABLE_PLACES: Enable places search (default: true)
            OSM_ENABLE_GEOMETRY: Enable geometry tools (default: true) 
            OSM_ENABLE_OVERPASS: Enable Overpass queries (default: false)
            OSM_MAX_RESULTS: Maximum results per query (default: 50)
            OSM_GEOMETRY_FORMAT: Geometry format (default: geojson)
            OSM_CACHE_ENABLED: Enable caching (default: true)
            OSM_CACHE_TTL: Cache TTL seconds (default: 3600)
            OSM_PROXY_URL: HTTP proxy URL
        
        Returns:
            OSMConfig instance populated from environment
        """
        
        # Parse country codes
        country_codes = get_env_list("OSM_COUNTRY_CODES")
        
        # Parse custom headers
        custom_headers = {}
        if os.getenv("OSM_CUSTOM_HEADERS"):
            for header_pair in os.getenv("OSM_CUSTOM_HEADERS").split(","):
                if "=" in header_pair:
                    key, value = header_pair.split("=", 1)
                    custom_headers[key.strip()] = value.strip()

        return cls(
            # Endpoints
            nominatim_url=validate_env_url("OSM_NOMINATIM_URL") or "https://nominatim.openstreetmap.org",
            overpass_url=validate_env_url("OSM_OVERPASS_URL") or "https://overpass-api.de/api",
            
            # Network
            timeout=get_env_int("OSM_TIMEOUT", 15),
            max_retries=get_env_int("OSM_MAX_RETRIES", 2),
            rate_limit=get_env_int("OSM_RATE_LIMIT", 1),
            
            # Service
            user_agent=os.getenv("OSM_USER_AGENT", "SkyFi-MCP-Server/1.0.0"),
            language=os.getenv("OSM_LANGUAGE", "en"),
            country_codes=country_codes,
            
            # Features
            enable_geocoding=get_env_bool("OSM_ENABLE_GEOCODING", True),
            enable_places_search=get_env_bool("OSM_ENABLE_PLACES", True),
            enable_geometry_tools=get_env_bool("OSM_ENABLE_GEOMETRY", True),
            enable_overpass_queries=get_env_bool("OSM_ENABLE_OVERPASS", False),
            
            # Results
            max_results=get_env_int("OSM_MAX_RESULTS", 50),
            include_geometry=get_env_bool("OSM_INCLUDE_GEOMETRY", True),
            geometry_format=os.getenv("OSM_GEOMETRY_FORMAT", "geojson"),
            
            # Caching
            cache_enabled=get_env_bool("OSM_CACHE_ENABLED", True),
            cache_ttl=get_env_int("OSM_CACHE_TTL", 3600),
            
            # Advanced
            custom_headers=custom_headers if custom_headers else None,
            proxy_url=validate_env_url("OSM_PROXY_URL")
        )

    def get_effective_headers(self) -> Dict[str, str]:
        """
        Get effective HTTP headers including user agent and custom headers.
        
        Returns:
            Dictionary of HTTP headers for requests
        """
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
            "Accept-Language": self.language
        }
        
        # Add custom headers
        if self.custom_headers:
            headers.update(self.custom_headers)
        
        return headers

    def get_nominatim_params(self) -> Dict[str, Any]:
        """
        Get default parameters for Nominatim API requests.
        
        Returns:
            Dictionary of default query parameters
        """
        params = {
            "format": "json",
            "limit": self.max_results,
            "addressdetails": 1,
            "extratags": 1,
            "namedetails": 1,
            "accept-language": self.language
        }
        
        if self.include_geometry:
            if self.geometry_format == "geojson":
                params["polygon_geojson"] = 1
            elif self.geometry_format == "wkt": 
                params["polygon_text"] = 1
            else:
                params["polygon_kml"] = 1
        
        if self.country_codes:
            params["countrycodes"] = ",".join(self.country_codes)
        
        return params

    def validate_config(self) -> List[str]:
        """
        Validate the current configuration and return any issues.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Check required fields
        if not self.nominatim_url:
            errors.append("Nominatim URL is required")
        
        # Validate URLs
        for url_field, url_value in [
            ("nominatim_url", self.nominatim_url),
            ("overpass_url", self.overpass_url),
            ("proxy_url", self.proxy_url)
        ]:
            if url_value and not (url_value.startswith("http://") or url_value.startswith("https://")):
                errors.append(f"{url_field} must be a valid HTTP(S) URL")
        
        # Validate numeric fields
        if self.timeout <= 0:
            errors.append("Timeout must be greater than 0")
        
        if self.max_retries < 0:
            errors.append("Max retries cannot be negative")
        
        if self.rate_limit <= 0:
            errors.append("Rate limit must be greater than 0")
        
        if self.max_results <= 0 or self.max_results > 500:
            errors.append("Max results must be between 1 and 500")
        
        if self.cache_ttl <= 0:
            errors.append("Cache TTL must be greater than 0")
        
        # Validate enums
        if self.geometry_format not in ["geojson", "wkt", "bbox"]:
            errors.append("Geometry format must be 'geojson', 'wkt', or 'bbox'")
        
        # Validate country codes
        if self.country_codes:
            for code in self.country_codes:
                if len(code) != 2 or not code.isalpha():
                    errors.append(f"Invalid country code: {code} (must be ISO 3166-1 alpha-2)")
        
        return errors

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary for debugging/logging.
        
        Returns:
            Dictionary representation of configuration
        """
        return {
            "endpoints": {
                "nominatim_url": self.nominatim_url,
                "overpass_url": self.overpass_url
            },
            "network": {
                "timeout": self.timeout,
                "max_retries": self.max_retries,
                "rate_limit": self.rate_limit,
                "proxy_url": self.proxy_url
            },
            "service": {
                "user_agent": self.user_agent,
                "language": self.language,
                "country_codes": self.country_codes
            },
            "features": {
                "geocoding": self.enable_geocoding,
                "places_search": self.enable_places_search,
                "geometry_tools": self.enable_geometry_tools,
                "overpass_queries": self.enable_overpass_queries
            },
            "results": {
                "max_results": self.max_results,
                "include_geometry": self.include_geometry,
                "geometry_format": self.geometry_format
            },
            "cache": {
                "enabled": self.cache_enabled,
                "ttl": self.cache_ttl
            },
            "custom_headers_count": len(self.custom_headers) if self.custom_headers else 0
        }

    def __repr__(self) -> str:
        """String representation for debugging."""
        enabled_features = sum([
            self.enable_geocoding,
            self.enable_places_search, 
            self.enable_geometry_tools,
            self.enable_overpass_queries
        ])
        
        return (
            f"OSMConfig(nominatim={self.nominatim_url}, "
            f"features={enabled_features}, cache={self.cache_enabled})"
        )