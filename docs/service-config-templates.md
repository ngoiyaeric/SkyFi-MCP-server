# Service Configuration Templates and Patterns

## Overview

This document provides comprehensive templates and patterns for service configuration classes in the SkyFi MCP server. Each service follows consistent patterns while allowing for service-specific customization.

## 1. Base Configuration Class Template

### 1.1 Environment Utilities

```python
# utils/environment.py
import os
from typing import Any, List, Optional

def get_env_bool(key: str, default: bool = False) -> bool:
    """Get boolean environment variable with proper parsing."""
    value = os.getenv(key, "").lower()
    if value in ("true", "1", "yes", "on"):
        return True
    elif value in ("false", "0", "no", "off"):
        return False
    else:
        return default

def get_env_int(key: str, default: int = 0) -> int:
    """Get integer environment variable with validation."""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default

def get_env_float(key: str, default: float = 0.0) -> float:
    """Get float environment variable with validation."""
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        return default

def get_env_list(key: str, separator: str = ",", default: Optional[List[str]] = None) -> Optional[List[str]]:
    """Get list environment variable with proper parsing."""
    value = os.getenv(key)
    if not value:
        return default
    
    items = [item.strip() for item in value.split(separator) if item.strip()]
    return items if items else default

def get_env_dict(key: str, item_separator: str = ",", kv_separator: str = "=") -> dict[str, str]:
    """Parse environment variable as dictionary."""
    value = os.getenv(key, "")
    if not value:
        return {}
    
    result = {}
    for item in value.split(item_separator):
        item = item.strip()
        if kv_separator in item:
            k, v = item.split(kv_separator, 1)
            result[k.strip()] = v.strip()
    
    return result
```

### 1.2 Base Configuration Pattern

```python
# models/base.py
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar, Optional, Dict, Any
from ..utils.environment import get_env_bool, get_env_int, get_env_float, get_env_dict

@dataclass
class BaseServiceConfig(ABC):
    """
    Base configuration class with common patterns for all services.
    
    This class provides:
    - Consistent authentication method detection
    - Environment variable parsing patterns
    - Configuration validation
    - Service health checking
    """
    
    # Required configuration
    url: str = ""
    
    # Authentication methods (in order of precedence)
    # OAuth 2.0 (highest priority if configured)
    oauth_client_id: Optional[str] = None
    oauth_client_secret: Optional[str] = None  
    oauth_access_token: Optional[str] = None
    oauth_refresh_token: Optional[str] = None
    oauth_scope: Optional[str] = None
    
    # API Token/Key authentication
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    username: Optional[str] = None
    
    # Personal Access Token (for enterprise/self-hosted)
    personal_token: Optional[str] = None
    
    # Network configuration
    ssl_verify: bool = True
    timeout: int = 30
    max_retries: int = 3
    
    # Filtering and access control
    custom_headers: Optional[Dict[str, str]] = None
    
    # Service metadata
    service_name: ClassVar[str] = ""
    env_prefix: ClassVar[str] = ""

    @classmethod
    @abstractmethod
    def from_env(cls) -> BaseServiceConfig:
        """Create configuration from environment variables."""
        pass

    @abstractmethod
    def is_auth_configured(self) -> bool:
        """Check if any authentication method is properly configured."""
        pass

    def get_auth_method(self) -> str:
        """Determine the best available authentication method."""
        if (self.oauth_client_id and self.oauth_client_secret):
            return "oauth"
        elif self.api_key:
            return "api_key"
        elif self.personal_token:
            return "personal_token"
        else:
            return "none"

    def _has_stored_tokens(self) -> bool:
        """Check if OAuth tokens are stored securely."""
        # Implementation depends on token storage strategy
        # Could check secure storage, database, etc.
        return False

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        if not self.url:
            errors.append(f"{self.service_name} URL is required")
        
        if not self.is_auth_configured():
            errors.append(f"{self.service_name} authentication not configured")
        
        if self.timeout <= 0:
            errors.append("Timeout must be positive")
        
        if self.max_retries < 0:
            errors.append("Max retries cannot be negative")
        
        return errors

    def get_display_info(self) -> Dict[str, Any]:
        """Get configuration info safe for display (no secrets)."""
        return {
            "service": self.service_name,
            "url": self.url,
            "auth_method": self.get_auth_method(),
            "ssl_verify": self.ssl_verify,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "has_custom_headers": bool(self.custom_headers),
        }
```

## 2. SkyFi Service Configuration

### 2.1 SkyFi Configuration Class

```python
# skyfi/config.py
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, List, ClassVar
from ..models.base import BaseServiceConfig
from ..utils.environment import get_env_bool, get_env_int, get_env_float, get_env_list, get_env_dict

@dataclass
class SkyFiConfig(BaseServiceConfig):
    """
    Configuration for SkyFi API service integration.
    
    Environment Variables:
        SKYFI_URL: Base URL for SkyFi API (default: https://app.skyfi.com/platform-api)
        SKYFI_API_KEY: SkyFi API key for authentication
        SKYFI_OAUTH_CLIENT_ID: OAuth client ID
        SKYFI_OAUTH_CLIENT_SECRET: OAuth client secret
        SKYFI_OAUTH_ACCESS_TOKEN: OAuth access token
        SKYFI_PERSONAL_TOKEN: Personal access token
        SKYFI_SSL_VERIFY: Verify SSL certificates (default: true)
        SKYFI_TIMEOUT: Request timeout in seconds (default: 30)
        SKYFI_MAX_RETRIES: Maximum retry attempts (default: 3)
        SKYFI_DEFAULT_PAGE_SIZE: Default page size for searches (default: 20)
        SKYFI_MAX_PAGE_SIZE: Maximum page size allowed (default: 100)
        SKYFI_CACHE_TTL: Cache TTL in seconds (default: 300)
        SKYFI_RATE_LIMIT_REQUESTS: Rate limit requests per window (default: 100)
        SKYFI_RATE_LIMIT_WINDOW: Rate limit window in seconds (default: 60)
        SKYFI_MAX_ORDER_COST: Maximum order cost limit in USD
        SKYFI_ALLOWED_ORDER_TYPES: Comma-separated list of allowed order types
        SKYFI_DEFAULT_DELIVERY_DRIVER: Default delivery driver (default: S3)
        SKYFI_CUSTOM_HEADERS: Custom headers in format "key=value,key2=value2"
    """
    
    # Service metadata
    service_name: ClassVar[str] = "SkyFi"
    env_prefix: ClassVar[str] = "SKYFI"
    
    # SkyFi-specific settings
    default_page_size: int = 20
    max_page_size: int = 100
    cache_ttl_seconds: int = 300
    rate_limit_requests: int = 100
    rate_limit_window: int = 60
    
    # Business logic constraints
    max_order_cost: Optional[float] = None
    allowed_order_types: Optional[List[str]] = None
    default_delivery_driver: str = "S3"
    
    # API-specific settings
    budget_warning_threshold: float = 0.8  # Warn when 80% of budget used
    max_concurrent_orders: int = 10
    
    @classmethod
    def from_env(cls) -> SkyFiConfig:
        """Create configuration from environment variables."""
        
        # Parse custom headers
        custom_headers = get_env_dict("SKYFI_CUSTOM_HEADERS")

        return cls(
            # Base configuration
            url=os.getenv("SKYFI_URL", "https://app.skyfi.com/platform-api"),
            
            # Authentication (multiple methods supported)
            api_key=os.getenv("SKYFI_API_KEY"),
            oauth_client_id=os.getenv("SKYFI_OAUTH_CLIENT_ID"),
            oauth_client_secret=os.getenv("SKYFI_OAUTH_CLIENT_SECRET"),
            oauth_access_token=os.getenv("SKYFI_OAUTH_ACCESS_TOKEN"),
            oauth_refresh_token=os.getenv("SKYFI_OAUTH_REFRESH_TOKEN"),
            oauth_scope=os.getenv("SKYFI_OAUTH_SCOPE"),
            personal_token=os.getenv("SKYFI_PERSONAL_TOKEN"),
            username=os.getenv("SKYFI_USERNAME"),
            
            # Network configuration
            ssl_verify=get_env_bool("SKYFI_SSL_VERIFY", True),
            timeout=get_env_int("SKYFI_TIMEOUT", 30),
            max_retries=get_env_int("SKYFI_MAX_RETRIES", 3),
            
            # Service-specific configuration
            default_page_size=get_env_int("SKYFI_DEFAULT_PAGE_SIZE", 20),
            max_page_size=get_env_int("SKYFI_MAX_PAGE_SIZE", 100),
            cache_ttl_seconds=get_env_int("SKYFI_CACHE_TTL", 300),
            rate_limit_requests=get_env_int("SKYFI_RATE_LIMIT_REQUESTS", 100),
            rate_limit_window=get_env_int("SKYFI_RATE_LIMIT_WINDOW", 60),
            
            # Business constraints
            max_order_cost=get_env_float("SKYFI_MAX_ORDER_COST", 0) or None,
            default_delivery_driver=os.getenv("SKYFI_DEFAULT_DELIVERY_DRIVER", "S3"),
            budget_warning_threshold=get_env_float("SKYFI_BUDGET_WARNING_THRESHOLD", 0.8),
            max_concurrent_orders=get_env_int("SKYFI_MAX_CONCURRENT_ORDERS", 10),
            
            # Filtering and access control
            allowed_order_types=get_env_list("SKYFI_ALLOWED_ORDER_TYPES"),
            custom_headers=custom_headers if custom_headers else None,
        )

    def is_auth_configured(self) -> bool:
        """SkyFi requires at minimum an API key."""
        return bool(
            self.api_key or 
            self.oauth_access_token or 
            self.personal_token or
            (self.oauth_client_id and self.oauth_client_secret)
        )

    def validate(self) -> list[str]:
        """Validate SkyFi-specific configuration."""
        errors = super().validate()
        
        # Page size validation
        if self.default_page_size <= 0:
            errors.append("Default page size must be positive")
        
        if self.max_page_size <= 0:
            errors.append("Max page size must be positive")
        
        if self.default_page_size > self.max_page_size:
            errors.append("Default page size cannot exceed max page size")
        
        # Rate limiting validation
        if self.rate_limit_requests <= 0:
            errors.append("Rate limit requests must be positive")
        
        if self.rate_limit_window <= 0:
            errors.append("Rate limit window must be positive")
        
        # Business logic validation
        if self.max_order_cost is not None and self.max_order_cost <= 0:
            errors.append("Max order cost must be positive if specified")
        
        if self.budget_warning_threshold <= 0 or self.budget_warning_threshold > 1:
            errors.append("Budget warning threshold must be between 0 and 1")
        
        # Delivery driver validation
        valid_drivers = ["S3", "GS", "AZURE", "NONE"]
        if self.default_delivery_driver not in valid_drivers:
            errors.append(f"Default delivery driver must be one of: {', '.join(valid_drivers)}")
        
        return errors

    def get_display_info(self) -> dict:
        """Get SkyFi configuration info for display."""
        info = super().get_display_info()
        info.update({
            "default_page_size": self.default_page_size,
            "max_page_size": self.max_page_size,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "rate_limit": f"{self.rate_limit_requests}/{self.rate_limit_window}s",
            "max_order_cost": self.max_order_cost,
            "default_delivery_driver": self.default_delivery_driver,
            "allowed_order_types": self.allowed_order_types,
            "budget_warning_threshold": self.budget_warning_threshold,
        })
        return info
```

## 3. OpenStreetMap Service Configuration

### 3.1 OSM Configuration Class

```python
# osm/config.py
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, List, ClassVar
from ..models.base import BaseServiceConfig
from ..utils.environment import get_env_bool, get_env_int, get_env_float, get_env_list

@dataclass
class OSMConfig(BaseServiceConfig):
    """
    Configuration for OpenStreetMap service integration.
    
    Environment Variables:
        OSM_NOMINATIM_URL: Nominatim geocoding service URL
        OSM_OVERPASS_URL: Overpass API URL for POI queries
        OSM_USER_AGENT: User agent for API requests (required by OSM policy)
        OSM_SSL_VERIFY: Verify SSL certificates (default: true)
        OSM_TIMEOUT: Request timeout in seconds (default: 30)
        OSM_MAX_RETRIES: Maximum retry attempts (default: 3)
        OSM_RATE_LIMIT_DELAY: Delay between requests in seconds (default: 1.0)
        OSM_MAX_RESULTS: Maximum results per query (default: 50)
        OSM_GEOCODE_CACHE_TTL: Geocoding cache TTL in seconds (default: 3600)
        OSM_POI_CACHE_TTL: POI cache TTL in seconds (default: 1800)
        OSM_ALLOWED_COUNTRIES: Comma-separated list of allowed country codes
        OSM_MAX_POLYGON_AREA: Maximum polygon area in square kilometers (default: 10000)
    """
    
    # Service metadata
    service_name: ClassVar[str] = "OpenStreetMap"
    env_prefix: ClassVar[str] = "OSM"
    
    # OSM-specific endpoints
    nominatim_url: str = "https://nominatim.openstreetmap.org"
    overpass_url: str = "https://overpass-api.de/api/interpreter"
    
    # API requirements
    user_agent: str = "SkyFi-MCP-Server/1.0"
    
    # Rate limiting (respect OSM usage policy)
    rate_limit_delay: float = 1.0  # 1 second between requests
    max_results_per_query: int = 50
    
    # Caching configuration
    geocode_cache_ttl: int = 3600  # 1 hour
    poi_cache_ttl: int = 1800     # 30 minutes
    
    # Geographic constraints
    allowed_countries: Optional[List[str]] = None
    max_polygon_area: float = 10000.0  # 10,000 km²
    
    # Service limits
    max_batch_geocode: int = 10
    max_poi_radius: float = 50000.0  # 50km

    @classmethod
    def from_env(cls) -> OSMConfig:
        """Create configuration from environment variables."""
        return cls(
            # Base URL (for compatibility)
            url=os.getenv("OSM_NOMINATIM_URL", "https://nominatim.openstreetmap.org"),
            
            # OSM-specific endpoints
            nominatim_url=os.getenv("OSM_NOMINATIM_URL", "https://nominatim.openstreetmap.org"),
            overpass_url=os.getenv("OSM_OVERPASS_URL", "https://overpass-api.de/api/interpreter"),
            user_agent=os.getenv("OSM_USER_AGENT", "SkyFi-MCP-Server/1.0"),
            
            # Network configuration
            ssl_verify=get_env_bool("OSM_SSL_VERIFY", True),
            timeout=get_env_int("OSM_TIMEOUT", 30),
            max_retries=get_env_int("OSM_MAX_RETRIES", 3),
            
            # Rate limiting and API limits
            rate_limit_delay=get_env_float("OSM_RATE_LIMIT_DELAY", 1.0),
            max_results_per_query=get_env_int("OSM_MAX_RESULTS", 50),
            
            # Caching
            geocode_cache_ttl=get_env_int("OSM_GEOCODE_CACHE_TTL", 3600),
            poi_cache_ttl=get_env_int("OSM_POI_CACHE_TTL", 1800),
            
            # Geographic constraints
            allowed_countries=get_env_list("OSM_ALLOWED_COUNTRIES"),
            max_polygon_area=get_env_float("OSM_MAX_POLYGON_AREA", 10000.0),
            max_batch_geocode=get_env_int("OSM_MAX_BATCH_GEOCODE", 10),
            max_poi_radius=get_env_float("OSM_MAX_POI_RADIUS", 50000.0),
        )

    def is_auth_configured(self) -> bool:
        """OSM services typically don't require authentication."""
        return bool(self.url and self.nominatim_url and self.user_agent)

    def validate(self) -> list[str]:
        """Validate OSM-specific configuration."""
        errors = super().validate()
        
        # User agent is required by OSM policy
        if not self.user_agent or self.user_agent.strip() == "":
            errors.append("User agent is required for OSM API requests")
        
        # Rate limiting validation
        if self.rate_limit_delay < 0:
            errors.append("Rate limit delay cannot be negative")
        
        if self.max_results_per_query <= 0 or self.max_results_per_query > 100:
            errors.append("Max results per query must be between 1 and 100")
        
        # Geographic constraints
        if self.max_polygon_area <= 0:
            errors.append("Max polygon area must be positive")
        
        if self.max_poi_radius <= 0:
            errors.append("Max POI radius must be positive")
        
        if self.max_batch_geocode <= 0 or self.max_batch_geocode > 50:
            errors.append("Max batch geocode must be between 1 and 50")
        
        # URL validation
        if not self.nominatim_url.startswith(("http://", "https://")):
            errors.append("Nominatim URL must be a valid HTTP/HTTPS URL")
        
        if not self.overpass_url.startswith(("http://", "https://")):
            errors.append("Overpass URL must be a valid HTTP/HTTPS URL")
        
        return errors

    def get_display_info(self) -> dict:
        """Get OSM configuration info for display."""
        info = super().get_display_info()
        info.update({
            "nominatim_url": self.nominatim_url,
            "overpass_url": self.overpass_url,
            "user_agent": self.user_agent,
            "rate_limit_delay": f"{self.rate_limit_delay}s",
            "max_results": self.max_results_per_query,
            "geocode_cache_ttl": f"{self.geocode_cache_ttl}s",
            "poi_cache_ttl": f"{self.poi_cache_ttl}s",
            "max_polygon_area": f"{self.max_polygon_area} km²",
            "allowed_countries": self.allowed_countries,
        })
        return info
```

## 4. Weather Service Configuration

### 4.1 Weather Configuration Class

```python
# weather/config.py
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, List, ClassVar
from ..models.base import BaseServiceConfig
from ..utils.environment import get_env_bool, get_env_int, get_env_float, get_env_list

@dataclass
class WeatherConfig(BaseServiceConfig):
    """
    Configuration for Weather API service integration.
    
    Environment Variables:
        WEATHER_URL: Base URL for weather API
        WEATHER_API_KEY: Weather API key for authentication
        WEATHER_PROVIDER: Weather data provider (openweathermap, weatherapi, etc.)
        WEATHER_SSL_VERIFY: Verify SSL certificates (default: true)
        WEATHER_TIMEOUT: Request timeout in seconds (default: 30)
        WEATHER_MAX_RETRIES: Maximum retry attempts (default: 3)
        WEATHER_CACHE_CURRENT_TTL: Current weather cache TTL in seconds (default: 600)
        WEATHER_CACHE_FORECAST_TTL: Forecast cache TTL in seconds (default: 3600)
        WEATHER_CACHE_HISTORICAL_TTL: Historical weather cache TTL (default: 86400)
        WEATHER_MAX_FORECAST_DAYS: Maximum forecast days supported (default: 7)
        WEATHER_MAX_HISTORICAL_DAYS: Maximum historical days supported (default: 30)
        WEATHER_UNITS: Temperature units (metric, imperial, kelvin)
        WEATHER_LANGUAGE: Language for weather descriptions (default: en)
    """
    
    # Service metadata
    service_name: ClassVar[str] = "Weather"
    env_prefix: ClassVar[str] = "WEATHER"
    
    # Weather service provider
    provider: str = "openweathermap"
    
    # Caching configuration (weather data changes at different rates)
    cache_current_ttl: int = 600      # 10 minutes for current weather
    cache_forecast_ttl: int = 3600    # 1 hour for forecasts
    cache_historical_ttl: int = 86400 # 24 hours for historical data
    
    # Service limits and preferences
    max_forecast_days: int = 7
    max_historical_days: int = 30
    units: str = "metric"  # metric, imperial, kelvin
    language: str = "en"
    
    # Data quality settings
    include_alerts: bool = True
    include_minutely: bool = False  # Often not needed and uses more quota
    include_hourly: bool = True
    
    # Rate limiting
    requests_per_minute: int = 60
    requests_per_day: Optional[int] = None

    @classmethod
    def from_env(cls) -> WeatherConfig:
        """Create configuration from environment variables."""
        # Default URLs by provider
        provider = os.getenv("WEATHER_PROVIDER", "openweathermap").lower()
        default_urls = {
            "openweathermap": "https://api.openweathermap.org/data/2.5",
            "weatherapi": "https://api.weatherapi.com/v1",
            "visualcrossing": "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline",
        }
        
        default_url = default_urls.get(provider, "https://api.openweathermap.org/data/2.5")
        
        return cls(
            # Base configuration
            url=os.getenv("WEATHER_URL", default_url),
            
            # Authentication
            api_key=os.getenv("WEATHER_API_KEY"),
            
            # Network configuration
            ssl_verify=get_env_bool("WEATHER_SSL_VERIFY", True),
            timeout=get_env_int("WEATHER_TIMEOUT", 30),
            max_retries=get_env_int("WEATHER_MAX_RETRIES", 3),
            
            # Provider configuration
            provider=provider,
            
            # Caching configuration
            cache_current_ttl=get_env_int("WEATHER_CACHE_CURRENT_TTL", 600),
            cache_forecast_ttl=get_env_int("WEATHER_CACHE_FORECAST_TTL", 3600),
            cache_historical_ttl=get_env_int("WEATHER_CACHE_HISTORICAL_TTL", 86400),
            
            # Service limits
            max_forecast_days=get_env_int("WEATHER_MAX_FORECAST_DAYS", 7),
            max_historical_days=get_env_int("WEATHER_MAX_HISTORICAL_DAYS", 30),
            units=os.getenv("WEATHER_UNITS", "metric"),
            language=os.getenv("WEATHER_LANGUAGE", "en"),
            
            # Data preferences
            include_alerts=get_env_bool("WEATHER_INCLUDE_ALERTS", True),
            include_minutely=get_env_bool("WEATHER_INCLUDE_MINUTELY", False),
            include_hourly=get_env_bool("WEATHER_INCLUDE_HOURLY", True),
            
            # Rate limiting
            requests_per_minute=get_env_int("WEATHER_REQUESTS_PER_MINUTE", 60),
            requests_per_day=get_env_int("WEATHER_REQUESTS_PER_DAY", 0) or None,
        )

    def is_auth_configured(self) -> bool:
        """Most weather services require an API key."""
        return bool(self.api_key)

    def validate(self) -> list[str]:
        """Validate weather-specific configuration."""
        errors = super().validate()
        
        # Units validation
        valid_units = ["metric", "imperial", "kelvin", "standard"]
        if self.units not in valid_units:
            errors.append(f"Units must be one of: {', '.join(valid_units)}")
        
        # Forecast days validation
        if self.max_forecast_days <= 0 or self.max_forecast_days > 16:
            errors.append("Max forecast days must be between 1 and 16")
        
        # Historical days validation
        if self.max_historical_days <= 0:
            errors.append("Max historical days must be positive")
        
        # Cache TTL validation
        if self.cache_current_ttl <= 0:
            errors.append("Current weather cache TTL must be positive")
        
        if self.cache_forecast_ttl <= 0:
            errors.append("Forecast cache TTL must be positive")
        
        if self.cache_historical_ttl <= 0:
            errors.append("Historical cache TTL must be positive")
        
        # Rate limiting validation
        if self.requests_per_minute <= 0:
            errors.append("Requests per minute must be positive")
        
        if self.requests_per_day is not None and self.requests_per_day <= 0:
            errors.append("Requests per day must be positive if specified")
        
        # Provider-specific validation
        valid_providers = ["openweathermap", "weatherapi", "visualcrossing"]
        if self.provider not in valid_providers:
            errors.append(f"Provider must be one of: {', '.join(valid_providers)}")
        
        return errors

    def get_display_info(self) -> dict:
        """Get weather configuration info for display."""
        info = super().get_display_info()
        info.update({
            "provider": self.provider,
            "units": self.units,
            "language": self.language,
            "max_forecast_days": self.max_forecast_days,
            "max_historical_days": self.max_historical_days,
            "cache_ttls": {
                "current": f"{self.cache_current_ttl}s",
                "forecast": f"{self.cache_forecast_ttl}s",
                "historical": f"{self.cache_historical_ttl}s",
            },
            "include_alerts": self.include_alerts,
            "include_hourly": self.include_hourly,
            "rate_limits": {
                "per_minute": self.requests_per_minute,
                "per_day": self.requests_per_day,
            },
        })
        return info
```

## 5. Configuration Factory Pattern

### 5.1 Configuration Manager

```python
# utils/config_manager.py
from typing import Dict, Type, Optional, Any
from ..models.base import BaseServiceConfig
from ..skyfi.config import SkyFiConfig
from ..osm.config import OSMConfig
from ..weather.config import WeatherConfig

class ConfigurationManager:
    """
    Central configuration manager for all services.
    
    Provides:
    - Service configuration discovery
    - Validation across all services
    - Configuration health checking
    - Environment variable documentation
    """
    
    SERVICE_CONFIG_CLASSES: Dict[str, Type[BaseServiceConfig]] = {
        "skyfi": SkyFiConfig,
        "osm": OSMConfig,
        "weather": WeatherConfig,
    }
    
    def __init__(self):
        self._configs: Dict[str, BaseServiceConfig] = {}
        self._validation_errors: Dict[str, list[str]] = {}
    
    def load_all_configs(self) -> Dict[str, BaseServiceConfig]:
        """Load configurations for all available services."""
        configs = {}
        
        for service_name, config_class in self.SERVICE_CONFIG_CLASSES.items():
            try:
                config = config_class.from_env()
                
                # Validate configuration
                errors = config.validate()
                if errors:
                    self._validation_errors[service_name] = errors
                    continue
                
                # Only include if properly configured
                if config.is_auth_configured():
                    configs[service_name] = config
                    
            except Exception as e:
                self._validation_errors[service_name] = [f"Failed to load: {str(e)}"]
        
        self._configs = configs
        return configs
    
    def get_config(self, service_name: str) -> Optional[BaseServiceConfig]:
        """Get configuration for a specific service."""
        return self._configs.get(service_name)
    
    def is_service_available(self, service_name: str) -> bool:
        """Check if a service is properly configured and available."""
        return service_name in self._configs
    
    def get_available_services(self) -> list[str]:
        """Get list of all available services."""
        return list(self._configs.keys())
    
    def get_validation_errors(self) -> Dict[str, list[str]]:
        """Get validation errors for all services."""
        return self._validation_errors.copy()
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status for all services."""
        status = {
            "available_services": self.get_available_services(),
            "total_services": len(self.SERVICE_CONFIG_CLASSES),
            "validation_errors": self.get_validation_errors(),
            "services": {}
        }
        
        for service_name, config in self._configs.items():
            status["services"][service_name] = {
                "configured": True,
                "auth_method": config.get_auth_method(),
                "info": config.get_display_info()
            }
        
        # Add unconfigured services
        for service_name in self.SERVICE_CONFIG_CLASSES:
            if service_name not in self._configs:
                status["services"][service_name] = {
                    "configured": False,
                    "errors": self._validation_errors.get(service_name, [])
                }
        
        return status
    
    def generate_env_template(self) -> str:
        """Generate .env template with all configuration options."""
        template_lines = [
            "# SkyFi MCP Server Configuration Template",
            "# Copy this file to .env and configure the services you want to use",
            "",
        ]
        
        for service_name, config_class in self.SERVICE_CONFIG_CLASSES.items():
            template_lines.extend([
                f"# {config_class.service_name} Configuration",
                f"# Documentation: {config_class.__doc__ or 'No documentation available'}",
            ])
            
            # Get all environment variables from the class docstring
            if config_class.__doc__:
                doc_lines = config_class.__doc__.split('\n')
                env_vars_section = False
                
                for line in doc_lines:
                    line = line.strip()
                    if line.startswith("Environment Variables:"):
                        env_vars_section = True
                        continue
                    
                    if env_vars_section and line.startswith(f"{config_class.env_prefix}_"):
                        # Extract variable name and description
                        if ":" in line:
                            var_name = line.split(":")[0].strip()
                            description = line.split(":", 1)[1].strip()
                            template_lines.append(f"# {var_name}={description}")
                        else:
                            template_lines.append(f"# {line}")
            
            template_lines.extend(["", ""])
        
        return "\n".join(template_lines)
```

## 6. Configuration Usage Examples

### 6.1 Service Configuration Loading

```python
# Example usage in main application
from .utils.config_manager import ConfigurationManager

async def initialize_services():
    """Initialize services based on available configurations."""
    config_manager = ConfigurationManager()
    configs = config_manager.load_all_configs()
    
    # Check for validation errors
    errors = config_manager.get_validation_errors()
    if errors:
        for service, service_errors in errors.items():
            logger.warning(f"{service} configuration errors: {service_errors}")
    
    # Initialize available services
    initialized_services = {}
    
    for service_name, config in configs.items():
        logger.info(f"Initializing {service_name} service")
        logger.info(f"Configuration: {config.get_display_info()}")
        
        # Service-specific initialization would go here
        initialized_services[service_name] = config
    
    return initialized_services

# Generate configuration template
def create_env_template():
    """Create .env template file."""
    config_manager = ConfigurationManager()
    template = config_manager.generate_env_template()
    
    with open(".env.example", "w") as f:
        f.write(template)
    
    print("Created .env.example with all configuration options")
```

This comprehensive configuration system provides:

1. **Consistent Patterns** - All services follow the same configuration patterns
2. **Environment-First** - Configuration primarily through environment variables
3. **Validation** - Built-in validation for all configuration values
4. **Flexibility** - Support for multiple authentication methods per service
5. **Documentation** - Self-documenting configuration with .env template generation
6. **Error Handling** - Clear validation errors and configuration status reporting
7. **Type Safety** - Full type annotations for all configuration classes
8. **Service Discovery** - Automatic detection of configured services

Each service can be independently configured and deployed, while sharing common patterns for authentication, networking, and validation.