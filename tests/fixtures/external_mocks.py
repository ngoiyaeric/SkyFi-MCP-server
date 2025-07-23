"""
External Service Mocking Framework

This module provides comprehensive mocking for external services used by the SkyFi MCP server,
including SkyFi API, OpenWeatherMap, and OpenStreetMap Nominatim services.
"""

from __future__ import annotations

import asyncio
import json
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock
import httpx
import respx


class ExternalServiceMockSuite:
    """Comprehensive external service mocking suite."""
    
    def __init__(self):
        self.skyfi_mock = SkyFiAPIMock()
        self.weather_mock = WeatherAPIMock()
        self.osm_mock = OSMAPIMock()
        self.respx_router = None
        
    async def setup(self):
        """Initialize all external service mocks."""
        self.respx_router = respx.MockRouter(assert_all_called=False)
        
        # Setup individual service mocks
        await self.skyfi_mock.setup(self.respx_router)
        await self.weather_mock.setup(self.respx_router)
        await self.osm_mock.setup(self.respx_router)
        
        # Start the mock router
        await self.respx_router.start()
        
    async def teardown(self):
        """Cleanup all mocks."""
        if self.respx_router:
            await self.respx_router.stop()


class SkyFiAPIMock:
    """SkyFi Platform API mock with realistic responses."""
    
    def __init__(self):
        self.base_url = "http://mock-skyfi-api.test"
        
    async def setup(self, router: respx.MockRouter):
        """Setup SkyFi API mock routes."""
        
        # Authentication endpoint - whoami
        router.get(f"{self.base_url}/platform-api/auth/whoami").mock(
            side_effect=self._handle_whoami_request
        )
        
        # Archive search endpoint
        router.post(f"{self.base_url}/platform-api/archives/search").mock(
            side_effect=self._handle_archive_search
        )
        
        # Order creation endpoint
        router.post(f"{self.base_url}/platform-api/orders").mock(
            side_effect=self._handle_create_order
        )
        
        # Order status endpoint
        router.get(f"{self.base_url}/platform-api/orders/{respx.patterns.ANY}").mock(
            side_effect=self._handle_order_status
        )
        
        # Archive details endpoint
        router.get(f"{self.base_url}/platform-api/archives/{respx.patterns.ANY}").mock(
            side_effect=self._handle_archive_details
        )
        
    def _handle_whoami_request(self, request: httpx.Request):
        """Handle whoami authentication requests."""
        api_key = request.headers.get("X-Skyfi-Api-Key")
        
        if not api_key:
            return httpx.Response(401, json={"detail": "Authentication failed"})
            
        if api_key == "test_skyfi_key_valid_123":
            return httpx.Response(200, json={
                "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
                "organizationId": "7bc05553-4b68-44e8-b7bc-37be63c6d9e9",
                "email": "test@example.com",
                "firstName": "Test",
                "lastName": "User",
                "isDemoAccount": False,
                "currentBudgetUsage": 150.50,
                "budgetAmount": 1000.00,
                "hasValidSharedCard": True
            })
            
        elif api_key == "test_skyfi_key_expired":
            return httpx.Response(401, json={"detail": "API key expired"})
            
        elif api_key == "test_skyfi_key_rate_limited":
            return httpx.Response(429, json={
                "detail": "Rate limit exceeded",
                "retry_after": 60
            })
            
        else:
            return httpx.Response(401, json={"detail": "Invalid API key"})
            
    def _handle_archive_search(self, request: httpx.Request):
        """Handle archive search requests."""
        api_key = request.headers.get("X-Skyfi-Api-Key")
        
        if api_key != "test_skyfi_key_valid_123":
            return httpx.Response(401, json={"detail": "Authentication failed"})
            
        try:
            search_params = json.loads(request.content)
        except json.JSONDecodeError:
            return httpx.Response(400, json={"detail": "Invalid JSON in request body"})
            
        # Validate required parameters
        if "aoi" not in search_params:
            return httpx.Response(422, json={
                "detail": "Missing required parameter: aoi"
            })
            
        # Mock search results based on request
        aoi = search_params["aoi"]
        
        if aoi.get("type") == "Point":
            # Point queries return fewer results
            mock_results = [
                {
                    "id": "archive_001",
                    "capture_time": "2024-01-15T10:30:00Z",
                    "cloud_coverage": 5.2,
                    "resolution": 3.0,
                    "sensor": "WorldView-3",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [-122.42, 37.77], [-122.41, 37.77],
                            [-122.41, 37.78], [-122.42, 37.78],
                            [-122.42, 37.77]
                        ]]
                    },
                    "preview_url": "https://preview.skyfi.com/archive_001.jpg",
                    "price_usd": 45.00
                }
            ]
        elif aoi.get("type") == "Polygon":
            # Polygon queries return more results
            mock_results = [
                {
                    "id": "archive_002",
                    "capture_time": "2024-01-20T14:15:00Z", 
                    "cloud_coverage": 12.8,
                    "resolution": 2.5,
                    "sensor": "GeoEye-1",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [-122.5, 37.7], [-122.4, 37.7],
                            [-122.4, 37.8], [-122.5, 37.8],
                            [-122.5, 37.7]
                        ]]
                    },
                    "preview_url": "https://preview.skyfi.com/archive_002.jpg",
                    "price_usd": 125.00
                },
                {
                    "id": "archive_003",
                    "capture_time": "2024-01-22T09:45:00Z",
                    "cloud_coverage": 8.1,
                    "resolution": 1.5,
                    "sensor": "QuickBird",
                    "geometry": {
                        "type": "Polygon", 
                        "coordinates": [[
                            [-122.45, 37.75], [-122.35, 37.75],
                            [-122.35, 37.85], [-122.45, 37.85],
                            [-122.45, 37.75]
                        ]]
                    },
                    "preview_url": "https://preview.skyfi.com/archive_003.jpg",
                    "price_usd": 180.00
                }
            ]
        else:
            return httpx.Response(400, json={
                "detail": "Unsupported geometry type"
            })
            
        return httpx.Response(200, json={
            "results": mock_results,
            "total": len(mock_results),
            "page": 1,
            "per_page": 50
        })
        
    def _handle_create_order(self, request: httpx.Request):
        """Handle order creation requests."""
        api_key = request.headers.get("X-Skyfi-Api-Key")
        
        if api_key != "test_skyfi_key_valid_123":
            return httpx.Response(401, json={"detail": "Authentication failed"})
            
        try:
            order_params = json.loads(request.content)
        except json.JSONDecodeError:
            return httpx.Response(400, json={"detail": "Invalid JSON in request body"})
            
        # Validate order parameters
        required_fields = ["archive_ids", "delivery_config"]
        for field in required_fields:
            if field not in order_params:
                return httpx.Response(422, json={
                    "detail": f"Missing required parameter: {field}"
                })
                
        # Mock successful order creation
        return httpx.Response(201, json={
            "id": "order_12345",
            "status": "processing",
            "archive_ids": order_params["archive_ids"],
            "delivery_config": order_params["delivery_config"],
            "total_cost_usd": 250.00,
            "estimated_delivery": "2024-01-25T10:00:00Z",
            "created_at": "2024-01-23T15:30:00Z"
        })
        
    def _handle_order_status(self, request: httpx.Request):
        """Handle order status requests."""
        api_key = request.headers.get("X-Skyfi-Api-Key")
        
        if api_key != "test_skyfi_key_valid_123":
            return httpx.Response(401, json={"detail": "Authentication failed"})
            
        # Extract order ID from URL
        order_id = request.url.path.split("/")[-1]
        
        if order_id == "order_12345":
            return httpx.Response(200, json={
                "id": "order_12345",
                "status": "completed",
                "progress": 100,
                "delivery_url": "https://delivery.skyfi.com/order_12345.zip",
                "completed_at": "2024-01-25T09:30:00Z"
            })
        else:
            return httpx.Response(404, json={"detail": "Order not found"})
            
    def _handle_archive_details(self, request: httpx.Request):
        """Handle archive details requests."""
        api_key = request.headers.get("X-Skyfi-Api-Key")
        
        if api_key != "test_skyfi_key_valid_123":
            return httpx.Response(401, json={"detail": "Authentication failed"})
            
        # Extract archive ID from URL
        archive_id = request.url.path.split("/")[-1]
        
        # Mock archive details
        archive_details = {
            "archive_001": {
                "id": "archive_001",
                "capture_time": "2024-01-15T10:30:00Z",
                "cloud_coverage": 5.2,
                "resolution": 3.0,
                "sensor": "WorldView-3",
                "sun_elevation": 45.2,
                "off_nadir_angle": 12.8,
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-122.42, 37.77], [-122.41, 37.77],
                        [-122.41, 37.78], [-122.42, 37.78],
                        [-122.42, 37.77]
                    ]]
                },
                "metadata": {
                    "satellite": "WorldView-3",
                    "processing_level": "1B",
                    "spectral_bands": ["Blue", "Green", "Red", "Near-IR"]
                }
            }
        }
        
        if archive_id in archive_details:
            return httpx.Response(200, json=archive_details[archive_id])
        else:
            return httpx.Response(404, json={"detail": "Archive not found"})


class WeatherAPIMock:
    """Weather service API mock."""
    
    def __init__(self):
        self.base_url = "http://mock-weather-api.test"
        
    async def setup(self, router: respx.MockRouter):
        """Setup weather API mock routes."""
        
        # Current weather endpoint
        router.get(f"{self.base_url}/weather").mock(
            side_effect=self._handle_current_weather
        )
        
        # Weather forecast endpoint
        router.get(f"{self.base_url}/forecast").mock(
            side_effect=self._handle_weather_forecast
        )
        
    def _handle_current_weather(self, request: httpx.Request):
        """Handle current weather requests."""
        params = dict(request.url.params)
        
        if "lat" not in params or "lon" not in params:
            return httpx.Response(400, json={
                "error": "Missing required parameters: lat, lon"
            })
            
        try:
            lat = float(params["lat"])
            lon = float(params["lon"])
        except ValueError:
            return httpx.Response(400, json={
                "error": "Invalid latitude or longitude"
            })
            
        # Mock weather response based on location
        if 37.0 <= lat <= 38.0 and -123.0 <= lon <= -122.0:
            # San Francisco area
            return httpx.Response(200, json={
                "coord": {"lon": lon, "lat": lat},
                "weather": [{
                    "id": 800,
                    "main": "Clear",
                    "description": "clear sky",
                    "icon": "01d"
                }],
                "main": {
                    "temp": 282.55,  # Kelvin
                    "feels_like": 281.86,
                    "temp_min": 280.37,
                    "temp_max": 284.26,
                    "pressure": 1023,
                    "humidity": 100
                },
                "visibility": 10000,
                "wind": {
                    "speed": 1.5,
                    "deg": 350
                },
                "dt": 1643723400,
                "name": "San Francisco"
            })
        else:
            # Generic location
            return httpx.Response(200, json={
                "coord": {"lon": lon, "lat": lat},
                "weather": [{
                    "id": 801,
                    "main": "Clouds", 
                    "description": "few clouds",
                    "icon": "02d"
                }],
                "main": {
                    "temp": 290.15,
                    "pressure": 1013,
                    "humidity": 65
                },
                "wind": {"speed": 2.1, "deg": 180},
                "dt": 1643723400,
                "name": "Generic Location"
            })
            
    def _handle_weather_forecast(self, request: httpx.Request):
        """Handle weather forecast requests."""
        params = dict(request.url.params)
        
        if "lat" not in params or "lon" not in params:
            return httpx.Response(400, json={
                "error": "Missing required parameters: lat, lon"
            })
            
        # Mock 5-day forecast
        forecast_data = {
            "list": [
                {
                    "dt": 1643723400 + (i * 3600 * 3),  # 3-hour intervals
                    "main": {
                        "temp": 285.0 + (i % 3),
                        "pressure": 1013 + (i % 5),
                        "humidity": 60 + (i % 20)
                    },
                    "weather": [{
                        "main": "Clear" if i % 2 == 0 else "Clouds",
                        "description": "clear sky" if i % 2 == 0 else "few clouds"
                    }],
                    "wind": {"speed": 1.5 + (i % 3) * 0.5}
                }
                for i in range(40)  # 5 days * 8 intervals per day
            ],
            "city": {
                "name": "Test Location",
                "coord": {"lat": float(params["lat"]), "lon": float(params["lon"])}
            }
        }
        
        return httpx.Response(200, json=forecast_data)


class OSMAPIMock:
    """OpenStreetMap Nominatim API mock."""
    
    def __init__(self):
        self.base_url = "http://mock-osm-api.test"
        
    async def setup(self, router: respx.MockRouter):
        """Setup OSM API mock routes."""
        
        # Geocoding search endpoint
        router.get(f"{self.base_url}/search").mock(
            side_effect=self._handle_search_request
        )
        
        # Reverse geocoding endpoint
        router.get(f"{self.base_url}/reverse").mock(
            side_effect=self._handle_reverse_request
        )
        
    def _handle_search_request(self, request: httpx.Request):
        """Handle geocoding search requests."""
        params = dict(request.url.params)
        
        query = params.get("q", "").lower()
        
        if not query:
            return httpx.Response(400, json={
                "error": "Missing query parameter"
            })
            
        # Mock responses based on query
        if "san francisco" in query or "sf" in query:
            return httpx.Response(200, json=[{
                "place_id": 282983122,
                "licence": "© OpenStreetMap contributors",
                "osm_type": "relation",
                "osm_id": 111968,
                "boundingbox": ["37.6398299", "37.9298239", "-123.1738281", "-122.281479"],
                "lat": "37.7749295",
                "lon": "-122.4194155",
                "display_name": "San Francisco, California, United States",
                "class": "place",
                "type": "city",
                "importance": 0.75
            }])
            
        elif "nonexistent" in query:
            return httpx.Response(200, json=[])
            
        else:
            # Generic location
            return httpx.Response(200, json=[{
                "place_id": 123456,
                "licence": "© OpenStreetMap contributors",
                "lat": "40.7128",
                "lon": "-74.0060",
                "display_name": "Generic City, State, Country",
                "class": "place",
                "type": "city"
            }])
            
    def _handle_reverse_request(self, request: httpx.Request):
        """Handle reverse geocoding requests."""
        params = dict(request.url.params)
        
        try:
            lat = float(params.get("lat", 0))
            lon = float(params.get("lon", 0))
        except ValueError:
            return httpx.Response(400, json={
                "error": "Invalid latitude or longitude"
            })
            
        # Mock reverse geocoding responses
        if 37.0 <= lat <= 38.0 and -123.0 <= lon <= -122.0:
            return httpx.Response(200, json={
                "place_id": 282983122,
                "licence": "© OpenStreetMap contributors",
                "lat": str(lat),
                "lon": str(lon),
                "display_name": "San Francisco, California, United States",
                "address": {
                    "city": "San Francisco",
                    "state": "California",
                    "country": "United States",
                    "country_code": "us"
                }
            })
        else:
            return httpx.Response(200, json={
                "place_id": 123456,
                "lat": str(lat),
                "lon": str(lon),
                "display_name": "Unknown Location",
                "address": {
                    "country": "Unknown"
                }
            })