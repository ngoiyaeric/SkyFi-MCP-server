"""
SkyFi Ordering Tools

This module implements MCP tools for SkyFi order management, enabling
AI applications to create, track, and manage satellite imagery orders
from both archive and tasking services.

Features:
- Archive image ordering with flexible delivery options
- Tasking order creation for new imagery capture
- Order status tracking and progress monitoring
- Order history and management
- Pricing estimation and cost management
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from fastmcp import FastMCP
from pydantic import BaseModel, Field, validator
import httpx

from . import skyfi_mcp
from ..models.skyfi.order import Order, OrderStatus, OrderRequest, DeliveryOptions
from ..exceptions import SkyFiMCPError

logger = logging.getLogger("mcp-skyfi.skyfi.ordering")


class OrderTypeEnum(str, Enum):
    """Order type enumeration"""
    ARCHIVE = "archive"
    TASKING = "tasking"


class DeliveryMethodEnum(str, Enum):
    """Delivery method enumeration"""
    DOWNLOAD = "download"
    CLOUD_STORAGE = "cloud_storage"
    FTP = "ftp"
    API = "api"


class ArchiveOrderParams(BaseModel):
    """Parameters for creating an archive image order"""
    
    image_ids: List[str] = Field(
        description="List of archive image IDs to order"
    )
    
    delivery_method: DeliveryMethodEnum = Field(
        DeliveryMethodEnum.DOWNLOAD,
        description="Delivery method for the ordered images"
    )
    
    delivery_config: Optional[Dict[str, Any]] = Field(
        None,
        description="Delivery-specific configuration (cloud storage credentials, FTP details, etc.)"
    )
    
    output_format: str = Field(
        "GeoTIFF",
        description="Desired output format (GeoTIFF, JPEG, PNG, etc.)"
    )
    
    output_projection: Optional[str] = Field(
        None,
        description="Target coordinate reference system (EPSG code or proj4 string)"
    )
    
    processing_options: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional processing options (orthorectification, pan-sharpening, etc.)"
    )
    
    priority: str = Field(
        "standard",
        description="Order priority (standard, expedited, rush)"
    )
    
    notifications: Optional[Dict[str, Any]] = Field(
        None,
        description="Notification preferences (email, webhook, etc.)"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Custom metadata to associate with the order"
    )


class TaskingOrderParams(BaseModel):
    """Parameters for creating a new imagery tasking order"""
    
    geometry: Union[Dict[str, Any], str] = Field(
        description="Area of interest as GeoJSON geometry, WKT, or bbox"
    )
    
    start_date: str = Field(
        description="Earliest acceptable capture date (YYYY-MM-DD or ISO format)"
    )
    
    end_date: str = Field(
        description="Latest acceptable capture date (YYYY-MM-DD or ISO format)"
    )
    
    max_cloud_cover: float = Field(
        20.0,
        ge=0.0,
        le=100.0,
        description="Maximum acceptable cloud cover percentage"
    )
    
    min_resolution: Optional[float] = Field(
        None,
        gt=0,
        description="Minimum required resolution in meters per pixel"
    )
    
    preferred_satellites: Optional[List[str]] = Field(
        None,
        description="Preferred satellite missions for capture"
    )
    
    delivery_method: DeliveryMethodEnum = Field(
        DeliveryMethodEnum.DOWNLOAD,
        description="Delivery method for captured images"
    )
    
    delivery_config: Optional[Dict[str, Any]] = Field(
        None,
        description="Delivery-specific configuration"
    )
    
    output_format: str = Field(
        "GeoTIFF",
        description="Desired output format"
    )
    
    processing_level: str = Field(
        "L1C",
        description="Processing level (L1A, L1B, L1C, L2A)"
    )
    
    priority: str = Field(
        "standard",
        description="Order priority level"
    )
    
    budget_limit: Optional[float] = Field(
        None,
        gt=0,
        description="Maximum budget for the tasking order in USD"
    )
    
    notifications: Optional[Dict[str, Any]] = Field(
        None,
        description="Notification preferences"
    )


@skyfi_mcp.tool(
    name="skyfi_create_archive_order",
    description="Create an order for existing archive satellite imagery with delivery options"
)
async def create_archive_order(
    image_ids: List[str],
    delivery_method: str = "download",
    delivery_config: Optional[Dict[str, Any]] = None,
    output_format: str = "GeoTIFF",
    output_projection: Optional[str] = None,
    processing_options: Optional[Dict[str, Any]] = None,
    priority: str = "standard",
    notifications: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create an order for existing archive satellite imagery.
    
    This tool allows AI applications to order and download satellite imagery
    that already exists in the SkyFi archive. Orders can be customized with:
    - Multiple delivery methods (download, cloud storage, FTP, API)
    - Various output formats and projections
    - Custom processing options
    - Priority handling and notifications
    
    Args:
        image_ids: List of archive image IDs to order (from search results)
        delivery_method: How to deliver images (download, cloud_storage, ftp, api)
        delivery_config: Delivery-specific settings (storage credentials, etc.)
        output_format: Desired format (GeoTIFF, JPEG, PNG, NetCDF, etc.)
        output_projection: Target CRS (e.g., "EPSG:4326", "EPSG:3857")
        processing_options: Additional processing (orthorectification, pan-sharpening)
        priority: Order priority (standard, expedited, rush)
        notifications: Notification settings (email, webhook endpoints)
        metadata: Custom metadata to attach to the order
        
    Returns:
        Dictionary containing:
        - order_id: Unique identifier for the created order
        - status: Current order status
        - estimated_delivery: Expected completion time
        - total_cost: Total cost in USD
        - items: List of ordered images with individual details
        - delivery_info: Delivery method and configuration
        - tracking_url: URL to track order progress
        
    Raises:
        SkyFiMCPError: If order creation fails or images are unavailable
    """
    
    try:
        logger.info(f"Creating archive order for {len(image_ids)} images")
        
        # Validate parameters
        params = ArchiveOrderParams(
            image_ids=image_ids,
            delivery_method=DeliveryMethodEnum(delivery_method),
            delivery_config=delivery_config,
            output_format=output_format,
            output_projection=output_projection,
            processing_options=processing_options,
            priority=priority,
            notifications=notifications,
            metadata=metadata
        )
        
        # Get SkyFi configuration
        app_context = skyfi_mcp._mcp_server.request_context.lifespan_context.get("app_lifespan_context")
        if not app_context or not hasattr(app_context, 'skyfi_config'):
            raise SkyFiMCPError("SkyFi service not configured")
        
        config = app_context.skyfi_config
        
        # Check if ordering is enabled
        if not config.enable_ordering:
            raise SkyFiMCPError("Order creation is disabled in current configuration")
        
        headers = {
            **config.get_effective_headers(),
            **config.get_auth_headers()
        }
        
        # Build order payload
        order_payload = {
            "type": "archive",
            "items": [{"image_id": img_id} for img_id in params.image_ids],
            "delivery": {
                "method": params.delivery_method.value,
                "config": params.delivery_config or {}
            },
            "output": {
                "format": params.output_format,
                "projection": params.output_projection,
                "processing_options": params.processing_options or {}
            },
            "priority": params.priority,
            "notifications": params.notifications or {},
            "metadata": params.metadata or {}
        }
        
        # Execute order creation
        async with httpx.AsyncClient(
            timeout=config.timeout,
            verify=config.ssl_verify
        ) as client:
            
            response = await client.post(
                f"{config.url}/orders/archive",
                json=order_payload,
                headers=headers
            )
            
            if response.status_code == 400:
                error_detail = response.json().get("detail", "Invalid order parameters")
                raise SkyFiMCPError(f"Order creation failed: {error_detail}")
            elif response.status_code == 401:
                raise SkyFiMCPError("Authentication failed")
            elif response.status_code == 402:
                raise SkyFiMCPError("Payment required - insufficient credits or billing issue")
            elif response.status_code == 404:
                raise SkyFiMCPError("One or more images not found in archive")
            elif response.status_code != 201:
                raise SkyFiMCPError(f"Order creation failed: HTTP {response.status_code}")
            
            order_result = response.json()
        
        # Format response
        result = {
            "order_id": order_result.get("id"),
            "status": order_result.get("status", "pending"),
            "created_at": order_result.get("created_at"),
            "estimated_delivery": order_result.get("estimated_delivery_date"),
            "estimated_processing_time": order_result.get("estimated_processing_hours"),
            "total_cost_usd": order_result.get("total_cost"),
            "currency": order_result.get("currency", "USD"),
            "items": [],
            "delivery_info": {
                "method": params.delivery_method.value,
                "configuration": order_result.get("delivery_configuration", {})
            },
            "tracking_url": f"{config.url}/orders/{order_result.get('id')}/status",
            "download_url": order_result.get("download_url")
        }
        
        # Process ordered items
        for item in order_result.get("items", []):
            processed_item = {
                "image_id": item.get("image_id"),
                "status": item.get("status", "pending"),
                "cost_usd": item.get("cost"),
                "estimated_size_mb": item.get("estimated_size_mb"),
                "processing_options": item.get("processing_options", {}),
                "delivery_url": item.get("delivery_url")
            }
            result["items"].append(processed_item)
        
        logger.info(f"Archive order created successfully: {result['order_id']}")
        return result
        
    except Exception as e:
        logger.error(f"Archive order creation failed: {e}", exc_info=True)
        if isinstance(e, SkyFiMCPError):
            raise
        raise SkyFiMCPError(f"Archive order error: {str(e)}")


@skyfi_mcp.tool(
    name="skyfi_create_tasking_order",
    description="Create a tasking order for new satellite imagery capture with custom requirements"
)
async def create_tasking_order(
    geometry: str,
    start_date: str,
    end_date: str,
    max_cloud_cover: float = 20.0,
    min_resolution: Optional[float] = None,
    preferred_satellites: Optional[List[str]] = None,
    delivery_method: str = "download",
    delivery_config: Optional[Dict[str, Any]] = None,
    output_format: str = "GeoTIFF",
    processing_level: str = "L1C",
    priority: str = "standard",
    budget_limit: Optional[float] = None,
    notifications: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a tasking order for new satellite imagery capture.
    
    This tool allows AI applications to request new satellite imagery capture
    for areas where archive imagery is insufficient. The system will:
    - Analyze capture feasibility for the specified area and timeframe
    - Schedule capture attempts with available satellites
    - Process and deliver images upon successful capture
    - Provide progress updates and delivery notifications
    
    Args:
        geometry: Area of interest (GeoJSON, WKT, or bbox [west,south,east,north])
        start_date: Earliest capture date (YYYY-MM-DD or ISO format)
        end_date: Latest capture date (YYYY-MM-DD or ISO format)
        max_cloud_cover: Maximum acceptable cloud cover percentage (0-100)
        min_resolution: Minimum resolution required in meters per pixel
        preferred_satellites: List of preferred satellite missions
        delivery_method: Delivery method (download, cloud_storage, ftp, api)
        delivery_config: Delivery-specific configuration
        output_format: Output format (GeoTIFF, JPEG, PNG, etc.)
        processing_level: Processing level (L1A, L1B, L1C, L2A)
        priority: Order priority (standard, expedited, rush)
        budget_limit: Maximum budget in USD
        notifications: Notification preferences
        
    Returns:
        Dictionary containing:
        - order_id: Unique identifier for the tasking order
        - status: Current order status
        - feasibility: Capture probability and satellite pass predictions
        - estimated_cost: Cost estimate range
        - timeline: Expected capture and delivery timeline
        - capture_opportunities: List of upcoming satellite passes
        - monitoring_info: How to track capture progress
        
    Raises:
        SkyFiMCPError: If tasking order creation fails or area is not feasible
    """
    
    try:
        logger.info(f"Creating tasking order for geometry: {geometry}")
        
        # Validate parameters
        params = TaskingOrderParams(
            geometry=geometry,
            start_date=start_date,
            end_date=end_date,
            max_cloud_cover=max_cloud_cover,
            min_resolution=min_resolution,
            preferred_satellites=preferred_satellites,
            delivery_method=DeliveryMethodEnum(delivery_method),
            delivery_config=delivery_config,
            output_format=output_format,
            processing_level=processing_level,
            priority=priority,
            budget_limit=budget_limit,
            notifications=notifications
        )
        
        # Get SkyFi configuration
        app_context = skyfi_mcp._mcp_server.request_context.lifespan_context.get("app_lifespan_context")
        if not app_context or not hasattr(app_context, 'skyfi_config'):
            raise SkyFiMCPError("SkyFi service not configured")
        
        config = app_context.skyfi_config
        
        if not config.enable_ordering:
            raise SkyFiMCPError("Tasking orders are disabled in current configuration")
        
        headers = {
            **config.get_effective_headers(),
            **config.get_auth_headers()
        }
        
        # Normalize geometry
        from .archives import _normalize_geometry
        normalized_geometry = _normalize_geometry(params.geometry)
        
        # Build tasking order payload
        order_payload = {
            "type": "tasking",
            "area_of_interest": normalized_geometry,
            "temporal_requirements": {
                "start_date": params.start_date,
                "end_date": params.end_date,
                "flexible_timing": True
            },
            "quality_requirements": {
                "max_cloud_cover": params.max_cloud_cover,
                "min_resolution": params.min_resolution,
                "processing_level": params.processing_level
            },
            "capture_preferences": {
                "preferred_satellites": params.preferred_satellites or [],
                "priority": params.priority
            },
            "delivery": {
                "method": params.delivery_method.value,
                "config": params.delivery_config or {},
                "format": params.output_format
            },
            "budget": {
                "limit": params.budget_limit,
                "currency": "USD"
            },
            "notifications": params.notifications or {}
        }
        
        # Execute tasking order creation
        async with httpx.AsyncClient(
            timeout=config.timeout * 2,  # Longer timeout for tasking analysis
            verify=config.ssl_verify
        ) as client:
            
            response = await client.post(
                f"{config.url}/orders/tasking",
                json=order_payload,
                headers=headers
            )
            
            if response.status_code == 400:
                error_detail = response.json().get("detail", "Invalid tasking parameters")
                raise SkyFiMCPError(f"Tasking order failed: {error_detail}")
            elif response.status_code == 401:
                raise SkyFiMCPError("Authentication failed")
            elif response.status_code == 402:
                raise SkyFiMCPError("Payment required - insufficient credits")
            elif response.status_code == 422:
                raise SkyFiMCPError("Area not suitable for tasking or requirements too restrictive")
            elif response.status_code != 201:
                raise SkyFiMCPError(f"Tasking order failed: HTTP {response.status_code}")
            
            tasking_result = response.json()
        
        # Format response
        result = {
            "order_id": tasking_result.get("id"),
            "status": tasking_result.get("status", "analyzing"),
            "created_at": tasking_result.get("created_at"),
            "area_of_interest": normalized_geometry,
            "temporal_window": {
                "start": params.start_date,
                "end": params.end_date,
                "duration_days": (datetime.fromisoformat(params.end_date) - 
                                 datetime.fromisoformat(params.start_date)).days
            },
            "requirements": {
                "max_cloud_cover": params.max_cloud_cover,
                "min_resolution": params.min_resolution,
                "processing_level": params.processing_level
            },
            "feasibility": {
                "analysis_status": tasking_result.get("feasibility_status", "analyzing"),
                "capture_probability": tasking_result.get("capture_probability"),
                "difficulty_score": tasking_result.get("difficulty_score"),
                "recommended_adjustments": tasking_result.get("recommendations", [])
            },
            "estimated_cost": {
                "min_usd": tasking_result.get("cost_estimate", {}).get("min"),
                "max_usd": tasking_result.get("cost_estimate", {}).get("max"),
                "currency": "USD",
                "factors": tasking_result.get("cost_factors", [])
            },
            "timeline": {
                "feasibility_analysis_complete": tasking_result.get("analysis_complete_date"),
                "first_capture_opportunity": tasking_result.get("first_opportunity_date"),
                "estimated_capture_date": tasking_result.get("estimated_capture_date"),
                "estimated_delivery_date": tasking_result.get("estimated_delivery_date")
            },
            "capture_opportunities": tasking_result.get("satellite_passes", []),
            "monitoring_info": {
                "tracking_url": f"{config.url}/orders/{tasking_result.get('id')}/status",
                "webhook_url": tasking_result.get("webhook_url"),
                "update_frequency": "4x daily during capture window"
            }
        }
        
        logger.info(f"Tasking order created successfully: {result['order_id']}")
        return result
        
    except Exception as e:
        logger.error(f"Tasking order creation failed: {e}", exc_info=True)
        if isinstance(e, SkyFiMCPError):
            raise
        raise SkyFiMCPError(f"Tasking order error: {str(e)}")


@skyfi_mcp.tool(
    name="skyfi_get_order_status",
    description="Get current status and progress information for an existing order"
)
async def get_order_status(order_id: str) -> Dict[str, Any]:
    """
    Retrieve current status and detailed progress information for an order.
    
    This tool provides real-time updates on order progress including:
    - Current processing status and stage
    - Completion percentage and estimated time remaining
    - Individual item status for multi-image orders
    - Download availability and delivery information
    - Any issues or errors encountered
    - Next steps and expected timeline
    
    Args:
        order_id: Unique identifier of the order to check
        
    Returns:
        Dictionary containing:
        - order_info: Basic order details and metadata
        - current_status: Current processing status and stage
        - progress: Completion percentage and timing estimates
        - items: Status of individual order items
        - delivery: Download links and delivery information
        - issues: Any problems or errors encountered
        - next_steps: Expected next actions and timeline
        
    Raises:
        SkyFiMCPError: If order not found or access denied
    """
    
    try:
        logger.info(f"Checking status for order: {order_id}")
        
        # Get SkyFi configuration
        app_context = skyfi_mcp._mcp_server.request_context.lifespan_context.get("app_lifespan_context")
        if not app_context or not hasattr(app_context, 'skyfi_config'):
            raise SkyFiMCPError("SkyFi service not configured")
        
        config = app_context.skyfi_config
        headers = {
            **config.get_effective_headers(),
            **config.get_auth_headers()
        }
        
        # Execute status request
        async with httpx.AsyncClient(
            timeout=config.timeout,
            verify=config.ssl_verify
        ) as client:
            
            response = await client.get(
                f"{config.url}/orders/{order_id}/status",
                headers=headers
            )
            
            if response.status_code == 404:
                raise SkyFiMCPError(f"Order not found: {order_id}")
            elif response.status_code == 401:
                raise SkyFiMCPError("Authentication failed")
            elif response.status_code == 403:
                raise SkyFiMCPError("Access denied - order belongs to different account")
            elif response.status_code != 200:
                raise SkyFiMCPError(f"Status check failed: HTTP {response.status_code}")
            
            status_data = response.json()
        
        # Format status response
        result = {
            "order_info": {
                "order_id": status_data.get("id"),
                "type": status_data.get("type"),
                "created_at": status_data.get("created_at"),
                "last_updated": status_data.get("updated_at"),
                "priority": status_data.get("priority", "standard")
            },
            "current_status": {
                "stage": status_data.get("status"),
                "stage_description": _get_status_description(status_data.get("status")),
                "substage": status_data.get("substage"),
                "is_active": status_data.get("is_active", False),
                "is_completed": status_data.get("is_completed", False),
                "is_failed": status_data.get("is_failed", False)
            },
            "progress": {
                "completion_percent": status_data.get("progress_percent", 0),
                "estimated_completion": status_data.get("estimated_completion"),
                "time_remaining_hours": status_data.get("time_remaining_hours"),
                "processing_started": status_data.get("processing_started"),
                "processing_steps": status_data.get("processing_steps", [])
            },
            "items": [],
            "delivery": {
                "method": status_data.get("delivery_method"),
                "status": status_data.get("delivery_status"),
                "download_urls": status_data.get("download_urls", []),
                "expires_at": status_data.get("download_expires_at"),
                "total_size_mb": status_data.get("total_size_mb")
            },
            "costs": {
                "total_charged_usd": status_data.get("total_charged"),
                "currency": status_data.get("currency", "USD"),
                "billing_status": status_data.get("billing_status")
            },
            "issues": status_data.get("issues", []),
            "notifications": {
                "last_sent": status_data.get("last_notification_sent"),
                "next_update": status_data.get("next_update_scheduled")
            }
        }
        
        # Process individual items
        for item in status_data.get("items", []):
            processed_item = {
                "item_id": item.get("id"),
                "image_id": item.get("image_id"),
                "status": item.get("status"),
                "progress_percent": item.get("progress_percent", 0),
                "file_size_mb": item.get("file_size_mb"),
                "download_url": item.get("download_url"),
                "processing_details": item.get("processing_details", {}),
                "issues": item.get("issues", [])
            }
            result["items"].append(processed_item)
        
        # Add next steps based on current status
        result["next_steps"] = _get_next_steps(status_data.get("status"), status_data.get("type"))
        
        logger.info(f"Retrieved status for order {order_id}: {result['current_status']['stage']}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to get order status for {order_id}: {e}", exc_info=True)
        if isinstance(e, SkyFiMCPError):
            raise
        raise SkyFiMCPError(f"Order status error: {str(e)}")


def _get_status_description(status: str) -> str:
    """Get human-readable description for order status"""
    
    status_descriptions = {
        "pending": "Order received and queued for processing",
        "analyzing": "Analyzing requirements and feasibility",
        "approved": "Order approved and ready for processing",
        "processing": "Images are being processed",
        "capturing": "Satellite capture in progress (tasking orders)",
        "completed": "Order completed and ready for delivery",
        "delivered": "Order delivered successfully",
        "failed": "Order failed - see issues for details",
        "cancelled": "Order was cancelled",
        "expired": "Order expired before completion"
    }
    
    return status_descriptions.get(status, f"Unknown status: {status}")


def _get_next_steps(status: str, order_type: str) -> List[str]:
    """Get expected next steps based on current status"""
    
    if status == "pending":
        return ["Order will be reviewed and approved", "Processing will begin within 24 hours"]
    elif status == "analyzing":
        return ["Feasibility analysis in progress", "You will receive an update within 4 hours"]
    elif status == "approved":
        return ["Processing will begin shortly", "You'll receive a notification when processing starts"]
    elif status == "processing":
        return ["Images are being processed", "Processing typically takes 2-8 hours"]
    elif status == "capturing" and order_type == "tasking":
        return ["Waiting for optimal capture conditions", "Satellite passes monitored 4x daily"]
    elif status == "completed":
        return ["Order ready for download", "Download links are active for 7 days"]
    elif status == "delivered":
        return ["Order successfully delivered", "No further action required"]
    elif status == "failed":
        return ["Review failure details", "Contact support if assistance needed"]
    else:
        return ["Check back for updates", "Contact support if you have questions"]


logger.info("SkyFi Ordering tools loaded successfully")