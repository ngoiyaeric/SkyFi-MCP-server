"""
Weather Service Configuration

Configuration management for weather data API integration with multi-method
authentication support and environment-based configuration loading.
"""


import os
from typing import Optional
from pydantic import BaseModel, Field, validator


class WeatherConfig(BaseModel):
    """
    Weather service configuration with API key authentication.
    
    Supports OpenWeatherMap API and other weather data providers.
    """
    
    # API Configuration
    api_url: str = Field(
        default="https://api.openweathermap.org/data/2.5",
        description="Base URL for weather API"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API key for weather service authentication"
    )
    
    # Request Configuration
    timeout: float = Field(
        default=30.0,
        description="Request timeout in seconds"
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of API request retries"
    )
    
    # Feature Configuration
    units: str = Field(
        default="metric",
        description="Units for weather data (metric, imperial, kelvin)"
    )
    language: str = Field(
        default="en",
        description="Language for weather descriptions"
    )
    
    @validator("units")
    def validate_units(cls, v):
        """Validate units parameter."""
        valid_units = {"metric", "imperial", "kelvin"}
        if v not in valid_units:
            raise ValueError(f"Units must be one of {valid_units}")
        return v
    
    @classmethod
    def from_env(cls) -> "WeatherConfig":
        """
        Create configuration from environment variables.
        
        Environment Variables:
        - WEATHER_URL: Weather API base URL
        - WEATHER_API_KEY: API key for authentication
        - WEATHER_TIMEOUT: Request timeout
        - WEATHER_MAX_RETRIES: Maximum retries
        - WEATHER_UNITS: Units for data (metric/imperial/kelvin)
        - WEATHER_LANGUAGE: Language code
        """
        return cls(
            api_url=os.getenv("WEATHER_URL", "https://api.openweathermap.org/data/2.5"),
            api_key=os.getenv("WEATHER_API_KEY"),
            timeout=float(os.getenv("WEATHER_TIMEOUT", "30.0")),
            max_retries=int(os.getenv("WEATHER_MAX_RETRIES", "3")),
            units=os.getenv("WEATHER_UNITS", "metric"),
            language=os.getenv("WEATHER_LANGUAGE", "en")
        )
    
    def is_auth_configured(self) -> bool:
        """Check if authentication is properly configured."""
        return bool(self.api_key)
    
    def get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers for API requests."""
        if not self.api_key:
            return {}
        return {"appid": self.api_key}
    
    def validate_config(self) -> list[str]:
        """
        Validate configuration and return list of issues.
        
        Returns:
            List of configuration issues, empty if valid
        """
        issues = []
        
        if not self.api_key:
            issues.append("Weather API key not configured")
        
        if not self.api_url:
            issues.append("Weather API URL not configured")
        
        return issues